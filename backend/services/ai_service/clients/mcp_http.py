"""Official MCP SDK over HTTP only; no stdio, shell, roots or sampling."""
import asyncio
import ipaddress
import json
import socket
from urllib.parse import urlsplit
from contextlib import asynccontextmanager
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from fastapi import HTTPException
from jsonschema import Draft202012Validator
from .mcp_proxy import proxy_for


def validate_url(value):
    try:
        p = urlsplit(value)
        valid = p.scheme == 'https' and p.hostname and p.port in (None, 443) and not (p.username or p.password or p.query or p.fragment)
    except ValueError:
        valid = False
    if not valid or len(value) > 1500 or any(c.isspace() for c in value):
        raise HTTPException(422, 'MCP 地址需为公网 HTTPS 地址（443端口），不能包含凭证或查询参数')
    return value


class BoundedStream(httpx2.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream
    async def __aiter__(self):
        total = 0
        async for chunk in self.stream:
            total += len(chunk)
            if total > 2 * 1024 * 1024:
                raise ValueError('MCP response too large')
            yield chunk
    async def aclose(self):
        await self.stream.aclose()


class PublicTransport(httpx2.AsyncBaseTransport):
    def __init__(self, endpoint):
        self.endpoint = httpx2.URL(validate_url(endpoint))
        self.proxy = proxy_for(self.endpoint.host)
        self.inner = httpx2.AsyncHTTPTransport(retries=0, trust_env=False, proxy=self.proxy)

    async def handle_async_request(self, request):
        # Every HTTP request remains at the configured endpoint. No redirect following.
        if request.url != self.endpoint:
            raise ValueError('Unexpected MCP destination')
        if self.proxy:
            # Only explicitly allowlisted hosts delegate DNS/egress to the trusted
            # operator proxy. Preserve hostname for CONNECT and TLS validation.
            response = await self.inner.handle_async_request(request)
        else:
            host = request.url.host
            addresses = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            ips = [row[4][0] for row in addresses]
            if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
                raise ValueError('Non-public MCP destination')
            # Pin direct connections to the verified IP, retaining TLS name/Host.
            target = request.url.copy_with(host=ips[0])
            pinned = httpx2.Request(request.method, target, headers=request.headers,
                                    stream=request.stream, extensions={**request.extensions, 'sni_hostname': host})
            response = await self.inner.handle_async_request(pinned)
        if 300 <= response.status_code < 400 or response.headers.get('content-encoding', 'identity') != 'identity':
            await response.aclose()
            raise ValueError('MCP redirects/compressed responses not allowed')
        response.stream = BoundedStream(response.stream)
        return response

    async def aclose(self):
        await self.inner.aclose()


@asynccontextmanager
async def connection(url, headers):
    async with httpx2.AsyncClient(headers={**headers, 'Accept-Encoding': 'identity'},
                                  transport=PublicTransport(url), trust_env=False,
                                  follow_redirects=False, timeout=httpx2.Timeout(20, connect=8)) as http:
        async with Client(streamable_http_client(url, http_client=http), cache=None,
                          read_timeout_seconds=20) as client:
            yield client


def safe_schema(schema):
    if len(json.dumps(schema)) > 12000 or schema.get('type') != 'object':
        raise ValueError('Unsupported schema size/type')
    def walk(value, depth=0):
        if depth > 12:
            raise ValueError('Schema nesting too deep')
        if isinstance(value, dict):
            if any(k in value for k in ('$ref', '$dynamicRef', 'pattern', 'patternProperties')):
                raise ValueError('Schema references/patterns not supported')
            for item in value.values():
                walk(item, depth+1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth+1)
    walk(schema)
    Draft202012Validator.check_schema(schema)
    return schema


async def tools(client):
    result, cursors, cursor = [], set(), None
    for _ in range(8):
        page = await client.list_tools(cursor=cursor, cache_mode='refresh')
        for t in page.tools:
            row = t.model_dump(mode='json', by_alias=True, exclude_none=True)
            if len(result) >= 64:
                raise ValueError('Too many MCP tools')
            import re
            if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,128}', row['name']) or any(x['name'] == row['name'] for x in result):
                raise ValueError('Invalid/duplicate MCP tool name')
            schema = safe_schema(row['inputSchema'])
            result.append({'name': row['name'], 'description': row.get('description', '')[:2000],
                           'inputSchema': schema, 'effect': 'disabled'})
        cursor = page.next_cursor
        if cursor is None:
            return result
        if cursor in cursors:
            raise ValueError('Repeated cursor')
        cursors.add(cursor)
    raise ValueError('Too many pages')


async def discover(url, headers):
    async with asyncio.timeout(30):
        async with connection(url, headers) as client:
            return await tools(client)


def redact(value, headers):
    secrets=[]
    for secret in headers.values():
        if secret:
            secrets.append(secret)
            if secret.lower().startswith('bearer '):secrets.append(secret[7:])
    def clean(item):
        if isinstance(item,str):
            for secret in secrets:item=item.replace(secret,'[redacted]')
            return item
        if isinstance(item,list):return [clean(v) for v in item]
        if isinstance(item,dict):return {clean(k):clean(v) for k,v in item.items()}
        return item
    return clean(value)


async def invoke(url, headers, definition, arguments, before_call=None):
    async with asyncio.timeout(35):
        async with connection(url, headers) as client:
            current = await tools(client)
            tool = next((t for t in current if t['name'] == definition['name']), None)
            if not tool or tool['inputSchema'] != definition['inputSchema'] or tool['description'] != definition['description']:
                raise HTTPException(409, 'MCP 工具定义已变化，请重新发现工具并授权')
            if before_call is not None:before_call()
            # Low-level call avoids high-level automatic tool retries or elicitation loops.
            result = await client.session.call_tool(definition['name'], arguments)
            data = result.model_dump(mode='json', by_alias=True, exclude_none=True)
            # Text/structured output only; no automatic URI download or local file access.
            content = [{'type': 'text', 'text': item.get('text', '')[:12000]}
                       for item in data.get('content', []) if item.get('type') == 'text']
            output = {'content': content[:8], 'isError': data.get('isError', False),
                      'structuredContent': data.get('structuredContent'),
                      'omitted_blocks': sum(item.get('type') != 'text' for item in data.get('content', []))}
            output=redact(output,headers)
            encoded = json.dumps(output, ensure_ascii=False)
            if len(encoded) > 24000:
                return {'content': [{'type':'text','text':encoded[:22000]}], 'truncated':True, 'isError':output['isError']}
            return json.loads(encoded)

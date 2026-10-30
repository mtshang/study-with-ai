"""Bounded OpenAI-compatible embeddings; credentials never enter task receipts."""
import asyncio,ipaddress,json,math,socket
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from ..services.configuration import validate_url

class PublicTransport(httpx.AsyncBaseTransport):
    def __init__(self,endpoint):
        self.endpoint=httpx.URL(endpoint)
        self.inner=httpx.AsyncHTTPTransport(trust_env=False,retries=0)
    async def handle_async_request(self,request):
        if request.url!=self.endpoint:raise ValueError('Unexpected destination')
        host=request.url.host
        addresses=await asyncio.get_running_loop().getaddrinfo(host,443,type=socket.SOCK_STREAM)
        ips=[r[4][0] for r in addresses]
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise HTTPException(422,'Embedding 域名解析到本机、内网或保留地址；请检查代理 Fake-IP 设置')
        pinned=httpx.Request(request.method,request.url.copy_with(host=ips[0]),headers=request.headers,
            stream=request.stream,extensions={**request.extensions,'sni_hostname':host})
        return await self.inner.handle_async_request(pinned)
    async def aclose(self):await self.inner.aclose()

def validate_vectors(body,count):
    rows=body['data']
    if len(rows)!=count or sorted(r['index'] for r in rows)!=list(range(count)):raise ValueError('Invalid indices')
    vectors=[r['embedding'] for r in sorted(rows,key=lambda r:r['index'])]
    size=len(vectors[0])
    if not 1<=size<=8192:raise ValueError('Invalid dimension')
    for vector in vectors:
        if len(vector)!=size or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in vector):raise ValueError('Invalid vector')
        if not any(x!=0 for x in vector):raise ValueError('Zero vector')
    return vectors

async def embed(config,texts):
    if not 1<=len(texts)<=16 or any(not t.strip() or len(t)>3000 for t in texts):
        raise HTTPException(422,'向量化每批最多16段，每段最多3000字符')
    endpoint=validate_url(config['base_url'])+'/embeddings'
    try:
        async with httpx.AsyncClient(transport=PublicTransport(endpoint),trust_env=False,follow_redirects=False,timeout=60) as client:
            async with client.stream('POST',endpoint,headers={'Authorization':'Bearer '+config['key'],'Accept-Encoding':'identity'},
                json={'model':config['model'],'input':texts,'encoding_format':'float'}) as response:
                if response.status_code!=200:raise HTTPException(502,f'Embedding 接口返回 HTTP {response.status_code}，请检查地址、模型、Key和额度')
                body=bytearray()
                async for part in response.aiter_bytes():
                    body.extend(part)
                    if len(body)>4*1024*1024:raise ValueError('Response too large')
        return validate_vectors(json.loads(body),len(texts))
    except (httpx.HTTPError,OSError,ValueError,KeyError,TypeError,IndexError,OverflowError):
        raise HTTPException(502,'Embedding 连接失败或返回向量格式不正确') from None

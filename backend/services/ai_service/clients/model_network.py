"""Exact model endpoint transport; user trust permits only TUN Fake-IP ranges."""
import asyncio,ipaddress,socket
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException

def permits(address,trusted=False):
    ip=ipaddress.ip_address(address)
    return ip.is_global or (trusted and ((ip.version==4 and ip in ipaddress.ip_network('198.18.0.0/15')) or (ip.version==6 and ip in ipaddress.ip_network('2001:2::/48'))))

async def resolve(host,trusted=False):
    try:
        rows=await asyncio.get_running_loop().getaddrinfo(host,443,type=socket.SOCK_STREAM)
    except socket.gaierror:raise HTTPException(502,'模型接口域名无法解析') from None
    ips=[r[4][0] for r in rows]
    if not ips or any(not permits(ip,trusted) for ip in ips):
        raise HTTPException(422,'模型地址解析为本机、内网或保留地址；TUN Fake-IP需在API设置中确认信任当前URL')
    return ips

class ModelTransport(httpx.AsyncBaseTransport):
    def __init__(self,endpoint,*,base_url='',trusted_url=''):
        self.endpoint=httpx.URL(endpoint)
        base=base_url.rstrip('/')
        self.trusted=bool(base and trusted_url==base and endpoint in (base,base+'/chat/completions'))
        self.inner=httpx.AsyncHTTPTransport(trust_env=False,retries=0)
    async def handle_async_request(self,request):
        if request.url!=self.endpoint:raise ValueError('Unexpected destination')
        host=request.url.host
        ips=await resolve(host,self.trusted)
        pinned=httpx.Request(request.method,request.url.copy_with(host=ips[0]),headers=request.headers,
            stream=request.stream,extensions={**request.extensions,'sni_hostname':host})
        return await self.inner.handle_async_request(pinned)
    async def aclose(self):await self.inner.aclose()

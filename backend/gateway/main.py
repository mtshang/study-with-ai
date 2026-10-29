"""Development HTTP gateway. No business tables or per-user authority inferred here."""
from contextlib import asynccontextmanager
import asyncio
import httpx
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,StreamingResponse
from starlette.background import BackgroundTask
from common import config
from common.body_limit import BodyLimitMiddleware

HOP={"host","connection","keep-alive","proxy-authenticate","proxy-authorization","te","trailer","transfer-encoding","upgrade"}

def forwarded_headers(raw):
    connection=set()
    for key,value in raw:
        if key.lower()==b"connection": connection.update(part.strip().lower() for part in value.decode("latin1").split(","))
    blocked=HOP|connection|{"x-service-key","x-task-grant","x-user-id","x-forwarded-for","x-forwarded-host","x-forwarded-proto"}
    return [(key,value) for key,value in raw if key.decode("latin1").lower() not in blocked]

def target(path):
    if path.startswith("/api/auth/") or path.startswith("/api/preferences/"): return config.IDENTITY_URL
    if path=="/api/courses" or path.startswith("/api/courses/"): return config.LEARNING_URL
    if path.startswith("/api/ai/"): return config.AI_URL
    return None

@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=httpx.Timeout(60,connect=5),trust_env=False,
                                 limits=httpx.Limits(max_connections=100,max_keepalive_connections=20)) as client:
        app.state.http=client
        yield

app=FastAPI(title="Study with AI gateway",lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)

@app.get("/api/health")
async def health(): return {"status":"ok","service":"gateway"}

@app.get("/api/ready")
async def ready(request:Request):
    async def probe(name,url):
        try:
            response=await request.app.state.http.get(url+"/api/ready",timeout=5)
            return name,response.status_code==200
        except httpx.HTTPError: return name,False
    results=dict(await asyncio.gather(probe("identity",config.IDENTITY_URL),probe("learning",config.LEARNING_URL),probe("ai",config.AI_URL)))
    good=all(results.values())
    return JSONResponse({"status":"ready" if good else "unavailable","database":"mysql","services":results},status_code=200 if good else 503)

@app.api_route("/{path:path}",methods=["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"])
async def proxy(path:str,request:Request):
    base=target(request.url.path)
    if base is None: return JSONResponse({"detail":"接口不存在"},status_code=404)
    if request.method not in {"GET","HEAD","OPTIONS"} and request.headers.get("origin") not in config.for_service("identity").origins:
        return JSONResponse({"detail":"请求来源不受信任"},status_code=403)
    client=request.app.state.http
    url=httpx.URL(base+request.url.path).copy_with(query=request.url.query.encode("ascii"))
    # No automatic retries: a timed-out mutation may already have committed.
    headers=forwarded_headers(request.headers.raw)
    # A pooled HTTP client keeps a cookie jar. Always provide the inbound cookie header,
    # even when empty, so one browser can never inherit another browser's login cookie.
    if not any(key.lower()==b"cookie" for key,_ in headers): headers.append((b"cookie",b""))
    upstream=client.build_request(request.method,url,headers=headers,content=await request.body())
    try:
        response=await client.send(upstream,stream=True)
    except httpx.TimeoutException:
        return JSONResponse({"detail":"服务响应超时，请核对操作结果后再重试"},status_code=504)
    except httpx.HTTPError:
        return JSONResponse({"detail":"目标服务暂不可用"},status_code=502)
    async def chunks():
        try:
            async for chunk in response.aiter_raw(): yield chunk
        finally: await response.aclose()
    result=StreamingResponse(chunks(),status_code=response.status_code,background=BackgroundTask(response.aclose))
    result.raw_headers=forwarded_headers(response.headers.raw)
    return result

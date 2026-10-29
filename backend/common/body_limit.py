"""Bound actual request bytes, including chunked requests without Content-Length."""
from starlette.responses import JSONResponse

class BodyLimitMiddleware:
    def __init__(self,app): self.app=app

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http" or scope["method"] in {"GET","HEAD","OPTIONS"}:
            return await self.app(scope,receive,send)
        path=scope["path"]
        limit=11*1024*1024 if (path.endswith("/materials/upload") or path=="/api/ai/extensions/skills") else (8*1024*1024 if path.startswith("/api/courses") else (65536 if path.startswith("/api/ai/") else 16384))
        if path=='/internal/execute': limit=100000
        if path=='/internal/agent-executions':limit=8*1024*1024
        headers=dict(scope.get("headers",[]))
        length=headers.get(b"content-length",b"")
        async def reject():
            await JSONResponse({"detail":"请求内容过大"},status_code=413,headers={"Cache-Control":"no-store"})(scope,receive,send)
        if length.isdigit() and int(length)>limit: return await reject()
        chunks=[];size=0
        while True:
            message=await receive()
            if message["type"]=="http.disconnect": return
            chunk=message.get("body",b"");size+=len(chunk)
            if size>limit: return await reject()
            chunks.append(chunk)
            if not message.get("more_body",False): break
        body=b"".join(chunks);chunks.clear();consumed=False
        async def replay():
            nonlocal consumed,body
            if consumed: return await receive()
            consumed=True
            result={"type":"http.request","body":body,"more_body":False}
            body=b""
            return result
        await self.app(scope,replay,send)

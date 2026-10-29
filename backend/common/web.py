from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from common.errors import BusinessError
from common.body_limit import BodyLimitMiddleware

def create_app(title, settings, engine=None):
    @asynccontextmanager
    async def lifespan(application):
        yield
        if engine is not None: engine.dispose()
    application=FastAPI(title=title,version="0.2.0",lifespan=lifespan)
    @application.middleware("http")
    async def browser_boundary(request: Request, call_next):
        # All browser writes must originate from an explicitly allowed frontend.
        # No wildcard CORS and no trust in an arbitrary Host or forwarded header.
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") not in settings.origins:
                return JSONResponse(status_code=403, content={"detail": "请求来源不受信任"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError):
        # FastAPI's default error details include raw input (including passwords).
        message = "输入格式不正确；用户名需为 3–64 字符，密码需为 8–128 字符" if request.url.path.startswith("/api/auth") else "输入格式不正确，请检查名称、题目、答案、内容长度及所属章节"
        if request.url.path.startswith("/api/preferences"):
            message="设置格式不正确：字号增量为 0–6 的整数，紧凑布局为布尔值，并需提供版本号"
        return JSONResponse(status_code=422, content={"detail": message})

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logging.getLogger(__name__).error("Database request failed (%s)", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "数据库暂不可用，请确认服务与迁移状态"})


    @application.exception_handler(BusinessError)
    async def business_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail":exc.detail})
    application.add_middleware(BodyLimitMiddleware)
    return application

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .database import engine
from .logging_config import configure_logging, get_logger
from .migrate import migration_status, run_migrations
from .routers import annotations, documents, replies
from .storage import get_storage

settings = get_settings()
configure_logging(settings.log_level, settings.resolved_log_format)
log = get_logger("contract.app")


def collect_readiness() -> dict:
    """汇总就绪状态：数据库可连、迁移已到最新、存储可写。任一失败即未就绪。"""
    checks: dict = {}

    try:
        # SQLite 下 SELECT 1 不触碰库文件，必须真读一次系统表才算探活
        probe = (
            text("SELECT name FROM sqlite_master LIMIT 1")
            if settings.resolved_database_url.startswith("sqlite")
            else text("SELECT 1")
        )
        with engine.connect() as conn:
            conn.execute(probe)
        checks["database"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001 - 探针需要兜底所有失败
        checks["database"] = {"ok": False, "error": str(exc)}

    try:
        current, head = migration_status()
        ok = current == head
        checks["migrations"] = {"ok": ok, "current": current, "head": head}
        if not ok:
            checks["migrations"]["error"] = (
                "数据库迁移未完成，请执行: python -m app.migrate"
            )
    except Exception as exc:  # noqa: BLE001
        checks["migrations"] = {"ok": False, "error": str(exc)}

    try:
        get_storage().check_writable()
        checks["storage"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        checks["storage"] = {"ok": False, "error": str(exc)}

    return {"ok": all(c["ok"] for c in checks.values()), "checks": checks}


@asynccontextmanager
async def lifespan(_: FastAPI):
    for warning in settings.config_warnings():
        log.warning("config_warning: %s", warning)
    log.info(
        "startup",
        extra={
            "app_env": settings.app_env,
            "database_url": settings.resolved_database_url,
            "storage_dir": str(settings.resolved_storage_dir),
            "auto_migrate": settings.resolved_auto_migrate,
        },
    )
    try:
        get_storage()  # 确保存储目录存在；失败不阻断启动，readiness 会报出来
    except Exception:
        log.exception("storage_init_failed")

    if settings.resolved_auto_migrate:
        run_migrations()
        log.info("auto_migrate_done")

    readiness = collect_readiness()
    if readiness["ok"]:
        log.info("readiness_ok")
    else:
        # 不直接退出：进程保持存活以便探针暴露具体失败项，编排层据此重启/告警
        log.error("not_ready_on_startup", extra={"readiness": readiness})

    yield

    engine.dispose()
    log.info("shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.resolved_enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.resolved_enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """按 Content-Length 提前拒绝超大上传，避免把大文件读进内存。"""
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        limit = settings.max_upload_mb * 1024 * 1024
        if int(content_length) > limit:
            return JSONResponse(
                status_code=413,
                content={"detail": f"请求体超过大小限制（{settings.max_upload_mb}MB）"},
            )
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception(
            "request_failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    log.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["x-request-id"] = request_id
    return response


app.include_router(documents.router)
app.include_router(annotations.router)
app.include_router(replies.router)


@app.get("/api/health")
def health():
    """存活探针：只证明进程能响应，不做任何外部依赖检查。"""
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    """就绪探针：数据库可连 + 迁移到最新 + 存储可写，缺一不可。"""
    readiness = collect_readiness()
    status_code = 200 if readiness["ok"] else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if readiness["ok"] else "not_ready",
            "checks": readiness["checks"],
        },
    )

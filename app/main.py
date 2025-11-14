"""FastAPI application entry point."""
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import init_db, close_db, get_db
from app.middleware.metrics import setup_metrics
from app.middleware.audit import setup_audit_middleware
from app.middleware.audit import AuditMiddleware
from app.api.v1 import (
    auth,
    templates,
    checks,
    reports,
    files,
    tasks,
    users,
    roles,
    schedules,
    webhooks,
    audit,
    integrations,
    brigades,
    meta,
    demo,
    dashboards,
)
from app.routing.encrypted_route import EncryptedAPIRoute


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    setup_metrics(app)
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.router.route_class = EncryptedAPIRoute

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware
app.add_middleware(AuditMiddleware)

# Static files for HTML panels
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass  # Static directory might not exist in all environments


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve index.html at root."""
    try:
        from pathlib import Path
        index_path = Path("static/index.html")
        if index_path.exists():
            return index_path.read_text(encoding="utf-8")
    except Exception:
        pass
    return """
    <html>
        <head><title>MantaQC API</title></head>
        <body>
            <h1>MantaQC API</h1>
            <p>API доступен на <a href="/docs">/docs</a></p>
            <p><a href="/static/admin.html">Admin Panel</a> | <a href="/static/user.html">User Panel</a></p>
        </body>
    </html>
    """

# Apply encrypted route wrapper to API routers
for api_router in (
    auth.router,
    templates.router,
    checks.router,
    reports.router,
    files.router,
    tasks.router,
    users.router,
    roles.router,
    schedules.router,
    brigades.router,
    webhooks.router,
    audit.router,
    integrations.router,
    demo.router,
    dashboards.router,
):
    api_router.route_class = EncryptedAPIRoute

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(
    templates.router, prefix=f"{settings.API_V1_PREFIX}/templates", tags=["templates"]
)
app.include_router(checks.router, prefix=f"{settings.API_V1_PREFIX}/checks", tags=["checks"])
app.include_router(
    reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["reports"]
)
app.include_router(files.router, prefix=f"{settings.API_V1_PREFIX}/files", tags=["files"])
app.include_router(tasks.router, prefix=f"{settings.API_V1_PREFIX}/tasks", tags=["tasks"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["users"])
app.include_router(roles.router, prefix=f"{settings.API_V1_PREFIX}/roles", tags=["roles"])
app.include_router(
    schedules.router, prefix=f"{settings.API_V1_PREFIX}/schedules", tags=["schedules"]
)
app.include_router(
    brigades.router, prefix=f"{settings.API_V1_PREFIX}/brigades", tags=["brigades"]
)
app.include_router(meta.router, prefix=f"{settings.API_V1_PREFIX}/meta", tags=["meta"])
app.include_router(demo.router, prefix=f"{settings.API_V1_PREFIX}/demo", tags=["demo"])
app.include_router(
    webhooks.router, prefix=f"{settings.API_V1_PREFIX}/webhooks", tags=["webhooks"]
)
app.include_router(audit.router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["audit"])
app.include_router(
    integrations.router,
    prefix=f"{settings.API_V1_PREFIX}/integrations",
    tags=["integrations"],
)
app.include_router(
    dashboards.router,
    prefix=f"{settings.API_V1_PREFIX}/dashboards",
    tags=["dashboards"],
)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    from app.database import engine
    from app.services.storage_service import storage_service
    import redis
    from app.config import settings
    
    health_status = {
        "status": "ok",
        "checks": {
            "database": "unknown",
            "redis": "unknown",
            "s3": "unknown",
        }
    }
    
    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute(select(1))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check S3
    try:
        storage_service.file_exists("health-check")
        health_status["checks"]["s3"] = "ok"
    except Exception as e:
        health_status["checks"]["s3"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


"""
Office DMS - FastAPI Main Application
Entry point with middleware, exception handlers, and route registration.
"""
import time
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import init_database, get_db_status, SessionLocal
from app.core.logging import get_logger
from app.core.celery_app import celery_app
from app.core.storage import storage_manager
from app.core.rate_limiter import rate_limit_middleware
from app.api.dependencies import get_optional_user
from app.api.routes import auth, documents, search, sop, reminders, audit, admin, realtime
from app.api.routes import analytics, admin_activity, auth_2fa, permissions, reports
from app.api.routes import settings as settings_routes
from app.api.routes import workspace, workspace_files
from app.routes import analysis, preview, realtime_updates, document_versions, advanced_reports, rate_limiting, external_integrations
# from app.api.routes import tags, rules, templates  # Temporarily disabled due to missing dependencies
# from app.api.routes import versions, integrations, monitoring
# from app.api import webhooks  # Temporarily disabled
from app.models.database import User

logger = get_logger(__name__)

# =============================================================================
# Application Factory
# =============================================================================
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Office DMS - AI Document Management System",
        description="""
        Enterprise-grade local AI document management system for logistics,
        customs clearance, and office workflow automation.

        Features:
        - OCR (including Myanmar language)
        - Document classification (Invoice, BL, NRC, FDA, etc.)
        - Duplicate detection
        - SOP tracking
        - ETA/follow-up reminders
        - Full audit trail
        - Role-based access control
        """,
        version="1.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
    )

    # =============================================================================
    # Middleware
    # =============================================================================
    # CORS - Validate origins from environment
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8000,http://localhost:5173')
    cors_origins_list = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]
    
    # In production, require CORS_ORIGINS to be set (not default)
    if settings.ENVIRONMENT == "production" and cors_origins == 'http://localhost:3000,http://localhost:8000,http://localhost:5173':
        logger.warning("⚠️  PRODUCTION MODE: Using default CORS origins. Set CORS_ORIGINS environment variable!")
    
    # In debug mode, allow all for development convenience
    if settings.DEBUG:
        cors_origins_list = ["*"]
    
    logger.info(f"CORS origins: {cors_origins_list}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_list,
        allow_credentials=True if cors_origins_list != ["*"] else False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session with secure cookie settings
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,  # Convert days to seconds
        session_cookie="refresh_token",
        same_site="strict",
        https_only=settings.ENVIRONMENT == "production",  # Secure cookie only in production
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_request_timing(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        # Log slow requests
        if duration > 5.0:
            logger.warning(f"Slow request: {request.method} {request.url.path} took {duration:.2f}s")

        return response

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req_{time.time():.6f}")
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Rate limiting middleware
    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        return await rate_limit_middleware(request, call_next)

    # =============================================================================
    # Exception Handlers
    # =============================================================================
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler - never exposes stack traces."""
        logger.error(f"Unhandled exception: {exc}")

        if settings.DEBUG:
            detail = str(exc)
        else:
            detail = "An internal server error occurred. Please try again later."

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": detail,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )

    # =============================================================================
    # Static Files & Templates
    # =============================================================================
    static_path = Path(__file__).resolve().parent / "static"
    templates_path = Path(__file__).resolve().parent / "templates"

    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    templates = Jinja2Templates(directory=str(templates_path))

    # =============================================================================
    # API Routes
    # =============================================================================
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
    app.include_router(search.router, prefix="/api/search", tags=["Search"])
    app.include_router(sop.router, prefix="/api/sop", tags=["SOP"])
    app.include_router(reminders.router, prefix="/api/reminders", tags=["Reminders"])
    app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
    app.include_router(realtime.router, prefix="/api/realtime", tags=["Real-time"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])
    app.include_router(workspace.router)
    app.include_router(workspace_files.router)
    app.include_router(analytics.router, prefix="/api/admin/analytics", tags=["Analytics"])
    app.include_router(admin_activity.router, prefix="/api/admin/activity", tags=["Admin Activity"])
    app.include_router(auth_2fa.router, prefix="/api/2fa", tags=["2FA Authentication"])
    app.include_router(permissions.router, prefix="/api/permissions", tags=["Permissions"])
    app.include_router(reports.router, prefix="/api/admin/reports", tags=["Reports"])
    app.include_router(analysis.router, tags=["Analysis"])
    app.include_router(preview.router, tags=["Preview"])
    app.include_router(realtime_updates.router, tags=["Real-time Updates"])
    app.include_router(document_versions.router, tags=["Document Versions"])
    app.include_router(advanced_reports.router, tags=["Advanced Reports"])
    app.include_router(rate_limiting.router, tags=["Rate Limiting"])
    app.include_router(external_integrations.router, tags=["External Integrations"])
    
    # =============================================================================
    # Metrics Endpoint
    # =============================================================================
    app.mount("/metrics", make_asgi_app(get_prometheus_metrics().registry))
    
    # Temporarily disabled due to missing dependencies
    # app.include_router(tags.router, prefix="/api/tags", tags=["Tags"])
    # app.include_router(rules.router, prefix="/api/admin/rules", tags=["Automation Rules"])
    # app.include_router(templates.router, prefix="/api/templates", tags=["Template Library"])
    # app.include_router(versions.router, prefix="/api", tags=["Document Versions"])
    # app.include_router(integrations.router, prefix="/api/admin/integrations", tags=["External Integrations"])
    # app.include_router(monitoring.router, prefix="/api", tags=["System Monitoring"])
    # app.include_router(webhooks.router, prefix="/api", tags=["Webhooks"])

    # =============================================================================
    # HTML Pages (Jinja2 Templates + Vanilla JavaScript)
    # =============================================================================
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Redirect to dashboard or login."""
        return templates.TemplateResponse("login.html", {"request": request})

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        """Login page."""
        return templates.TemplateResponse("login.html", {"request": request})

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request, user=Depends(get_optional_user)):
        """Main dashboard (requires auth)."""
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
        })

    @app.get("/documents/pending", response_class=HTMLResponse)
    async def pending_page(request: Request, user=Depends(get_optional_user)):
        """Pending documents page."""
        return templates.TemplateResponse("pending.html", {
            "request": request,
            "user": user,
        })

    @app.get("/documents/{doc_id}", response_class=HTMLResponse)
    async def document_detail_page(request: Request, doc_id: int, user=Depends(get_optional_user)):
        """Document detail page."""
        return templates.TemplateResponse("document_detail.html", {
            "request": request,
            "doc_id": doc_id,
            "user": user,
        })

    @app.get("/settings/sources", response_class=HTMLResponse)
    async def settings_sources_page(request: Request, user=Depends(get_optional_user)):
        """Watch sources settings page (admin only)."""
        return templates.TemplateResponse("settings_sources.html", {
            "request": request,
            "user": user,
        })

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request, user=Depends(get_optional_user)):
        """Search page."""
        return templates.TemplateResponse("search.html", {
            "request": request,
            "user": user,
        })

    @app.get("/sop", response_class=HTMLResponse)
    async def sop_page(request: Request, user=Depends(get_optional_user)):
        """SOP tracker page."""
        return templates.TemplateResponse("sop.html", {
            "request": request,
            "user": user,
        })

    @app.get("/reminders", response_class=HTMLResponse)
    async def reminders_page(request: Request, user=Depends(get_optional_user)):
        """Reminders page."""
        return templates.TemplateResponse("reminders.html", {
            "request": request,
            "user": user,
        })

    @app.get("/audit", response_class=HTMLResponse)
    async def audit_page(request: Request, user=Depends(get_optional_user)):
        """Audit log page (admin only)."""
        return templates.TemplateResponse("audit.html", {
            "request": request,
            "user": user,
        })

    @app.get("/admin/activity", response_class=HTMLResponse)
    async def admin_activity_page(request: Request, user=Depends(get_optional_user)):
        """Admin activity heatmap page (admin only)."""
        return templates.TemplateResponse("admin_activity.html", {
            "request": request,
            "user": user,
        })

    @app.get("/admin/folders", response_class=HTMLResponse)
    async def admin_folder_permissions_page(request: Request, user=Depends(get_optional_user)):
        """Admin folder permissions page (admin only)."""
        return templates.TemplateResponse("admin_folder_permissions.html", {
            "request": request,
            "user": user,
        })

    @app.get("/reports", response_class=HTMLResponse)
    async def reports_page(request: Request, user=Depends(get_optional_user)):
        """Report generator page (admin only)."""
        return templates.TemplateResponse("reports.html", {
            "request": request,
            "user": user,
        })

    @app.get("/2fa-verify", response_class=HTMLResponse)
    async def two_fa_verify_page(request: Request):
        """2FA verification page."""
        return templates.TemplateResponse("2fa_verify.html", {
            "request": request,
        })

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request, user=Depends(get_optional_user)):
        """Settings page."""
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "user": user,
        })

    # =============================================================================
    # Health Check
    # =============================================================================
    @app.get("/health", tags=["System"])
    async def health_check():
        """
        Enhanced system health check endpoint.
        
        Checks PostgreSQL, Redis, Celery, and disk space.
        Returns detailed status with response times and error messages.
        """
        import psutil
        from app.core.redis_client import redis_client
        
        health = {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check PostgreSQL
        db_start = time.time()
        try:
            db_status = get_db_status()
            db_response_time = (time.time() - db_start) * 1000
            
            health["services"]["database"] = {
                "status": "healthy" if db_status.get("status") == "connected" else "unhealthy",
                "response_time_ms": round(db_response_time, 2),
                "details": db_status
            }
            
            if db_status.get("status") != "connected":
                health["status"] = "degraded"
        except Exception as e:
            db_response_time = (time.time() - db_start) * 1000
            health["services"]["database"] = {
                "status": "unhealthy",
                "response_time_ms": round(db_response_time, 2),
                "error": str(e)
            }
            health["status"] = "unhealthy"
        
        # Check Redis
        redis_start = time.time()
        try:
            if redis_client:
                redis_client.ping()
                redis_response_time = (time.time() - redis_start) * 1000
                
                health["services"]["redis"] = {
                    "status": "healthy" if redis_response_time < 500 else "degraded",
                    "response_time_ms": round(redis_response_time, 2)
                }
            else:
                health["services"]["redis"] = {
                    "status": "unhealthy",
                    "error": "Redis client not configured"
                }
                health["status"] = "degraded"
        except Exception as e:
            redis_response_time = (time.time() - redis_start) * 1000
            health["services"]["redis"] = {
                "status": "unhealthy",
                "response_time_ms": round(redis_response_time, 2),
                "error": str(e)
            }
            health["status"] = "degraded"
        
        # Check Celery
        celery_start = time.time()
        try:
            celery_app.control.ping(timeout=2)
            celery_response_time = (time.time() - celery_start) * 1000
            
            # Get worker stats
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            stats = inspect.stats()
            
            health["services"]["celery"] = {
                "status": "healthy",
                "response_time_ms": round(celery_response_time, 2),
                "active_workers": len(active_tasks) if active_tasks else 0
            }
        except Exception as e:
            celery_response_time = (time.time() - celery_start) * 1000
            health["services"]["celery"] = {
                "status": "unhealthy",
                "response_time_ms": round(celery_response_time, 2),
                "error": str(e)
            }
            health["status"] = "degraded"
        
        # Check Storage/MinIO
        storage_start = time.time()
        try:
            storage_status = storage_manager.get_stats()
            storage_response_time = (time.time() - storage_start) * 1000
            
            health["services"]["storage"] = {
                "status": "healthy",
                "response_time_ms": round(storage_response_time, 2),
                "details": storage_status
            }
        except Exception as e:
            storage_response_time = (time.time() - storage_start) * 1000
            health["services"]["storage"] = {
                "status": "unhealthy",
                "response_time_ms": round(storage_response_time, 2),
                "error": str(e)
            }
            health["status"] = "degraded"
        
        # Check Disk Space
        try:
            disk = psutil.disk_usage('/')
            disk_free_percent = (disk.free / disk.total) * 100
            
            disk_status = "healthy" if disk_free_percent > 10 else "degraded"
            if disk_free_percent < 5:
                disk_status = "unhealthy"
            
            health["services"]["disk"] = {
                "status": disk_status,
                "metrics": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "free_percent": round(disk_free_percent, 2)
                }
            }
            
            if disk_status == "unhealthy":
                health["status"] = "unhealthy"
        except Exception as e:
            health["services"]["disk"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Memory Usage
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            memory_status = "healthy" if memory_percent < 80 else "degraded"
            if memory_percent > 90:
                memory_status = "unhealthy"
            
            health["services"]["memory"] = {
                "status": memory_status,
                "metrics": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "free_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory_percent
                }
            }
            
            if memory_status == "unhealthy":
                health["status"] = "unhealthy"
        except Exception as e:
            health["services"]["memory"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        return health

    @app.get("/health/quick", tags=["System"])
    async def health_check_quick():
        """
        Quick health check endpoint (minimal checks).
        
        Only checks critical services (database and Redis) with minimal overhead.
        Useful for load balancer health checks.
        """
        from app.core.redis_client import redis_client
        
        # Quick database check
        try:
            get_db_status()
            db_ok = True
        except:
            db_ok = False
        
        # Quick Redis check
        try:
            if redis_client:
                redis_client.ping()
                redis_ok = True
            else:
                redis_ok = False
        except:
            redis_ok = False
        
        status = "healthy" if (db_ok and redis_ok) else "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error"
            }
        }

    @app.get("/api/config", tags=["System"])
    async def get_public_config():
        """Get public configuration (no sensitive data)."""
        return settings.to_dict()

    # =============================================================================
    # Admin User Seeding
    # =============================================================================
    def seed_admin_user():
        """Create default admin user if not exists."""
        try:
            db = SessionLocal()
            
            # Check if admin user already exists
            admin_user = db.query(User).filter(User.username == "admin").first()
            
            if admin_user:
                logger.info("✓ Admin user already exists - skipping seed")
                return
            
            # Create default admin user
            from app.core.security import hash_password
            
            admin_username = "admin"
            admin_password = "admin123"
            admin_email = "admin@example.com"
            
            # Hash the password using the security module
            hashed_password = hash_password(admin_password)
            
            # Create admin user
            new_admin = User(
                username=admin_username,
                email=admin_email,
                password_hash=hashed_password,
                role="admin",
                is_active=True,
                totp_enabled=False
            )
            
            db.add(new_admin)
            db.commit()
            
            logger.info(f"✓ Default admin user created: {admin_username}")
            logger.warning("⚠️  Please change the default admin password immediately!")
            logger.warning(f"   Default credentials: {admin_username} / {admin_password}")
            
        except Exception as e:
            logger.error(f"✗ Failed to seed admin user: {e}")
            # Don't raise exception - allow app to start even if seeding fails
        finally:
            db.close()

    # =============================================================================
    # Startup Event
    # =============================================================================
    @app.on_event("startup")
    async def startup_event():
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    async def startup_event():
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    async def startup_event():
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    async def startup_event():
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Initialize database and services on startup."""
        logger.info("=" * 60)
        logger.info("Office DMS starting up...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'sqlite'}")
        logger.info(f"Storage: {settings.MINIO_ENDPOINT}")
        logger.info("=" * 60)

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()

        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        init_database()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        seed_admin_user()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()

    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
        """Simple health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    return app


# Create application instance
app = create_app()
# Create application instance
app = create_app()
# Create application instance
app = create_app()
# Create application instance
app = create_app()
app = create_app()
app = create_app()
app = create_app()

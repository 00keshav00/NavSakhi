import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.config.logging_config import logger
from app.db.connection import connect_to_mongo, close_mongo_connection, get_database
from app.db.init_db import initialize_database

_prewarm_status = {
    "status": "pending",
    "completed_at": None,
    "error": None,
}

async def _async_startup_db_init():
    """
    Background asynchronous database initializer.
    Performs ping, index creation, and local development user seeding
    without delaying Uvicorn port binding on cloud runtimes (e.g., Render).
    """
    try:
        await initialize_database()

        # Ensure default local development test account exists strictly in non-production environments
        if settings.environment.lower() in ["development", "dev", "local", "test"]:
            try:
                from app.repositories.user_repository import UserRepository
                from app.services.user_service import UserService
                from app.schemas.user_schemas import UserCreate
                db = get_database()
                if db is not None:
                    user_repo = UserRepository(db)
                    existing = await user_repo.get_by_email("testuser@example.com")
                    if not existing:
                        user_service = UserService(user_repo)
                        await user_service.register_user(UserCreate(
                            username="testuser",
                            email="testuser@example.com",
                            password="password123"
                        ))
                        logger.info("Seeded default local test account: testuser@example.com")
            except Exception as e:
                logger.warning(f"Could not seed local test user: {e}")
    except Exception as e:
        logger.error(f"Background database initialization encountered error: {e}")

    # Safe sequential pre-warming of singletons during background initialization
    # Eliminates 19-24s first-request cold-start latency under free-tier limits without blocking port binding or /health/ready
    global _prewarm_status
    _prewarm_status["status"] = "in_progress"
    try:
        logger.info("Starting background singletons pre-warm...")
        from app.ml.predictor import get_ml_safety_predictor
        get_ml_safety_predictor()
        await asyncio.sleep(0.05)

        from app.intelligence.journey.transit_validator import global_validator, global_index
        from app.intelligence.journey.transit_graph import global_metro_graph, global_suburban_graph
        await asyncio.sleep(0.05)

        from app.intelligence.journey.schedule_engine import global_schedule_engine
        from app.intelligence.journey.fare_engine import global_fare_engine
        await asyncio.sleep(0.05)

        from app.intelligence.journey.multimodal_router import global_multimodal_router
        await asyncio.sleep(0.05)

        from app.services.autocomplete_service import global_autocomplete_service
        global_autocomplete_service.warm_cache()
        _prewarm_status["status"] = "completed"
        import time
        _prewarm_status["completed_at"] = time.time()
        logger.info("Background singletons pre-warm complete.")
    except Exception as e:
        _prewarm_status["status"] = "failed"
        _prewarm_status["error"] = str(e)
        logger.warning(f"Background singletons pre-warm non-fatal error: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}...")
    await connect_to_mongo()
    db_init_task = asyncio.create_task(_async_startup_db_init())

    yield
    # Shutdown actions
    logger.info(f"Shutting down {settings.app_name}...")
    if not db_init_task.done():
        db_init_task.cancel()
        try:
            await db_init_task
        except asyncio.CancelledError:
            pass
    await close_mongo_connection()

from app.api.v1.router import api_router
from app.api.handlers import register_exception_handlers
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Enable CORS for frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register API routes
app.include_router(api_router, prefix="/api/v1")

from app.api.websockets.emergency_ws import ws_router as emergency_ws_router
from app.api.websockets.journey_ws import router as journey_ws_router

app.include_router(emergency_ws_router, prefix="/api/v1/ws")
app.include_router(journey_ws_router, prefix="/api/v1/ws/journey")

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Backend health check endpoint.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "prewarm": _prewarm_status["status"],
    }

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness probe validating that spatial companion stores are built,
    accessible, and valid for bounded-memory production route scoring.
    """
    from fastapi.responses import JSONResponse
    from app.intelligence.journey.spatial_matcher import validate_companion_stores
    valid, reason = validate_companion_stores()
    if not valid:
        if settings.is_production:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "reason": reason}
            )
        else:
            return JSONResponse(
                status_code=200,
                content={"status": "degraded_dev_mode", "reason": reason}
            )
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "stores": "verified"}
    )

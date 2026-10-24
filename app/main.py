from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.config.logging_config import logger
from app.db.connection import connect_to_mongo, close_mongo_connection
from app.db.init_db import initialize_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}...")
    await connect_to_mongo()
    await initialize_database()
    
    # Ensure default local development test account exists strictly in non-production environments
    if settings.environment.lower() in ["development", "dev", "local", "test"]:
        try:
            from app.db.connection import get_database
            from app.repositories.user_repository import UserRepository
            from app.services.user_service import UserService
            from app.schemas.user_schemas import UserCreate
            user_repo = UserRepository(get_database())
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
    
    yield
    # Shutdown actions
    logger.info(f"Shutting down {settings.app_name}...")
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
@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """
    Authoritative backend health check endpoint.
    Serves both /health and /api/v1/health for compatibility with all monitor types.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


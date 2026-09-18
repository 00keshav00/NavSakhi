from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.config.logging_config import logger
from app.db.connection import connect_to_mongo, close_mongo_connection
from app.db.init_db import initialize_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info(f"Starting {settings.app_name}...")
    await connect_to_mongo()
    await initialize_database()
    
    # from app.auto_audit import trigger_audit
    # trigger_audit()
    
    # from app.doc_generator import trigger_doc_gen
    # trigger_doc_gen()
    
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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

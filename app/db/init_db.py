from app.db.connection import get_database
from app.config.logging_config import logger
from pymongo import ASCENDING, DESCENDING, GEOSPHERE

async def initialize_database():
    """
    Initializes database collections and indexes.
    """
    logger.info("Initializing database...")
    db = get_database()
    if db is None:
        logger.error("Database connection is not established.")
        return

    try:
        await db.command("ping")
        logger.info("Database ping successful.")
        await create_indexes(db)
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.error(f"Database ping or initialization failed: {e}")

async def create_indexes(db):
    """
    Creates MongoDB indexes for collections.
    """
    logger.info("Creating indexes...")
    
    # Users Indexes
    await db.users.create_index([("email", ASCENDING)], unique=True)
    
    # Journeys Indexes
    await db.journeys.create_index([("user_id", ASCENDING)])
    await db.journeys.create_index([("status", ASCENDING)])
    await db.journeys.create_index([("created_at", DESCENDING)])

    # Community Reports Indexes
    # 2dsphere index for geospatial queries
    await db.community_reports.create_index([("location", GEOSPHERE)])
    await db.community_reports.create_index([("created_at", DESCENDING)])
    await db.community_reports.create_index([("is_active", ASCENDING)])

    # Chat Sessions Indexes
    await db.chat_sessions.create_index([("user_id", ASCENDING)])
    await db.chat_sessions.create_index([("updated_at", DESCENDING)])

    logger.info("Indexes created successfully.")

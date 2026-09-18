from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings
from app.config.logging_config import logger

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db_instance.client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
    db_instance.db = db_instance.client[settings.database_name]
    logger.info("Connected to MongoDB.")

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_instance.client:
        db_instance.client.close()
    logger.info("MongoDB connection closed.")

def get_database():
    return db_instance.db

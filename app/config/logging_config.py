import logging
import sys
from app.config.settings import settings

def setup_logging():
    log_level = logging.DEBUG if settings.debug else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("backend.log")
        ]
    )
    
    logger = logging.getLogger(settings.app_name)
    logger.info(f"Logging initialized at {logging.getLevelName(log_level)} level.")
    return logger

logger = setup_logging()

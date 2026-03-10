import logging
import sys
from logging.handlers import RotatingFileHandler
from app.core.config import settings

def setup_logger():
    logger = logging.getLogger(settings.APP_NAME)
    
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s:%(lineno)d] - %(message)s"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File Handler (10MB 로테이션, 최대 5개 백업)
    file_handler = RotatingFileHandler(
        filename=f"{settings.DATA_DIR}/app.log", 
        encoding="utf-8",
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

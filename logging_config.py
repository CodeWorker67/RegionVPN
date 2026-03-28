import logging
from loguru import logger

time_format = "{time:YYYY-MM-DD!UTC}"
logger.add(f'logs/{time_format}_log.log', format='[{level}]\t[{time}] [{file}]\t: {message}', rotation='00:00')
logger_update: logging.Logger = logging.getLogger(__name__)
logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )

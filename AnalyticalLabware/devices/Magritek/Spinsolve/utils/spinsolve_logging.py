import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime


now = datetime.now().strftime("%d%m%y")

LEVEL = logging.INFO
HERE = os.path.abspath(".")
LOG_PATH = os.path.join(HERE, "spinsolve_logs")
NAME = "spinsolve"
MAX_BYTES_SIZE = 3 * 1000 * 1000  # 2 MB is enough to store ~30 spectra records
BACKUP_COUNT = 5  # will give in total logs for ~150 spectra records


def get_logger():
    """Returns logger object with predefined console and file handlers."""

    logger = logging.getLogger(NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []  # resetting

    ff = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # console handler
    ch = logging.StreamHandler()
    ch.setLevel(LEVEL)
    ch.setFormatter(ff)

    # file handler
    os.makedirs(LOG_PATH, exist_ok=True)
    file_path = os.path.join(LOG_PATH, f"{NAME}-{now}.log")
    fh = RotatingFileHandler(
        filename=file_path, mode="a", maxBytes=MAX_BYTES_SIZE, backupCount=BACKUP_COUNT
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(ff)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger

import logging
from datetime import datetime

now = datetime.now().strftime('%d%m%y')

LEVEL = logging.INFO
NAME = 'spinsolve'

def get_logger():

    logger = logging.getLogger(NAME)
    logger.setLevel(logging.DEBUG)

    ff = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(LEVEL)
    ch.setFormatter(ff)

    fh = logging.FileHandler(f'{NAME}-{now}.log', mode='a')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(ff)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger

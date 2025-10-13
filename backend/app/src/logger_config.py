import logging

import uvicorn

FORMAT = "%(levelprefix)s %(asctime)s [%(threadName)s] [%(name)s] %(message)s"


def get_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = uvicorn.logging.DefaultFormatter(
            FORMAT, datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

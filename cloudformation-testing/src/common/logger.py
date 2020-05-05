import logging
import sys

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_logger(logger_name, log_level="DEBUG"):
    name = logger_name or __name__
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.getLevelName(log_level))
        logger.addHandler(get_console_handler())
        # with this pattern, it's rarely necessary to propagate the error up to parent
        logger.propagate = False
    return logger

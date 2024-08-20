import logging
import colorlog

def setup_logger(level: str = "WARNING"):
    logger = logging.getLogger()
    if level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        raise ValueError("Invalid logging level. Please choose from 'DEBUG', 'INFO', or 'WARNING'.")

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))
    logger.addHandler(handler)

    return logger

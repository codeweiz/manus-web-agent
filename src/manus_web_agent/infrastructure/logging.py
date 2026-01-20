import logging


def setup_logging():
    """设置日志系统"""

    # root logger
    root_logger = logging.getLogger()

    # set root level
    log_level = logging.INFO
    root_logger.setLevel(log_level)

    # console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    # formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    # add handler
    root_logger.addHandler(console_handler)

    # Log init completed
    root_logger.info("Logging system initialized")


setup_logging()

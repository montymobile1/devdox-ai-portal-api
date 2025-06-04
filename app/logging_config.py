import logging
from logging.handlers import RotatingFileHandler

from app.middlewares.log_trace_context import RequestContextLogFilter


def setup_logging():
    """
    Configures logging for the entire application.
    Logs messages to console and to a rotating log file.
    """
    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate logs during development when using `uvicorn --reload`.
    # Each reload reinitializes the logger and adds new handlers unless cleared first.
    if logger.hasHandlers():
        logger.handlers.clear()

    # Add custom filter to inject trace_id and user_id
    log_filter = RequestContextLogFilter()

    # Create formatter
    formatter = logging.Formatter(
        fmt=(
            "[%(asctime)s] [%(levelname)s] [%(name)s] "
            "[thread=%(threadName)s, pid=%(process)d] "
            "[trace_id=%(trace_id)s, user_id=%(user_id)s] - %(message)s"
        ),
    )

    # Console handler for logging to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(log_filter)
    logger.addHandler(console_handler)

    # File handler with rotating log (max 5MB per file, keeping 3 backup files)
    file_handler = RotatingFileHandler(
        "app.log", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(log_filter)
    logger.addHandler(file_handler)

    # Optionally, create more handlers (e.g., for error logs, different log levels, etc.)
    error_handler = logging.FileHandler("error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    file_handler.addFilter(log_filter)
    logger.addHandler(error_handler)

    return logger

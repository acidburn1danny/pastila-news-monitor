"""Central logging configuration for Pastila Scout."""

import logging
import sys

from pastila_scout import __version__

LOGGER_NAME = "pastila_scout"
LOG_FORMAT = f"%(asctime)s %(levelname)s %(name)s version={__version__} %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
_HANDLER_MARKER = "_pastila_scout_console_handler"


def configure_logging(verbose: bool = False) -> None:
    """Configure one application console handler writing logs to stderr."""

    level = logging.DEBUG if verbose else logging.INFO
    application_logger = logging.getLogger(LOGGER_NAME)
    application_logger.setLevel(level)
    application_logger.propagate = False

    handlers = [
        handler
        for handler in application_logger.handlers
        if getattr(handler, _HANDLER_MARKER, False)
    ]
    if handlers:
        handler = handlers[0]
        for duplicate in handlers[1:]:
            application_logger.removeHandler(duplicate)
            duplicate.close()
        if handler.stream is not sys.stderr:
            application_logger.removeHandler(handler)
            handler.close()
            handler = logging.StreamHandler(sys.stderr)
            setattr(handler, _HANDLER_MARKER, True)
            application_logger.addHandler(handler)
    else:
        handler = logging.StreamHandler(sys.stderr)
        setattr(handler, _HANDLER_MARKER, True)
        handler.setLevel(level)
        application_logger.addHandler(handler)

    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

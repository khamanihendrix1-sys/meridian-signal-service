from __future__ import annotations

import logging

from structlog import configure, get_logger
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import LoggerFactory

from meridian.settings import Settings


def configure_structlog(settings: Settings) -> None:
    """Configure structured logging for the application."""
    logging.basicConfig(level=settings.log_level)
    configure(
        processors=[
            TimeStamper(fmt="iso"),
            JSONRenderer(sort_keys=True),
        ],
        logger_factory=LoggerFactory(),
    )


logger = get_logger()

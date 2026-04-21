from __future__ import annotations

"""Logging setup for the Agent process."""

import logging


def configure_logging() -> None:
    """Configure a simple stdout-friendly log format for local and Docker runs."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

"""Async MySQL runtime wrapper.

The repository can use this wrapper to create SQLAlchemy async engines when the
runtime dependencies are installed.  The wrapper is intentionally tiny so it is
safe to construct from environment variables and easy to replace in tests.
"""

from __future__ import annotations


from dataclasses import dataclass


@dataclass
class MySQLDatabase:
    """Container for an async SQLAlchemy DSN."""

    dsn: str

    def available(self) -> bool:
        """Return whether a DSN was configured."""
        return bool(self.dsn)

    def create_engine(self):
        """Create an async SQLAlchemy engine, or `None` if unavailable."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
        except Exception:
            return None
        if not self.dsn:
            return None
        return create_async_engine(self.dsn, pool_pre_ping=True, future=True)

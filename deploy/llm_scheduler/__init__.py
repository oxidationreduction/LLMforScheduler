"""Verifier-backed industrial scheduling package."""

from .api import ENGINE_VERSION, SCHEMA_VERSION, solve, solve_json, solve_legacy

__all__ = ["ENGINE_VERSION", "SCHEMA_VERSION", "solve", "solve_json", "solve_legacy"]
__version__ = ENGINE_VERSION

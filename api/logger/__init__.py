"""
Logger API Module for JSPro PowerDesk
Handles historical data logs from Redis and SQLite storage
"""

from .api_logger import logger_bp

__all__ = ['logger_bp']
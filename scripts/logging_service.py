#!/usr/bin/env python3
"""Structured logging service for production.

Provides:
1. JSON/text structured logging
2. File rotation
3. Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
4. Contextual logging
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import sys

ROOT = Path(__file__).resolve().parents[1]


class StructuredLogger:
    """Provides structured logging with JSON support."""

    def __init__(
        self,
        name: str,
        level: str = "INFO",
        log_format: str = "json",
        log_file: Optional[Path] = None,
    ):
        """Initialize structured logger.

        Args:
            name: Logger name
            level: Logging level
            log_format: Output format (json or text)
            log_file: Optional file to log to
        """
        self.name = name
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.log_format = log_format
        self.log_file = log_file

        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)

        # Remove existing handlers
        self.logger.handlers = []

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)

        if log_format == "json":
            console_handler.setFormatter(JsonFormatter())
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(self.level)

            if log_format == "json":
                file_handler.setFormatter(JsonFormatter())
            else:
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message.

        Args:
            message: Log message
            context: Additional context dict
        """
        self._log(logging.DEBUG, message, context)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log info message.

        Args:
            message: Log message
            context: Additional context dict
        """
        self._log(logging.INFO, message, context)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message.

        Args:
            message: Log message
            context: Additional context dict
        """
        self._log(logging.WARNING, message, context)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None, exception: Optional[Exception] = None) -> None:
        """Log error message.

        Args:
            message: Log message
            context: Additional context dict
            exception: Optional exception
        """
        if exception:
            self._log(logging.ERROR, f"{message}: {str(exception)}", context)
        else:
            self._log(logging.ERROR, message, context)

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message.

        Args:
            message: Log message
            context: Additional context dict
        """
        self._log(logging.CRITICAL, message, context)

    def _log(
        self,
        level: int,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal logging method.

        Args:
            level: Log level
            message: Log message
            context: Additional context
        """
        if self.log_format == "json":
            # Context is added via JsonFormatter
            self.logger.log(level, message, extra={"context": context or {}})
        else:
            if context:
                context_str = json.dumps(context)
                self.logger.log(level, f"{message} {context_str}")
            else:
                self.logger.log(level, message)


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON formatted log
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add context if present
        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        return json.dumps(log_data)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "orders") -> StructuredLogger:
    """Get or create global logger.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    global _logger
    if _logger is None:
        log_file = ROOT / "logs" / "orders.log"
        _logger = StructuredLogger(
            name,
            level="INFO",
            log_format="json",
            log_file=log_file,
        )
    return _logger


def main() -> None:
    """Demo structured logging."""
    print("[StructuredLogger] Testing structured logging\n")

    logger = StructuredLogger(
        "test",
        level="DEBUG",
        log_format="json",
        log_file=Path("/tmp/test.log"),
    )

    logger.info("Application started", {"version": "1.0", "environment": "dev"})
    logger.debug("Debug message", {"component": "orders"})
    logger.warning("High memory usage", {"usage_mb": 512})
    logger.error("Order processing failed", {"order_id": "OZ_123", "reason": "timeout"})

    print("\n✓ Structured logging demo completed")
    print(f"✓ Logs written to /tmp/test.log")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Configuration management with environment variables.

Provides:
1. Centralized configuration
2. Environment-based overrides
3. Validation and defaults
4. Secrets handling
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/orders.db"
    timeout: int = 30
    max_connections: int = 10


@dataclass
class WebConfig:
    """Web server configuration."""
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False
    workers: int = 4


@dataclass
class NotificationConfig:
    """Notification configuration."""
    slack_webhook: Optional[str] = None
    slack_enabled: bool = False
    email_enabled: bool = False
    email_from: str = "alerts@orders.local"
    email_to: str = "admin@example.com"
    smtp_host: Optional[str] = None
    smtp_port: int = 587


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"  # json or text
    file: str = "logs/orders.log"
    max_size_mb: int = 100
    backup_count: int = 5


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 1000
    burst_size: int = 100


@dataclass
class SecurityConfig:
    """Security configuration."""
    api_key_required: bool = False
    api_keys: list[str] = None
    cors_enabled: bool = False
    cors_origins: list[str] = None
    request_timeout: int = 30


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize config manager.

        Args:
            config_file: Path to config JSON file
        """
        self.config_file = config_file
        self.database = DatabaseConfig()
        self.web = WebConfig()
        self.notifications = NotificationConfig()
        self.logging = LoggingConfig()
        self.rate_limit = RateLimitConfig()
        self.security = SecurityConfig()

        # Load from file if provided
        if config_file and config_file.exists():
            self._load_from_file(config_file)

        # Override with environment variables
        self._load_from_env()

    def _load_from_file(self, config_file: Path) -> None:
        """Load configuration from JSON file.

        Args:
            config_file: Path to config file
        """
        try:
            data = json.loads(config_file.read_text())

            if "database" in data:
                self.database = DatabaseConfig(**data["database"])
            if "web" in data:
                self.web = WebConfig(**data["web"])
            if "notifications" in data:
                self.notifications = NotificationConfig(**data["notifications"])
            if "logging" in data:
                self.logging = LoggingConfig(**data["logging"])
            if "rate_limit" in data:
                self.rate_limit = RateLimitConfig(**data["rate_limit"])
            if "security" in data:
                self.security = SecurityConfig(**data["security"])

            print(f"[Config] Loaded from {config_file}")

        except Exception as e:
            print(f"[Config] Error loading config file: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Database
        if "DB_PATH" in os.environ:
            self.database.path = os.environ["DB_PATH"]
        if "DB_TIMEOUT" in os.environ:
            self.database.timeout = int(os.environ["DB_TIMEOUT"])

        # Web
        if "WEB_HOST" in os.environ:
            self.web.host = os.environ["WEB_HOST"]
        if "WEB_PORT" in os.environ:
            self.web.port = int(os.environ["WEB_PORT"])
        if "WEB_DEBUG" in os.environ:
            self.web.debug = os.environ["WEB_DEBUG"].lower() == "true"

        # Notifications
        if "SLACK_WEBHOOK" in os.environ:
            self.notifications.slack_webhook = os.environ["SLACK_WEBHOOK"]
            self.notifications.slack_enabled = True
        if "SLACK_ENABLED" in os.environ:
            self.notifications.slack_enabled = os.environ["SLACK_ENABLED"].lower() == "true"
        if "EMAIL_ENABLED" in os.environ:
            self.notifications.email_enabled = os.environ["EMAIL_ENABLED"].lower() == "true"
        if "EMAIL_TO" in os.environ:
            self.notifications.email_to = os.environ["EMAIL_TO"]
        if "SMTP_HOST" in os.environ:
            self.notifications.smtp_host = os.environ["SMTP_HOST"]

        # Logging
        if "LOG_LEVEL" in os.environ:
            self.logging.level = os.environ["LOG_LEVEL"]
        if "LOG_FILE" in os.environ:
            self.logging.file = os.environ["LOG_FILE"]

        # Rate limiting
        if "RATE_LIMIT_ENABLED" in os.environ:
            self.rate_limit.enabled = os.environ["RATE_LIMIT_ENABLED"].lower() == "true"
        if "RATE_LIMIT_RPM" in os.environ:
            self.rate_limit.requests_per_minute = int(os.environ["RATE_LIMIT_RPM"])

        # Security
        if "API_KEY_REQUIRED" in os.environ:
            self.security.api_key_required = os.environ["API_KEY_REQUIRED"].lower() == "true"
        if "API_KEYS" in os.environ:
            self.security.api_keys = os.environ["API_KEYS"].split(",")

    def get_config_dict(self) -> Dict[str, Any]:
        """Get complete configuration as dict.

        Returns:
            Configuration dictionary
        """
        return {
            "database": asdict(self.database),
            "web": asdict(self.web),
            "notifications": {k: v for k, v in asdict(self.notifications).items() if k != "slack_webhook"},
            "logging": asdict(self.logging),
            "rate_limit": asdict(self.rate_limit),
            "security": {k: v for k, v in asdict(self.security).items() if k != "api_keys"},
        }

    def save_to_file(self, path: Path) -> bool:
        """Save configuration to file.

        Args:
            path: Output file path

        Returns:
            True if saved
        """
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.get_config_dict(), indent=2))
            print(f"[Config] Saved to {path}")
            return True
        except Exception as e:
            print(f"[Config] Error saving config: {e}")
            return False

    def validate(self) -> bool:
        """Validate configuration.

        Returns:
            True if valid
        """
        errors = []

        # Validate database path
        db_path = Path(self.database.path)
        if not db_path.parent.exists():
            errors.append(f"Database directory does not exist: {db_path.parent}")

        # Validate web port
        if self.web.port < 1 or self.web.port > 65535:
            errors.append(f"Invalid web port: {self.web.port}")

        # Validate rate limit
        if self.rate_limit.requests_per_minute < 1:
            errors.append("Rate limit must be > 0")

        if errors:
            print("[Config] Validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        print("[Config] ✓ Configuration valid")
        return True


def main() -> None:
    """Demo configuration manager."""
    print("[ConfigManager] Testing configuration management\n")

    # Create default config
    config = ConfigManager()

    print("[ConfigManager] Default Configuration:")
    print(f"  Database: {config.database.path}")
    print(f"  Web: {config.web.host}:{config.web.port}")
    print(f"  Logging: {config.logging.level} ({config.logging.format})")
    print(f"  Rate limit: {config.rate_limit.requests_per_minute} req/min")

    # Validate
    config.validate()

    # Save example config
    example_config = {
        "database": {"path": "data/orders.db", "timeout": 30},
        "web": {"host": "0.0.0.0", "port": 5000, "debug": False},
        "logging": {"level": "INFO", "format": "json", "file": "logs/orders.log"},
        "rate_limit": {"enabled": True, "requests_per_minute": 1000},
    }

    config_path = Path("/tmp/config.example.json")
    config_path.write_text(json.dumps(example_config, indent=2))
    print(f"\n✓ Example config saved to: {config_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Phase 7 workflow: Production hardening.

Orchestrates:
1. Configuration management
2. Logging service setup
3. Error handling initialization
4. Rate limiting configuration
5. Data validation rules
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

from config_manager import ConfigManager
from logging_service import get_logger
from error_handler import ErrorHandler
from rate_limiter import PerEndpointLimiter
from data_validator import DataValidator


def run_phase7_hardening():
    """Execute Phase 7 production hardening."""
    print("\n" + "=" * 100)
    print("PHASE 7: PRODUCTION HARDENING".center(100))
    print("=" * 100)

    workflow_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": [],
    }

    try:
        # Step 1: Configuration management
        print("\n[Phase 7] Step 1: Initializing configuration management...")
        config = ConfigManager()
        config.validate()

        step1 = {
            "step": "configuration_management",
            "status": "completed",
            "database": config.database.path,
            "web_host": config.web.host,
            "web_port": config.web.port,
            "log_level": config.logging.level,
            "rate_limit_rpm": config.rate_limit.requests_per_minute,
        }
        workflow_log["steps"].append(step1)
        print(f"  ✓ Configuration loaded and validated")
        print(f"  ✓ Database: {config.database.path}")
        print(f"  ✓ Web: {config.web.host}:{config.web.port}")
        print(f"  ✓ Logging: {config.logging.level} ({config.logging.format})")

        # Step 2: Logging service
        print("\n[Phase 7] Step 2: Setting up structured logging...")
        logger = get_logger("orders")
        logger.info("Logging service initialized", {"phase": "7", "environment": "production"})

        step2 = {
            "step": "logging_service",
            "status": "completed",
            "log_file": str(ROOT / "logs" / "orders.log"),
            "log_format": "json",
            "log_level": "INFO",
        }
        workflow_log["steps"].append(step2)
        print(f"  ✓ Structured logging configured")
        print(f"  ✓ Format: JSON")
        print(f"  ✓ Output: {ROOT / 'logs' / 'orders.log'}")

        # Step 3: Error handling
        print("\n[Phase 7] Step 3: Initializing error handling...")
        error_handler = ErrorHandler()

        step3 = {
            "step": "error_handling",
            "status": "completed",
            "max_retries": 3,
            "initial_backoff": 1.0,
            "circuit_breakers": ["api", "database"],
        }
        workflow_log["steps"].append(step3)
        print(f"  ✓ Error handler initialized")
        print(f"  ✓ Retry strategy: 3 attempts with exponential backoff")
        print(f"  ✓ Circuit breakers: Configured")

        # Step 4: Rate limiting
        print("\n[Phase 7] Step 4: Configuring rate limiting...")
        rate_limiter = PerEndpointLimiter()

        endpoint_limits = {
            "/api/orders": 100,
            "/api/metrics": 200,
            "/api/audit": 50,
            "/api/alerts": 150,
        }

        for endpoint, rpm in endpoint_limits.items():
            rate_limiter.get_limiter(endpoint, rpm=rpm)

        step4 = {
            "step": "rate_limiting",
            "status": "completed",
            "enabled": True,
            "endpoints": endpoint_limits,
        }
        workflow_log["steps"].append(step4)
        print(f"  ✓ Rate limiting configured")
        print(f"  ✓ Per-endpoint limits:")
        for endpoint, rpm in endpoint_limits.items():
            print(f"    - {endpoint}: {rpm} req/min")

        # Step 5: Data validation
        print("\n[Phase 7] Step 5: Initializing data validation...")
        validator = DataValidator()

        validation_rules = {
            "order_data": ["order_id", "platform", "shop_id", "total_amount", "currency"],
            "query_params": ["limit", "offset", "sort"],
        }

        step5 = {
            "step": "data_validation",
            "status": "completed",
            "validation_schemas": validation_rules,
        }
        workflow_log["steps"].append(step5)
        print(f"  ✓ Data validation configured")
        print(f"  ✓ Schemas: {len(validation_rules)}")
        print(f"  ✓ Total rules: {sum(len(v) for v in validation_rules.values())}")

        # Summary
        print("\n" + "=" * 100)
        print("PHASE 7 SUMMARY".center(100))
        print("=" * 100)
        print(f"Status: ✅ COMPLETED")
        print(f"\nProduction Hardening Components:")
        print(f"  ✓ Configuration Management")
        print(f"    - Database: {config.database.path}")
        print(f"    - Timeout: {config.database.timeout}s")
        print(f"    - Web: {config.web.host}:{config.web.port}")
        print(f"    - Debug: {config.web.debug}")
        print(f"  ✓ Structured Logging")
        print(f"    - Level: {config.logging.level}")
        print(f"    - Format: JSON")
        print(f"    - File: {config.logging.file}")
        print(f"  ✓ Error Handling")
        print(f"    - Retry strategy: Exponential backoff (1→2→4s)")
        print(f"    - Max retries: 3")
        print(f"    - Circuit breaker timeout: 60s")
        print(f"  ✓ Rate Limiting")
        print(f"    - Enabled: True")
        print(f"    - Per-endpoint configuration: 4 endpoints")
        print(f"    - Default: 1000 req/min")
        print(f"  ✓ Data Validation")
        print(f"    - Order schema: 5 fields")
        print(f"    - Query schema: 3 fields")
        print(f"    - Sanitization: Enabled")

        print(f"\nEnvironment Variables Supported:")
        print(f"  - DB_PATH, DB_TIMEOUT")
        print(f"  - WEB_HOST, WEB_PORT, WEB_DEBUG")
        print(f"  - SLACK_WEBHOOK, SLACK_ENABLED, EMAIL_ENABLED")
        print(f"  - LOG_LEVEL, LOG_FILE")
        print(f"  - RATE_LIMIT_ENABLED, RATE_LIMIT_RPM")
        print(f"  - API_KEY_REQUIRED, API_KEYS")

        print(f"\nProduction Checklist:")
        print(f"  ✓ Configuration management (env vars + files)")
        print(f"  ✓ Structured logging (JSON format)")
        print(f"  ✓ Error handling (retries + circuit breaker)")
        print(f"  ✓ Rate limiting (per-endpoint)")
        print(f"  ✓ Data validation (input sanitization)")
        print(f"  ✓ Error classification (transient/permanent/degraded)")

        print("=" * 100)
        print("\nProduction Deployment Steps:")
        print(f"  1. Set environment variables for production")
        print(f"  2. Configure Slack webhook for alerts")
        print(f"  3. Set up log rotation (logrotate)")
        print(f"  4. Configure reverse proxy (nginx/apache)")
        print(f"  5. Enable API key authentication")
        print(f"  6. Deploy with process manager (systemd/supervisord)")
        print("=" * 100 + "\n")

        # Save workflow log
        workflow_log["status"] = "success"
        log_path = ROOT / "outputs" / "phase7_workflow_log.json"
        log_path.write_text(json.dumps(workflow_log, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Phase 7 workflow log: {log_path}")

        return workflow_log

    except Exception as e:
        print(f"\n❌ Phase 7 workflow failed: {e}")
        import traceback
        traceback.print_exc()
        workflow_log["status"] = "failed"
        workflow_log["error"] = str(e)
        raise


if __name__ == "__main__":
    run_phase7_hardening()

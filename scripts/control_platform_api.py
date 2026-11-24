#!/usr/bin/env python3
"""Codex Control Platform REST API - Handler orchestration and execution interface.

Exposes Phase 7 ActionHandlers through REST API for dashboard and external integration.
Implements routing, approval gates, health tracking, and audit logging.

Runs at http://127.0.0.1:8765
"""
from __future__ import annotations

import json
import logging
import hashlib
import uuid
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from action_handler_registry import ActionHandlerRegistry
from p0_control_integration import P0ControlIntegration
from p0_approval_ledger import (
    P0ApprovalLedgerManager,
    TaskApprovalRecord,
    TaskApprovalStatus,
    ApprovalGateConfig,
)
from health_tracker import HealthTracker, ExecutionMetric, ExecutionResult

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
registry = ActionHandlerRegistry()
ledger_manager = P0ApprovalLedgerManager()
health_tracker = HealthTracker()

# In-memory request tracking (for status checks before ledger persistence)
_request_cache: dict[str, dict[str, Any]] = {}


# ============================================================================
# API RESPONSE HELPERS
# ============================================================================

def success_response(data: Any, status_code: int = 200) -> tuple[dict, int]:
    """Format successful API response."""
    return {
        "status": "success",
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, status_code


def error_response(message: str, error_code: str, status_code: int = 400) -> tuple[dict, int]:
    """Format error API response."""
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, status_code


# ============================================================================
# HANDLER REGISTRY ENDPOINTS
# ============================================================================

def list_handlers():
    """List all registered Phase 7 handlers with metadata."""
    try:
        handlers = registry.list_handlers()
        return success_response({
            "total": len(handlers),
            "handlers": handlers,
        })
    except Exception as e:
        logger.error(f"Error listing handlers: {e}")
        return error_response(str(e), "HANDLER_LIST_ERROR", 500)


def get_handler_metadata(action_key: str):
    """Get metadata for a specific handler."""
    try:
        metadata = registry.get_metadata(action_key)
        if not metadata:
            return error_response(
                f"Handler not found: {action_key}",
                "HANDLER_NOT_FOUND",
                404
            )

        return success_response({
            "action_key": action_key,
            "metadata": metadata,
        })
    except Exception as e:
        logger.error(f"Error getting handler metadata: {e}")
        return error_response(str(e), "METADATA_ERROR", 500)


# ============================================================================
# EXECUTION ENDPOINTS
# ============================================================================

def execute_handler(action_key: str, payload: dict):
    """Execute a handler with optional approval gating.

    Request body:
    {
        "client_id": "client_xyz",
        "data": {...},
        "approval_required": true,
        "approvers": ["approver1@company.com", "approver2@company.com"]
    }
    """
    try:
        client_id = payload.get("client_id", "default_client")
        handler_data = payload.get("data", {})
        approval_required = payload.get("approval_required", True)
        approvers = payload.get("approvers", [])

        # Validate handler exists
        handler_class = registry.get_handler(action_key)
        if not handler_class:
            return error_response(
                f"Handler not found: {action_key}",
                "HANDLER_NOT_FOUND",
                404
            )

        # Generate task ID
        task_id = str(uuid.uuid4())

        # Instantiate handler
        handler = registry.instantiate_handler(action_key, client_id, handler_data)
        if not handler:
            return error_response(
                f"Failed to instantiate handler: {action_key}",
                "INSTANTIATION_ERROR",
                500
            )

        # Determine approval level from metadata
        metadata = registry.get_metadata(action_key)
        approval_level = metadata.get("approval_level", "P0-2")
        severity = _approval_level_to_severity(approval_level)

        # Create approval record
        approval_record = TaskApprovalRecord(
            task_id=task_id,
            approval_request_id=str(uuid.uuid4()),
            framework_context="Phase 24 PolicyGovernanceSystem",
            severity_level=severity,
            approvers_assigned=approvers or ["default_approver@company.com"],
        )

        # Cache request info
        _request_cache[task_id] = {
            "action_key": action_key,
            "client_id": client_id,
            "handler": handler,
            "approval_record": approval_record,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Execution request created: task_id={task_id}, action_key={action_key}")

        # If approval not required, execute immediately
        if not approval_required:
            return _execute_handler_internal(task_id, action_key)

        # Return task ID for approval flow
        return success_response({
            "task_id": task_id,
            "action_key": action_key,
            "approval_request_id": approval_record.approval_request_id,
            "status": approval_record.status.value,
            "approvers": approval_record.approvers_assigned,
            "severity": severity,
            "message": "Awaiting approval before execution",
        }, 202)  # 202 Accepted

    except Exception as e:
        logger.error(f"Error executing handler: {e}", exc_info=True)
        return error_response(str(e), "EXECUTION_ERROR", 500)


def _approval_level_to_severity(approval_level: str) -> int:
    """Convert approval level string to severity score."""
    levels = {
        "P0": 100,
        "P0-1": 95,
        "P0-2": 90,
        "P1": 70,
        "P2": 50,
    }
    return levels.get(approval_level, 50)


def _execute_handler_internal(task_id: str, action_key: str) -> tuple[dict, int]:
    """Internal handler execution with health tracking."""
    try:
        if task_id not in _request_cache:
            return error_response(
                f"Task not found: {task_id}",
                "TASK_NOT_FOUND",
                404
            )

        cached = _request_cache[task_id]
        handler = cached["handler"]
        approval_record: TaskApprovalRecord = cached["approval_record"]

        # Mark as executing
        approval_record.mark_executing()

        # Execute handler
        start_time = time.time()

        try:
            result = handler.execute(handler.data if hasattr(handler, 'data') else {})
            duration_ms = int((time.time() - start_time) * 1000)

            # Verify result
            verify_result = handler.verify(result) if hasattr(handler, 'verify') else {"valid": True}

            # Mark as completed
            approval_record.mark_completed()

            # Track health metrics
            action_type, platform = action_key.split("@") if "@" in action_key else (action_key, "unknown")
            metric = ExecutionMetric(
                task_id=task_id,
                action_type=action_type,
                platform=platform,
                result=ExecutionResult.SUCCESS,
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                p02_status="approved",
                verification_passed=verify_result.get("valid", True),
            )
            health_tracker.record_execution(metric)

            logger.info(f"Handler executed successfully: task_id={task_id}, duration={duration_ms}ms")

            return success_response({
                "task_id": task_id,
                "action_key": action_key,
                "status": "completed",
                "result": result,
                "verify_result": verify_result,
                "duration_ms": duration_ms,
            })

        except Exception as handler_error:
            duration_ms = int((time.time() - start_time) * 1000)
            approval_record.mark_failed(str(handler_error))

            # Track failure
            action_type, platform = action_key.split("@") if "@" in action_key else (action_key, "unknown")
            metric = ExecutionMetric(
                task_id=task_id,
                action_type=action_type,
                platform=platform,
                result=ExecutionResult.FAILED,
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_message=str(handler_error),
                p02_status="failed",
            )
            health_tracker.record_execution(metric)

            logger.error(f"Handler execution failed: task_id={task_id}, error={handler_error}")
            raise

    except Exception as e:
        logger.error(f"Internal execution error: {e}", exc_info=True)
        return error_response(str(e), "EXECUTION_ERROR", 500)


# ============================================================================
# APPROVAL ENDPOINTS
# ============================================================================

def approve_task(task_id: str, payload: dict):
    """Approve a task and trigger execution."""
    try:
        approver_email = payload.get("approver_email", "unknown@company.com")
        evidence = payload.get("evidence", {})

        if task_id not in _request_cache:
            return error_response(
                f"Task not found: {task_id}",
                "TASK_NOT_FOUND",
                404
            )

        cached = _request_cache[task_id]
        approval_record: TaskApprovalRecord = cached["approval_record"]
        action_key = cached["action_key"]

        # Mark approved
        approval_record.mark_approved(evidence)

        # Save to ledger
        ledger_manager.save_approval_record(approval_record)

        logger.info(f"Task approved: task_id={task_id}, approver={approver_email}")

        # Execute handler
        return _execute_handler_internal(task_id, action_key)

    except Exception as e:
        logger.error(f"Error approving task: {e}")
        return error_response(str(e), "APPROVAL_ERROR", 500)


def reject_task(task_id: str, payload: dict):
    """Reject a task approval."""
    try:
        approver_email = payload.get("approver_email", "unknown@company.com")
        reason = payload.get("reason", "No reason provided")

        if task_id not in _request_cache:
            return error_response(
                f"Task not found: {task_id}",
                "TASK_NOT_FOUND",
                404
            )

        cached = _request_cache[task_id]
        approval_record: TaskApprovalRecord = cached["approval_record"]
        action_key = cached["action_key"]

        # Mark rejected
        approval_record.mark_rejected(reason, {"approver": approver_email})

        # Save to ledger
        ledger_manager.save_approval_record(approval_record)

        logger.info(f"Task rejected: task_id={task_id}, approver={approver_email}, reason={reason}")

        return success_response({
            "task_id": task_id,
            "action_key": action_key,
            "status": "rejected",
            "reason": reason,
        })

    except Exception as e:
        logger.error(f"Error rejecting task: {e}")
        return error_response(str(e), "REJECTION_ERROR", 500)


def get_approval_status(task_id: str):
    """Get approval status for a task."""
    try:
        if task_id not in _request_cache:
            return error_response(
                f"Task not found: {task_id}",
                "TASK_NOT_FOUND",
                404
            )

        cached = _request_cache[task_id]
        approval_record: TaskApprovalRecord = cached["approval_record"]

        return success_response({
            "task_id": task_id,
            "approval_request_id": approval_record.approval_request_id,
            "status": approval_record.status.value,
            "approval_decision": approval_record.approval_decision,
            "approvers": approval_record.approvers_assigned,
            "created_at": approval_record.created_at,
            "updated_at": approval_record.updated_at,
        })

    except Exception as e:
        logger.error(f"Error getting approval status: {e}")
        return error_response(str(e), "STATUS_ERROR", 500)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

def get_health_status():
    """Get overall platform health status."""
    try:
        # Get all aggregated health metrics and convert to dicts
        all_health = health_tracker.get_all_health()
        modules = [m.to_dict() for m in all_health.values()]

        # Get overall platform health summary
        summary = health_tracker.get_health_summary()

        return success_response({
            "platform_status": "operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "modules": modules,
        })
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return error_response(str(e), "HEALTH_ERROR", 500)


def get_handler_health(action_key: str):
    """Get health metrics for a specific handler."""
    try:
        metrics = health_tracker.get_metrics_for_handler(action_key)

        if not metrics:
            return error_response(
                f"No metrics found for handler: {action_key}",
                "METRICS_NOT_FOUND",
                404
            )

        return success_response({
            "action_key": action_key,
            "metrics": [asdict(m) for m in metrics],
        })
    except Exception as e:
        logger.error(f"Error getting handler health: {e}")
        return error_response(str(e), "HEALTH_ERROR", 500)


# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================

def system_info():
    """Get system and platform information."""
    try:
        return success_response({
            "platform_name": "Codex Control Platform",
            "phase": "Phase 7-8 Integration",
            "version": "1.0.0",
            "endpoint": "http://127.0.0.1:8765",
            "handlers_registered": len(registry.list_handlers()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "features": [
                "Phase 7 ActionHandler execution",
                "P0-2 approval gate system",
                "Real-time health tracking",
                "Audit ledger storage",
                "Dashboard integration",
            ],
        })
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return error_response(str(e), "SYSTEM_ERROR", 500)


def health_check():
    """Simple health check for monitoring."""
    return success_response({"status": "healthy"})


# ============================================================================
# HTTP REQUEST HANDLER
# ============================================================================

class ControlPlatformRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for control platform REST API."""

    def do_GET(self):
        """Handle GET requests."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            # Route requests
            if path == "/":
                body, status = health_check()
            elif path == "/health":
                body, status = health_check()
            elif path == "/handlers":
                body, status = list_handlers()
            elif path.startswith("/handlers/"):
                action_key = path.split("/handlers/")[1].rstrip("/")
                if path.endswith("/health"):
                    action_key = action_key.replace("/health", "")
                    body, status = get_handler_health(action_key)
                else:
                    body, status = get_handler_metadata(action_key)
            elif path == "/approval/status":
                # Get status for a specific task
                task_id = query_params.get("task_id", [""])[0]
                if task_id:
                    body, status = get_approval_status(task_id)
                else:
                    body, status = error_response("Missing task_id parameter", "INVALID_REQUEST", 400)
            elif path == "/health/status":
                body, status = get_health_status()
            elif path == "/system/info":
                body, status = system_info()
            else:
                body, status = error_response(f"Path not found: {path}", "NOT_FOUND", 404)

            self._send_response(body, status)

        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            error_body, error_status = error_response(str(e), "INTERNAL_ERROR", 500)
            self._send_response(error_body, error_status)

    def do_POST(self):
        """Handle POST requests."""
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path

            # Parse JSON body
            content_length = int(self.headers.get("Content-Length", 0))
            body_raw = self.rfile.read(content_length)
            payload = json.loads(body_raw) if body_raw else {}

            # Route requests
            if path == "/execute":
                action_key = payload.get("action_key", "")
                if not action_key:
                    response_body, status = error_response("Missing action_key", "INVALID_REQUEST", 400)
                else:
                    response_body, status = execute_handler(action_key, payload)
            elif path.startswith("/approval/"):
                task_id = path.split("/approval/")[1].rstrip("/")
                if path.endswith("/approve"):
                    response_body, status = approve_task(task_id, payload)
                elif path.endswith("/reject"):
                    response_body, status = reject_task(task_id, payload)
                else:
                    response_body, status = error_response(f"Invalid approval path: {path}", "NOT_FOUND", 404)
            else:
                response_body, status = error_response(f"Path not found: {path}", "NOT_FOUND", 404)

            self._send_response(response_body, status)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {e}")
            error_body, error_status = error_response("Invalid JSON body", "INVALID_JSON", 400)
            self._send_response(error_body, error_status)
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            error_body, error_status = error_response(str(e), "INTERNAL_ERROR", 500)
            self._send_response(error_body, error_status)

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def _send_response(self, body: dict, status: int):
        """Send JSON response with CORS headers."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._add_cors_headers()
        self.end_headers()

        response_json = json.dumps(body, indent=2)
        self.wfile.write(response_json.encode())

    def _add_cors_headers(self):
        """Add CORS headers to response."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def log_message(self, format, *args):
        """Override to use project logger instead of default stderr."""
        logger.info(f"{self.client_address[0]} - {format % args}")


# ============================================================================
# SERVER STARTUP
# ============================================================================

def run_server(host: str = "127.0.0.1", port: int = 8766):
    """Start the HTTP server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, ControlPlatformRequestHandler)

    logger.info(f"Starting Codex Control Platform API at http://{host}:{port}")
    logger.info(f"Dashboard will connect to http://{host}:{port}")
    logger.info(f"Phase 7 handlers registered: {len(registry.list_handlers())}")
    logger.info("Press Ctrl+C to stop the server")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        httpd.shutdown()
        logger.info("Server stopped")


if __name__ == "__main__":
    run_server()

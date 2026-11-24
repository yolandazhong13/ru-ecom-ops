#!/usr/bin/env python3
"""SQLite database layer for persistent storage.

Provides:
1. Order ledger persistence
2. Audit trail storage
3. Metrics caching
4. Alert history
"""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

ROOT = Path(__file__).resolve().parents[1]


class DatabaseLayer:
    """SQLite database layer for persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database.

        Args:
            db_path: Path to SQLite database
        """
        if not db_path:
            db_path = ROOT / "data" / "orders.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                shop_id TEXT NOT NULL,
                total_amount REAL NOT NULL,
                currency TEXT NOT NULL,
                state_machine_state TEXT NOT NULL,
                reconciliation_status TEXT NOT NULL,
                matched_on_platform INTEGER NOT NULL,
                payment_confirmed INTEGER NOT NULL,
                delivered INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data JSON NOT NULL
            )
        """)

        # Audit trail table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details JSON NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            )
        """)

        # Metrics cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics_cache (
                key TEXT PRIMARY KEY,
                value JSON NOT NULL,
                computed_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)

        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved INTEGER DEFAULT 0,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            )
        """)

        conn.commit()
        conn.close()

    def save_order(self, order_data: Dict[str, Any]) -> bool:
        """Save order to database.

        Args:
            order_data: Order data dictionary

        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO orders
                (id, order_id, platform, shop_id, total_amount, currency,
                 state_machine_state, reconciliation_status, matched_on_platform,
                 payment_confirmed, delivered, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data.get('ledger_entry_id', order_data.get('order_id')),
                order_data['order_id'],
                order_data['platform'],
                order_data['shop_id'],
                order_data['total_amount'],
                order_data['currency'],
                order_data['state_machine_state'],
                order_data['reconciliation_status'],
                int(order_data.get('matched_on_platform', False)),
                int(order_data.get('payment_confirmed', False)),
                int(order_data.get('delivered', False)),
                order_data.get('created_at', datetime.now(timezone.utc).isoformat()),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(order_data),
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[DB] Error saving order: {e}")
            return False

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order from database.

        Args:
            order_id: Order ID to retrieve

        Returns:
            Order data or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            print(f"[DB] Error getting order: {e}")
            return None

    def get_all_orders(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all orders from database.

        Args:
            limit: Maximum orders to retrieve

        Returns:
            List of order data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM orders LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            print(f"[DB] Error getting orders: {e}")
            return []

    def save_audit_event(self, order_id: str, event_data: Dict[str, Any]) -> bool:
        """Save audit event.

        Args:
            order_id: Order ID
            event_data: Event data

        Returns:
            True if saved
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO audit_events (order_id, event_type, timestamp, details)
                VALUES (?, ?, ?, ?)
            """, (
                order_id,
                event_data.get('event_type', 'unknown'),
                event_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                json.dumps(event_data),
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[DB] Error saving audit event: {e}")
            return False

    def get_order_audit_trail(self, order_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for order.

        Args:
            order_id: Order ID

        Returns:
            List of audit events
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM audit_events WHERE order_id = ? ORDER BY timestamp DESC
            """, (order_id,))
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            print(f"[DB] Error getting audit trail: {e}")
            return []

    def save_metrics(self, key: str, value: Dict[str, Any], ttl_seconds: int = 300) -> bool:
        """Cache metrics.

        Args:
            key: Metric key
            value: Metric value
            ttl_seconds: Time to live

        Returns:
            True if saved
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc)
            expires = (now + __import__('datetime').timedelta(seconds=ttl_seconds)).isoformat()

            cursor.execute("""
                INSERT OR REPLACE INTO metrics_cache (key, value, computed_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (key, json.dumps(value), now.isoformat(), expires))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[DB] Error saving metrics: {e}")
            return False

    def get_metrics(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached metrics.

        Args:
            key: Metric key

        Returns:
            Metric value or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT value FROM metrics_cache
                WHERE key = ? AND expires_at > ?
            """, (key, datetime.now(timezone.utc).isoformat()))
            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row['value'])
            return None

        except Exception as e:
            print(f"[DB] Error getting metrics: {e}")
            return None

    def save_alert(self, order_id: str, alert_data: Dict[str, Any]) -> bool:
        """Save alert.

        Args:
            order_id: Order ID
            alert_data: Alert data

        Returns:
            True if saved
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO alerts (order_id, alert_type, severity, message, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                alert_data.get('alert_type', 'general'),
                alert_data.get('severity', 'info'),
                alert_data.get('message', ''),
                datetime.now(timezone.utc).isoformat(),
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[DB] Error saving alert: {e}")
            return False

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent unresolved alerts.

        Args:
            limit: Number of alerts to retrieve

        Returns:
            List of alerts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM alerts
                WHERE resolved = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            print(f"[DB] Error getting alerts: {e}")
            return []

    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics.

        Returns:
            Statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM orders")
            total_orders = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) as count FROM audit_events")
            total_events = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE resolved = 0")
            open_alerts = cursor.fetchone()[0]

            conn.close()

            return {
                "total_orders": total_orders,
                "total_events": total_events,
                "open_alerts": open_alerts,
            }

        except Exception as e:
            print(f"[DB] Error getting statistics: {e}")
            return {}


def main() -> None:
    """Demo database layer."""
    print("[Database] Testing SQLite persistence\n")

    db = DatabaseLayer()

    # Save test order
    test_order = {
        "order_id": "TEST_001",
        "platform": "WB_CN",
        "shop_id": "250146669",
        "total_amount": 1500.00,
        "currency": "RUB",
        "state_machine_state": "confirmed",
        "reconciliation_status": "matched",
        "matched_on_platform": True,
        "payment_confirmed": True,
        "delivered": False,
    }

    db.save_order(test_order)
    print("✓ Test order saved")

    # Retrieve order
    order = db.get_order("TEST_001")
    if order:
        print(f"✓ Order retrieved: {order['order_id']} ({order['platform']})")

    # Save audit event
    event = {
        "event_type": "ORDER_CREATED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": {"amount": 1500.00},
    }
    db.save_audit_event("TEST_001", event)
    print("✓ Audit event saved")

    # Save metrics
    metrics = {"orders_per_day": 42, "anomaly_rate": 0.75}
    db.save_metrics("daily_metrics", metrics)
    cached = db.get_metrics("daily_metrics")
    if cached:
        print(f"✓ Metrics cached and retrieved")

    # Save alert
    alert = {
        "alert_type": "SLA_VIOLATION",
        "severity": "P1",
        "message": "Payment overdue",
    }
    db.save_alert("TEST_001", alert)
    print("✓ Alert saved")

    # Get statistics
    stats = db.get_statistics()
    print(f"\n[Database] Statistics:")
    print(f"  Orders: {stats['total_orders']}")
    print(f"  Audit events: {stats['total_events']}")
    print(f"  Open alerts: {stats['open_alerts']}")
    print(f"\n✓ Database layer ready")


if __name__ == "__main__":
    main()

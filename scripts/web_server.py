#!/usr/bin/env python3
"""Flask web server with REST API and dashboard.

Provides:
1. REST API endpoints
2. Web dashboard routes
3. Real-time data access
4. Alert management
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from flask import Flask, jsonify, request, render_template_string
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("[Warning] Flask not installed. Install: pip install flask")

from database_layer import DatabaseLayer
from order_ledger import OrderLedger
from advanced_dashboard import AdvancedDashboard
from performance_metrics import PerformanceMetrics


class WebServer:
    """Flask-based web server for order management."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        """Initialize web server.

        Args:
            host: Server host
            port: Server port
        """
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required. Install: pip install flask")

        self.app = Flask(__name__)
        self.db = DatabaseLayer()
        self.host = host
        self.port = port

        self._register_routes()

    def _register_routes(self) -> None:
        """Register API and web routes."""

        # Health check
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

        # API: Get all orders
        @self.app.route("/api/orders", methods=["GET"])
        def get_orders():
            limit = request.args.get("limit", 100, type=int)
            orders = self.db.get_all_orders(limit=limit)
            return jsonify({"orders": orders, "count": len(orders)})

        # API: Get order details
        @self.app.route("/api/orders/<order_id>", methods=["GET"])
        def get_order(order_id: str):
            order = self.db.get_order(order_id)
            if not order:
                return jsonify({"error": "Order not found"}), 404
            return jsonify(order)

        # API: Get audit trail
        @self.app.route("/api/orders/<order_id>/audit", methods=["GET"])
        def get_audit_trail(order_id: str):
            trail = self.db.get_order_audit_trail(order_id)
            return jsonify({"order_id": order_id, "events": trail})

        # API: Get statistics
        @self.app.route("/api/statistics", methods=["GET"])
        def get_statistics():
            stats = self.db.get_statistics()
            return jsonify(stats)

        # API: Get metrics
        @self.app.route("/api/metrics", methods=["GET"])
        def get_metrics():
            try:
                ledger = OrderLedger()
                metrics = PerformanceMetrics(ledger)
                kpis = metrics.compute_kpis()
                return jsonify(kpis)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # API: Get alerts
        @self.app.route("/api/alerts", methods=["GET"])
        def get_alerts():
            limit = request.args.get("limit", 50, type=int)
            alerts = self.db.get_recent_alerts(limit=limit)
            return jsonify({"alerts": alerts, "count": len(alerts)})

        # Web: Dashboard
        @self.app.route("/", methods=["GET"])
        def dashboard():
            return self._render_dashboard_html()

        # Web: Orders list
        @self.app.route("/orders", methods=["GET"])
        def orders_page():
            return self._render_orders_html()

        # Web: Order details
        @self.app.route("/orders/<order_id>", methods=["GET"])
        def order_details(order_id: str):
            return self._render_order_detail_html(order_id)

    def _render_dashboard_html(self) -> str:
        """Render dashboard HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Order Management Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
        .stat { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .stat-value { font-size: 32px; font-weight: bold; color: #2c3e50; }
        .stat-label { font-size: 14px; color: #7f8c8d; margin-top: 5px; }
        .links { margin-top: 20px; }
        a { margin-right: 15px; color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
    <script>
        async function loadStats() {
            try {
                const resp = await fetch('/api/statistics');
                const data = await resp.json();
                document.getElementById('orders').textContent = data.total_orders || 0;
                document.getElementById('events').textContent = data.total_events || 0;
                document.getElementById('alerts').textContent = data.open_alerts || 0;
            } catch (e) {
                console.error('Error loading stats:', e);
            }
        }
        window.onload = () => loadStats();
        setInterval(loadStats, 5000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Order Management System</h1>
            <p>Real-time order tracking, analytics, and monitoring</p>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="orders">-</div>
                <div class="stat-label">Total Orders</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="events">-</div>
                <div class="stat-label">Audit Events</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="alerts">-</div>
                <div class="stat-label">Open Alerts</div>
            </div>
            <div class="stat">
                <div class="stat-value">✅</div>
                <div class="stat-label">System Status</div>
            </div>
        </div>

        <div class="links">
            <h3>Navigation:</h3>
            <a href="/orders">📋 Orders List</a>
            <a href="/api/metrics">📈 Metrics (JSON)</a>
            <a href="/api/alerts">🚨 Alerts (JSON)</a>
            <a href="/health">🏥 Health Check</a>
        </div>
    </div>
</body>
</html>
        """

    def _render_orders_html(self) -> str:
        """Render orders list HTML."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Orders</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        table { width: 100%; border-collapse: collapse; background: white; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #2c3e50; color: white; }
        tr:hover { background: #f9f9f9; }
        a { color: #3498db; text-decoration: none; }
        .back { margin-bottom: 20px; }
    </style>
    <script>
        async function loadOrders() {
            try {
                const resp = await fetch('/api/orders?limit=50');
                const data = await resp.json();
                const tbody = document.getElementById('orders-body');
                tbody.innerHTML = '';
                data.orders.forEach(order => {
                    const row = '<tr><td><a href="/orders/' + order.order_id + '">' + order.order_id + '</a></td><td>' +
                                order.platform + '</td><td>' + order.state_machine_state + '</td><td>' +
                                order.total_amount + ' ' + order.currency + '</td><td>' +
                                (order.matched_on_platform ? '✓' : '✗') + '</td></tr>';
                    tbody.innerHTML += row;
                });
            } catch (e) {
                console.error('Error:', e);
            }
        }
        window.onload = loadOrders;
        setInterval(loadOrders, 10000);
    </script>
</head>
<body>
    <div class="container">
        <div class="back"><a href="/">← Back to Dashboard</a></div>
        <h1>📋 Orders</h1>
        <table>
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Platform</th>
                    <th>State</th>
                    <th>Amount</th>
                    <th>Matched</th>
                </tr>
            </thead>
            <tbody id="orders-body">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>
        """

    def _render_order_detail_html(self, order_id: str) -> str:
        """Render order detail HTML."""
        detail_url = '/api/orders/' + order_id
        audit_url = '/api/orders/' + order_id + '/audit'

        return """
<!DOCTYPE html>
<html>
<head>
    <title>Order: """ + order_id + """</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; }
        .detail { background: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .detail h2 { margin-top: 0; border-bottom: 2px solid #2c3e50; }
        .field { margin: 10px 0; }
        .label { font-weight: bold; color: #2c3e50; }
        .back { margin-bottom: 20px; }
        a { color: #3498db; text-decoration: none; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #ecf0f1; }
    </style>
    <script>
        async function loadOrderDetail() {
            try {
                const resp = await fetch('""" + detail_url + """');
                const order = await resp.json();

                if (order.error) {
                    document.getElementById('detail').innerHTML = '<p>Order not found</p>';
                    return;
                }

                let html = '<div class="detail"><h2>Order Information</h2>';
                html += '<div class="field"><span class="label">Order ID:</span> ' + order.order_id + '</div>';
                html += '<div class="field"><span class="label">Platform:</span> ' + order.platform + '</div>';
                html += '<div class="field"><span class="label">Shop ID:</span> ' + order.shop_id + '</div>';
                html += '<div class="field"><span class="label">State:</span> ' + order.state_machine_state + '</div>';
                html += '<div class="field"><span class="label">Amount:</span> ' + order.total_amount + ' ' + order.currency + '</div>';
                html += '</div>';

                const auditResp = await fetch('""" + audit_url + """');
                const auditData = await auditResp.json();

                html += '<div class="detail"><h2>Audit Trail (' + auditData.events.length + ' events)</h2>';
                html += '<table><thead><tr><th>Event</th><th>Timestamp</th></tr></thead><tbody>';
                auditData.events.forEach(event => {
                    html += '<tr><td>' + event.event_type + '</td><td>' + event.timestamp + '</td></tr>';
                });
                html += '</tbody></table></div>';

                document.getElementById('detail').innerHTML = html;
            } catch (e) {
                console.error('Error:', e);
            }
        }
        window.onload = loadOrderDetail;
    </script>
</head>
<body>
    <div class="container">
        <div class="back"><a href="/orders">← Back to Orders</a></div>
        <h1>Order: """ + order_id + """</h1>
        <div id="detail">Loading...</div>
    </div>
</body>
</html>
        """

    def run(self) -> None:
        """Start web server."""
        print(f"\n[WebServer] Starting on http://{self.host}:{self.port}")
        print(f"[WebServer] Dashboard: http://{self.host}:{self.port}/")
        print(f"[WebServer] API: http://{self.host}:{self.port}/api/\n")

        self.app.run(host=self.host, port=self.port, debug=False)


if __name__ == "__main__":
    if not FLASK_AVAILABLE:
        print("[Error] Flask required. Install: pip install flask")
        sys.exit(1)

    server = WebServer()
    server.run()

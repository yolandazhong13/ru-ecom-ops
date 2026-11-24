# Phase 2: Order Tracking & Reconciliation System

## Summary

Phase 2 implements a complete order tracking and reconciliation system with real-time anomaly detection, alerting, and billing analysis. Five core components orchestrate a daily workflow processing orders from WB and Ozon platforms.

## Components

| Component | Lines | Purpose |
|-----------|-------|---------|
| order_tracker.py | 487 | Aggregate orders from platforms, map states, execute transitions |
| order_anomaly_detector.py | 417 | Detect timing, state, data, reconciliation anomalies |
| order_alert_dispatcher.py | 448 | Dispatch alerts via Feishu (P0/P1/P2 severity) |
| billing_aggregator.py | 402 | Daily/weekly/monthly revenue analysis by shop |
| reconciliation_engine.py | 503 | Compare ledger vs platform, detect discrepancies |
| order_dashboard.py | 85 | Real-time monitoring dashboard |
| order_workflow_orchestrator.py | 189 | Automated daily workflow orchestration |
| test_phase25_integration.py | 285 | Integration test with synthetic data |

**Total**: 2,816 lines of production code + tests

## Architecture

```
Platform APIs (WB/Ozon)
    ↓
UnifiedAPIGateway (fetch_all_orders)
    ↓
OrderTracker (map_platform_state → OrderState)
    ↓
OrderStateMachine (validate transitions)
    ↓
OrderLedger (persist with deduplication)
    ↓
OrderAnomalyDetector (classify by severity)
    ↓ P0 (critical) → Feishu (immediate)
    ↓ P1 (warning) → Feishu (batch by shop)
    ↓ P2 (info) → Feishu (daily summary)
    ↓
BillingAggregator (revenue by shop/platform)
    ↓
ReconciliationEngine (ledger vs platform)
```

## Key Features

✅ **Multi-platform support**: WB (Wildberries) + Ozon with unified adapter  
✅ **State machine**: 10 order states with valid transition validation  
✅ **Deduplication**: SHA-256 (order_id, platform, shop_id) for entry_id  
✅ **Anomaly detection**: 10 anomaly types across 4 categories  
✅ **Severity classification**: P0 (immediate), P1 (hourly), P2 (daily)  
✅ **Real-time alerting**: Feishu integration with color-coded severity  
✅ **Billing analysis**: Daily/weekly/monthly aggregation by shop  
✅ **Reconciliation**: Platform vs ledger with discrepancy tracking  
✅ **Dashboard**: Real-time monitoring of pipeline health  
✅ **Workflow automation**: Orchestrated daily processing

## Data Flow

### Order Tracking
- Input: Platform APIs return orders with platform_state
- Processing: Map to OrderState, execute transition, detect anomalies
- Output: OrderLedger with OrderLedgerEntry (deduped)

### Anomaly Detection
- Input: OrderLedger entries
- Scan: Timing (overdue dates), state (invalid transitions), data (missing fields)
- Output: AnomalyRecord list with severity and category

### Alert Dispatch
- Input: Anomaly records
- Route: P0→individual alerts, P1→shop batches, P2→daily summary
- Output: Feishu cards via webhook, dispatch logs

### Billing Aggregation
- Input: OrderLedger entries in date range
- Compute: Totals by shop/platform/state, payment confirmation
- Output: BillingReport with shop-level breakdown

### Reconciliation
- Input: Ledger entries vs live platform data
- Compare: Amount, state, currency per order
- Output: Discrepancy records (missing/mismatch)

## Output Files

| File | Size | Purpose |
|------|------|---------|
| order_tracker_report.json | 1.6K | Sync statistics |
| order_ledger.json | 2.7K | Persistent storage |
| anomaly_detection_report.json | 9.2K | Anomalies + severity |
| alert_dispatch_report.json | 181B | Dispatch logs |
| billing_report_daily.json | 1.6K | Revenue analysis |
| reconciliation_report.json | 28.5K | Discrepancies |
| order_dashboard.json | - | Real-time view |
| workflow_log_daily.json | - | Daily execution log |

## Usage

### Run complete daily workflow
```bash
python3 scripts/order_workflow_orchestrator.py
```

### Run individual components
```bash
python3 scripts/order_tracker.py
python3 scripts/order_anomaly_detector.py
python3 scripts/order_alert_dispatcher.py
python3 scripts/billing_aggregator.py
python3 scripts/reconciliation_engine.py
```

### View dashboard
```bash
python3 scripts/order_dashboard.py
```

### Integration test with synthetic data
```bash
python3 scripts/test_phase25_integration.py
```

## Test Results

**Integration Test (50 synthetic orders)**:
- Orders added: 50/50 ✅
- Anomalies detected: 14 (P0: 5, P1: 9) ✅
- Billing report: Generated ✅
- Reconciliation: All components working ✅

## Configuration

No API keys required for testing (mock adapters). For production:

**WB Configuration** (`.wb_config`):
```json
{"api_key": "your-wb-api-key"}
```

**Ozon Configuration** (`.ozon_config`):
```json
{"api_key": "your-ozon-api-key"}
```

**Feishu Configuration** (`.feishu_config`):
```json
{"webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/..."}
```

## State Machine

**Main Lifecycle**:
```
PENDING_PAYMENT → PAID → SHIPPED → IN_TRANSIT → DELIVERED → CONFIRMED
```

**Terminal States**:
- CANCELLED (pre-shipment)
- REFUSED_PRE_DELIVERY (before receiving)
- REFUSED_POST_DELIVERY (after receiving)
- RETURNED (post-delivery)

## Anomaly Types

**Timing** (3):
- payment_overdue (>1h)
- shipment_delayed (>24h)
- delivery_delayed (>7d)

**State Transition** (3):
- unexpected_cancellation
- unexpected_refusal
- unexpected_return

**Data Quality** (4):
- missing_order
- duplicate_order
- amount_mismatch
- sku_mismatch

## Severity Mapping

| Anomaly Type | P0 | P1 | P2 |
|---|---|---|---|
| payment_overdue | ✅ | | |
| shipment_delayed | | ✅ | |
| delivery_delayed | | ✅ | |
| unexpected_cancellation | | ✅ | |
| amount_mismatch | ✅ | | |
| missing_order | ✅ | | |

## Next Steps (Phase 3)

1. Create dashboard with real-time charts
2. Add historical trend analysis
3. Implement automatic retry for failed orders
4. Extend health tracking integration
5. Add batch error recovery

## Dependencies

- Python 3.9+
- Standard library only (no external packages)
- UnifiedAPIGateway (via wb_ozon_api_adapter.py)
- Feishu webhook (optional, for alerts)


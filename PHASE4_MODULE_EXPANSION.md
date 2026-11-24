# Phase 4: Workflow Module Expansion & Monitoring Integration

## Overview

Phase 4 expands the guarded workflow framework to support multiple action handlers across different platforms with integrated monitoring, validation, and alerting capabilities.

**Status**: In Progress  
**Components Implemented**: 4/5  
**Test Coverage**: Functional validation module + API health tracker

## Phase 4 Objectives

### 1. ✅ API Integration Monitoring
**File**: `api_health_tracker.py` (15 KB)

Tracks health of WB and Ozon API integrations:
- Per-endpoint status (AVAILABLE, DEGRADED, UNAVAILABLE)
- Call latency tracking (average, p95, p99)
- Rate limit monitoring
- Error rate analysis
- Platform-wide aggregation

**Metrics Schema**:
```json
{
  "api_endpoint": "/v3/product/info/list",
  "method": "POST",
  "platform": "WB_CN",
  "status_code": 200,
  "duration_ms": 145,
  "error_rate": 0.0,
  "rate_limit_remaining": 9999
}
```

**Status Thresholds**:
- AVAILABLE: error_rate ≤ 1%
- DEGRADED: 1% < error_rate ≤ 10%
- UNAVAILABLE: error_rate > 10%

**Database**: `outputs/api_health_tracking.json`

### 2. ✅ Data Quality Validation
**File**: `data_quality_validator.py` (18 KB)

Validates execution outputs against JSON schemas:
- Execution result validation
- Inventory aggregation validation
- Listing update validation
- Extensible rule-based framework

**Validation Rules Types**:
- required: Field must be present
- enum: Field value from allowed set
- type: Field type and value constraints
- range: Numeric range validation
- comparison: Cross-field comparisons
- conditional: Conditional logic

**Validation Status**:
- VALID: All rules passed
- INVALID: One or more rules failed
- WARNING: Rules passed with warnings
- UNKNOWN: No validation history

**Reports**: `outputs/validation_reports/validation_report.json`

### 3. ✅ Action Handler Registry
**File**: `action_handler_registry.py` (12 KB)

Centralized handler discovery and management:
- Register new handlers dynamically
- Metadata tracking (risk level, API requirements, description)
- Query handlers by action type, platform, or risk level
- Factory pattern for handler instantiation

**Handler Registration**:
```python
HANDLER_REGISTRY.register(
    action_type="inventory_update",
    platform="WB_CN",
    handler_class=InventoryActionHandler,
    description="Aggregates inventory...",
    requires_api=False,
    risk_level="low"
)
```

**Available Queries**:
- `get_handler(action_type, platform)` - Get specific handler
- `list_handlers()` - All handlers
- `list_by_platform(platform)` - Platform handlers
- `list_by_action_type(action_type)` - Action type handlers
- `list_by_risk_level(risk_level)` - Risk level handlers

### 4. ⏳ Unified Monitoring Dashboard
**Status**: To Be Implemented in Phase 4.2

Will integrate health tracking, API monitoring, and validation reports into single dashboard view.

## Workflow Modules Status

| Module | Platform | Handler | Status | Risk | API Required |
|--------|----------|---------|--------|------|--------------|
| inventory_update | WB_CN | InventoryActionHandler | ✅ Active | LOW | No |
| listing_update | Ozon RU | ListingActionHandler | ⏳ Pending | HIGH | Yes |
| pricing_update | WB_CN | To Implement | ⏳ Pending | HIGH | Yes |
| purchase_orders | WB_CN | To Implement | ⏳ Pending | MEDIUM | No |
| review_response | Ozon RU | To Implement | ⏳ Pending | LOW | Yes |
| + 12 more modules | Various | TBD | ⏳ Planned | Various | Various |

## Integration Architecture

```
UnifiedActionExecutor
├─ P0-2 Approval Workflow
├─ Health Tracking (Phase 3)
│  ├─ HealthTracker → health_tracking.json
│  └─ HealthDashboard
├─ API Monitoring (Phase 4)
│  ├─ APIHealthTracker → api_health_tracking.json
│  └─ APIHealthDashboard
└─ Data Quality Validation (Phase 4)
   ├─ DataQualityValidator → validation_reports/
   └─ Per-schema validation results

ActionHandlerRegistry (Phase 4)
├─ Handler Discovery
├─ Metadata Tracking
└─ Factory Pattern Instantiation
```

## Phase 4 Development Path

### 4.1 Core Infrastructure (COMPLETE)
- ✅ API health tracking engine
- ✅ Data quality validation framework
- ✅ Action handler registry
- ⏳ Unified monitoring dashboard

### 4.2 Listing Module (IN PROGRESS)
- Use existing ListingActionHandler from Phase 2
- Integrate API health tracking for Ozon endpoints
- Add validation schema for listing updates
- Create test harness and health metrics

### 4.3 Additional Modules (PLANNED)
- Pricing updates for WB_CN
- Purchase order processing
- Review response automation
- Platform feature monitoring
- Competitive intelligence

## Usage Examples

### Register Custom Handler

```python
from action_handler_registry import HANDLER_REGISTRY

HANDLER_REGISTRY.register(
    action_type="pricing_update",
    platform="WB_CN",
    handler_class=PricingActionHandler,
    description="Updates product prices on WB_CN",
    requires_api=True,
    risk_level="high"
)
```

### Discover Available Handlers

```python
from action_handler_registry import HANDLER_REGISTRY

# List all handlers
all_handlers = HANDLER_REGISTRY.list_handlers()

# List by platform
wb_handlers = HANDLER_REGISTRY.list_by_platform("WB_CN")

# List high-risk handlers
high_risk = HANDLER_REGISTRY.list_by_risk_level("high")
```

### Track API Health

```python
from api_health_tracker import APIHealthTracker, APIStatus

tracker = APIHealthTracker()

# Record API call
tracker.record_api_call(
    api_endpoint="/v3/product/info/list",
    method="POST",
    platform="WB_CN",
    status_code=200,
    duration_ms=145,
    rate_limit_remaining=9999
)

# Get platform health
health = tracker.get_platform_health("WB_CN")
```

### Validate Output Data

```python
from data_quality_validator import DataQualityValidator

validator = DataQualityValidator()

# Validate inventory aggregation
result = validator.validate_inventory_aggregation(inventory_data)
if result.validation_status == ValidationStatus.VALID:
    print("Data quality check passed")
```

## Files Created in Phase 4

| File | Size | Purpose |
|------|------|---------|
| api_health_tracker.py | 15 KB | API integration monitoring |
| data_quality_validator.py | 18 KB | Output validation schemas |
| action_handler_registry.py | 12 KB | Handler discovery & management |
| api_health_tracking.json | - | API metrics database |
| validation_reports/ | - | Validation result storage |

## Testing Strategy

### Unit Tests
- ✅ API health tracker metrics aggregation
- ✅ Data quality validation rules
- ✅ Handler registry operations
- ⏳ Integration tests with listing module

### End-to-End Tests
- ⏳ Listing update workflow (Phase 4.2)
- ⏳ API health tracking during execution
- ⏳ Validation of execution results
- ⏳ SLA compliance monitoring

## Metrics & Monitoring

### API Health SLAs
- **Availability**: ≥99.9% uptime per endpoint
- **Latency**: P95 < 500ms, P99 < 2000ms
- **Error Rate**: ≤0.1% per endpoint
- **Rate Limit**: Warn at 10% quota remaining

### Data Quality SLAs
- **Validation Pass Rate**: ≥99%
- **Schema Compliance**: 100% of fields validated
- **Error Detection**: <1ms overhead per record

### Workflow Execution SLAs
- **P0-2 Gate**: <100ms approval verification
- **Handler Execution**: <5s per action (varies by type)
- **Verification**: <2s post-execution validation
- **Health Recording**: <10ms metrics recording

## Phase 4 Roadmap

```
Week 1: Core Infrastructure ✅
  ✅ API health tracker
  ✅ Data quality validator
  ✅ Handler registry

Week 2-3: Listing Module Integration ⏳
  ⏳ Integrate ListingActionHandler
  ⏳ API health metrics for Ozon
  ⏳ Validation schemas for listings
  ⏳ Test harness with metrics

Week 4+: Module Expansion ⏳
  ⏳ Pricing update handler
  ⏳ Purchase order handler
  ⏳ Review response handler
  ⏳ Additional monitoring features
```

## Validation Checklist

✅ API health tracker records metrics  
✅ API endpoint health calculated correctly  
✅ Data quality validator validates schemas  
✅ Validation reports generated  
✅ Handler registry discovers handlers  
✅ Action handler factory working  
✅ All Phase 4 files verified with ls/stat  

⏳ Listing module integrated with monitoring  
⏳ End-to-end test harness for Phase 4  
⏳ Unified monitoring dashboard  

## Next Steps

1. **4.1 Complete**: Integrate monitoring into unified dashboard
2. **4.2 Start**: Listing module integration & testing
3. **4.3 Plan**: Additional workflow module implementations

## References

- Phase 2: P0-2 Approval Workflow - COMPLETE
- Phase 3: Health Tracking - COMPLETE
- Phase 4: Module Expansion - IN PROGRESS

---

*Last Updated: 2026-11-20T14:40:00Z*  
*Status: Phase 4 Core Infrastructure Complete*

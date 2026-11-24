#!/usr/bin/env python3
"""Order state machine for WB and Ozon platforms.

Defines order states, valid transitions, and state metadata for comprehensive
order lifecycle tracking from placement through delivery and post-delivery states.

Order Lifecycle:
  pending_payment → paid → shipped → in_transit → delivered → confirmed

  With branches to terminal states:
  - cancelled (pre-shipment cancellation)
  - refused_pre_delivery (refusal before receiving)
  - refused_post_delivery (refusal after receiving)
  - returned (return initiated post-delivery)
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Set


class OrderState(str, Enum):
    """Order states in the lifecycle."""

    # Main lifecycle states
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CONFIRMED = "confirmed"

    # Terminal states (cancellations, refusals, returns)
    CANCELLED = "cancelled"
    REFUSED_PRE_DELIVERY = "refused_pre_delivery"
    REFUSED_POST_DELIVERY = "refused_post_delivery"
    RETURNED = "returned"


class AnomalyType(str, Enum):
    """Anomaly classification for orders."""

    # Timing anomalies
    PAYMENT_OVERDUE = "payment_overdue"
    SHIPMENT_DELAYED = "shipment_delayed"
    DELIVERY_DELAYED = "delivery_delayed"

    # State transition anomalies
    UNEXPECTED_CANCELLATION = "unexpected_cancellation"
    UNEXPECTED_REFUSAL = "unexpected_refusal"
    UNEXPECTED_RETURN = "unexpected_return"

    # Data anomalies
    MISSING_ORDER = "missing_order"
    DUPLICATE_ORDER = "duplicate_order"
    AMOUNT_MISMATCH = "amount_mismatch"
    SKU_MISMATCH = "sku_mismatch"


class SeverityLevel(str, Enum):
    """Anomaly severity levels for alerting."""

    P0_IMMEDIATE = "p0_immediate"  # Immediate action required (payment overdue, missing order)
    P1_HOURLY = "p1_hourly"        # Summary alert within 1 hour (delays, refusals)
    P2_DAILY = "p2_daily"          # Daily summary (minor discrepancies)


# Valid state transitions
VALID_TRANSITIONS: dict[OrderState, Set[OrderState]] = {
    OrderState.PENDING_PAYMENT: {
        OrderState.PAID,
        OrderState.CANCELLED,  # Can cancel while awaiting payment
    },
    OrderState.PAID: {
        OrderState.SHIPPED,
        OrderState.CANCELLED,  # Can cancel after payment
    },
    OrderState.SHIPPED: {
        OrderState.IN_TRANSIT,
        OrderState.CANCELLED,  # Can cancel during shipment (rare)
    },
    OrderState.IN_TRANSIT: {
        OrderState.DELIVERED,
        OrderState.REFUSED_PRE_DELIVERY,  # Refusal before delivery
    },
    OrderState.DELIVERED: {
        OrderState.CONFIRMED,
        OrderState.REFUSED_POST_DELIVERY,  # Refusal after delivery
        OrderState.RETURNED,  # Return initiated
    },
    OrderState.CONFIRMED: {
        OrderState.RETURNED,  # Can return after confirmed
    },

    # Terminal states (no outbound transitions)
    OrderState.CANCELLED: set(),
    OrderState.REFUSED_PRE_DELIVERY: set(),
    OrderState.REFUSED_POST_DELIVERY: set(),
    OrderState.RETURNED: set(),
}


@dataclass
class StateTransition:
    """Record of a state transition."""

    from_state: OrderState
    to_state: OrderState
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class OrderStateContext:
    """Context for order state including lifecycle metadata."""

    order_id: str
    platform: str  # "WB_CN" or "Ozon"
    shop_id: str

    current_state: OrderState
    state_history: list[StateTransition] = field(default_factory=list)

    # Order details
    order_date: Optional[str] = None
    payment_date: Optional[str] = None
    sku: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "RUB"

    # State-specific metadata
    shipped_date: Optional[str] = None
    delivery_date: Optional[str] = None
    confirmed_date: Optional[str] = None

    # Anomaly tracking
    detected_anomalies: list[AnomalyType] = field(default_factory=list)

    # Last update from platform
    last_platform_update: Optional[str] = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "order_id": self.order_id,
            "platform": self.platform,
            "shop_id": self.shop_id,
            "current_state": self.current_state.value,
            "state_history": [t.to_dict() for t in self.state_history],
            "order_date": self.order_date,
            "payment_date": self.payment_date,
            "sku": self.sku,
            "amount": self.amount,
            "currency": self.currency,
            "shipped_date": self.shipped_date,
            "delivery_date": self.delivery_date,
            "confirmed_date": self.confirmed_date,
            "detected_anomalies": [a.value for a in self.detected_anomalies],
            "last_platform_update": self.last_platform_update,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class OrderStateMachine:
    """Manages order state transitions and validates state machine rules."""

    def __init__(self):
        """Initialize state machine."""
        pass

    @staticmethod
    def is_valid_transition(from_state: OrderState, to_state: OrderState) -> bool:
        """Check if transition is valid.

        Args:
            from_state: Current order state
            to_state: Target order state

        Returns:
            True if transition is allowed, False otherwise
        """
        if from_state not in VALID_TRANSITIONS:
            return False
        return to_state in VALID_TRANSITIONS[from_state]

    @staticmethod
    def transition(
        context: OrderStateContext,
        to_state: OrderState,
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        """Attempt state transition.

        Args:
            context: Order state context
            to_state: Target state
            reason: Reason for transition
            metadata: Additional transition metadata

        Returns:
            (success, error_message) tuple
        """
        from_state = context.current_state

        # Validate transition
        if not OrderStateMachine.is_valid_transition(from_state, to_state):
            return False, f"Invalid transition: {from_state.value} → {to_state.value}"

        # Record transition
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            metadata=metadata or {},
        )
        context.state_history.append(transition)

        # Update current state
        context.current_state = to_state

        # Update relevant timestamps
        now = datetime.now(timezone.utc).isoformat()
        if to_state == OrderState.SHIPPED:
            context.shipped_date = now
        elif to_state == OrderState.DELIVERED:
            context.delivery_date = now
        elif to_state == OrderState.CONFIRMED:
            context.confirmed_date = now

        context.updated_at = now

        return True, None

    @staticmethod
    def is_terminal_state(state: OrderState) -> bool:
        """Check if state is terminal (no further transitions possible).

        Args:
            state: Order state

        Returns:
            True if state is terminal
        """
        return len(VALID_TRANSITIONS.get(state, set())) == 0

    @staticmethod
    def get_next_possible_states(state: OrderState) -> Set[OrderState]:
        """Get all valid next states from current state.

        Args:
            state: Current order state

        Returns:
            Set of possible next states
        """
        return VALID_TRANSITIONS.get(state, set()).copy()


def main() -> None:
    """Demo order state machine."""

    print("[OrderStateMachine] Testing Order State Machine\n")

    # Create sample order context
    order = OrderStateContext(
        order_id="WB_12345678",
        platform="WB_CN",
        shop_id="250146669",
        current_state=OrderState.PENDING_PAYMENT,
        order_date="2026-11-23T10:30:00+00:00",
        sku="SKU-001",
        amount=1500.0,
    )

    print(f"[OrderStateMachine] Initial order state: {order.current_state.value}")
    print(f"[OrderStateMachine] Order: {order.order_id} from {order.platform}")

    # Test transitions
    transitions_to_test = [
        (OrderState.PAID, "Payment received"),
        (OrderState.SHIPPED, "Order shipped"),
        (OrderState.IN_TRANSIT, "In transit to customer"),
        (OrderState.DELIVERED, "Delivered to customer"),
        (OrderState.CONFIRMED, "Customer confirmed receipt"),
    ]

    print(f"\n[OrderStateMachine] Testing state transitions:")
    for target_state, reason in transitions_to_test:
        success, error = OrderStateMachine.transition(
            order,
            target_state,
            reason=reason,
            metadata={"initiated_by": "system"},
        )

        if success:
            print(f"  ✓ → {target_state.value}: {reason}")
        else:
            print(f"  ✗ → {target_state.value}: {error}")

    # Test invalid transition
    print(f"\n[OrderStateMachine] Testing invalid transition:")
    success, error = OrderStateMachine.transition(
        order,
        OrderState.CANCELLED,
        reason="Attempting to cancel confirmed order",
    )
    if not success:
        print(f"  ✓ Correctly blocked: {error}")

    # Display final state
    print(f"\n[OrderStateMachine] Final order state: {order.current_state.value}")
    print(f"[OrderStateMachine] State history:")
    for i, transition in enumerate(order.state_history, 1):
        print(f"  {i}. {transition.from_state.value} → {transition.to_state.value} ({transition.reason})")

    # Display possible next states
    print(f"\n[OrderStateMachine] Possible next states from {order.current_state.value}:")
    next_states = OrderStateMachine.get_next_possible_states(order.current_state)
    if next_states:
        for state in next_states:
            print(f"  - {state.value}")
    else:
        print(f"  (Terminal state - no transitions possible)")

    print(f"\n[OrderStateMachine] ✓ Order state machine initialized successfully")


if __name__ == "__main__":
    main()

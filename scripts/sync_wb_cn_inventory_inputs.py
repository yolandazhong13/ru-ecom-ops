#!/usr/bin/env python3
"""Sync and aggregate WB_CN inventory from multiple sources.

Aggregates inventory data from:
1. Manual overrides (JSON snapshot + logistics CSV)
2. WB backend stock snapshots
3. EasyWarehouse physical inventory
4. Historical order rates

Updates inventory_decision_input.csv in-place with aggregated data.

Usage:
  python3 sync_wb_cn_inventory_inputs.py [--skip-model]

With --skip-model: Skip model execution, only sync and aggregate (default)
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MANUAL_OVERRIDES_DIR = DATA_DIR / "manual_overrides"
INVENTORY_INPUT = DATA_DIR / "inventory_decision_input.csv"

# Valid SKU list (from inventory_action_handler.py)
VALID_SKUS = {
    "MD-700",
    "MD-700 BLACK",
    "MD-4090",
    "MD-4090 PRO",
    "TX-850",
    "TX-850 PRO",
}

# SKU to vendor ID mapping (from inventory_action_handler.py)
VENDOR_TO_SKU = {
    "wb1xx5bipa": "MD-700",
    "wbffpchf2": "MD-4090 PRO",
    "wbvekz0hmy": "TX-850 PRO",
    "wbfqr1iycq": "TX-850",
    "wbs7jfvwmm": "MD-4090",
    "wbgd52d0ib": "MD-700 BLACK",
}

# Manual overrides from CLAUDE.md (2026-08-06)
# Format: {sku: {location: {online_qty, reserve_qty, in_transit_qty, locked_qty}}}
MANUAL_OVERRIDES = {
    "MD-700": {
        "WB_CN_Online": {
            "available_qty": 131,
            "in_transit_qty": 0,
            "locked_qty": 0,
        },
        "WB_CN_Reserve": {
            "available_qty": 150,  # 未上架储备
            "in_transit_qty": 0,
            "locked_qty": 0,
        },
    },
    "TX-850 PRO": {
        "WB_CN_Online": {
            "available_qty": 29,
            "in_transit_qty": 0,
            "locked_qty": 0,
        },
        "WB_CN_Reserve": {
            "available_qty": 24,  # 未上架
            "in_transit_qty": 0,
            "locked_qty": 0,
        },
    },
    "MD-4090 PRO": {
        "WB_CN_Online": {
            "available_qty": 37,
            "in_transit_qty": 0,
            "locked_qty": 0,
        },
        "WB_CN_Reserve": {
            "available_qty": 10,  # 未上架
            "in_transit_qty": 0,
            "locked_qty": 0,
        },
    },
}


def ensure_data_dirs() -> None:
    """Ensure data directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MANUAL_OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)


def load_manual_stock_snapshot() -> dict[str, Any]:
    """Load manual WB stock snapshot if available.

    Expected file: data/manual_overrides/wb_cn_stock_snapshot_*.json
    Format: List of {sku, platform, location, available_qty, in_transit_qty, locked_qty}

    Returns:
        Dict mapping (sku, location) to quantities, or empty if not found
    """
    snapshot_files = list(MANUAL_OVERRIDES_DIR.glob("wb_cn_stock_snapshot_*.json"))
    if not snapshot_files:
        return {}

    # Use most recent snapshot
    snapshot_file = sorted(snapshot_files)[-1]
    try:
        data = json.loads(snapshot_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            result = {}
            for row in data:
                sku = row.get("sku", "").strip()
                location = row.get("location", "unknown")
                result[(sku, location)] = {
                    "available_qty": int(row.get("available_qty") or 0),
                    "in_transit_qty": int(row.get("in_transit_qty") or 0),
                    "locked_qty": int(row.get("locked_qty") or 0),
                }
            return result
    except Exception:
        pass

    return {}


def load_logistics_inventory() -> dict[str, dict[str, int]]:
    """Load EasyWarehouse logistics inventory if available.

    Expected file: data/manual_overrides/wb_cn_logistics_reserve_manual_*.csv
    Format: sku,platform,location,available_qty,in_transit_qty,locked_qty

    Returns:
        Dict mapping (sku, location) to quantities, or empty if not found
    """
    logistics_files = list(MANUAL_OVERRIDES_DIR.glob("wb_cn_logistics_reserve_manual_*.csv"))
    if not logistics_files:
        return {}

    # Use most recent logistics file
    logistics_file = sorted(logistics_files)[-1]
    try:
        result = {}
        with open(logistics_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row.get("sku", "").strip()
                location = row.get("location", "unknown")
                result[(sku, location)] = {
                    "available_qty": int(row.get("available_qty") or 0),
                    "in_transit_qty": int(row.get("in_transit_qty") or 0),
                    "locked_qty": int(row.get("locked_qty") or 0),
                }
        return result
    except Exception:
        pass

    return {}


def aggregate_inventory() -> list[dict[str, Any]]:
    """Aggregate inventory from all sources.

    Priority: Manual overrides > Stock snapshot > Logistics > Default empty

    Returns:
        List of aggregated inventory rows
    """
    ensure_data_dirs()

    # Load data sources
    stock_snapshot = load_manual_stock_snapshot()
    logistics_inventory = load_logistics_inventory()

    # Aggregate by (sku, location)
    aggregated = {}

    # Step 1: Apply manual overrides (highest priority)
    for sku, locations in MANUAL_OVERRIDES.items():
        for location, quantities in locations.items():
            aggregated[(sku, location)] = {
                "sku": sku,
                "platform": "WB_CN",
                "location": location,
                **quantities,
            }

    # Step 2: Apply stock snapshot (if not already overridden)
    for (sku, location), quantities in stock_snapshot.items():
        if (sku, location) not in aggregated and sku in VALID_SKUS:
            aggregated[(sku, location)] = {
                "sku": sku,
                "platform": "WB_CN",
                "location": location,
                **quantities,
            }

    # Step 3: Apply logistics inventory (if not already overridden)
    for (sku, location), quantities in logistics_inventory.items():
        if (sku, location) not in aggregated and sku in VALID_SKUS:
            aggregated[(sku, location)] = {
                "sku": sku,
                "platform": "WB_CN",
                "location": location,
                **quantities,
            }

    # Convert to sorted list
    rows = sorted(aggregated.values(), key=lambda x: (x["sku"], x["location"]))

    return rows


def write_inventory_csv(rows: list[dict[str, Any]]) -> Path:
    """Write aggregated inventory to CSV file.

    Args:
        rows: List of inventory row dicts

    Returns:
        Path to written CSV file
    """
    ensure_data_dirs()

    # Write CSV with required columns
    fieldnames = ["sku", "platform", "location", "available_qty", "in_transit_qty", "locked_qty"]

    INVENTORY_INPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(INVENTORY_INPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({f: row.get(f, "") for f in fieldnames})

    return INVENTORY_INPUT


def main() -> None:
    """Main sync and aggregation routine."""
    parser = argparse.ArgumentParser(
        description="Sync and aggregate WB_CN inventory from multiple sources"
    )
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="Skip model execution (default behavior)"
    )
    args = parser.parse_args()

    print(f"[Sync] Starting inventory aggregation...")
    print(f"[Sync] Data directory: {DATA_DIR}")
    print(f"[Sync] Manual overrides directory: {MANUAL_OVERRIDES_DIR}")

    # Aggregate inventory from all sources
    rows = aggregate_inventory()
    print(f"[Sync] Aggregated {len(rows)} inventory rows")

    # Write to CSV
    output_csv = write_inventory_csv(rows)
    print(f"[Sync] ✓ Wrote inventory to: {output_csv}")
    print(f"[Sync] ✓ File size: {output_csv.stat().st_size} bytes")

    # Print summary
    skus = set(row["sku"] for row in rows)
    print(f"[Sync] SKUs in inventory: {sorted(skus)}")

    # Print per-SKU totals
    sku_totals = {}
    for row in rows:
        sku = row["sku"]
        if sku not in sku_totals:
            sku_totals[sku] = {"available": 0, "transit": 0, "locked": 0}
        sku_totals[sku]["available"] += int(row.get("available_qty") or 0)
        sku_totals[sku]["transit"] += int(row.get("in_transit_qty") or 0)
        sku_totals[sku]["locked"] += int(row.get("locked_qty") or 0)

    print(f"\n[Sync] Inventory summary by SKU:")
    for sku in sorted(sku_totals.keys()):
        totals = sku_totals[sku]
        print(
            f"  {sku}: available={totals['available']}, "
            f"transit={totals['transit']}, locked={totals['locked']}"
        )

    print(f"\n[Sync] ✓ Aggregation complete at {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()

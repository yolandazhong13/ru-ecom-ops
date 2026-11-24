#!/usr/bin/env python3
"""Concrete ActionHandler for inventory aggregation on WB_CN.

Wraps the sync_wb_cn_inventory_inputs.py and fetch_logistics_inventory.py
logic into a reusable handler that works with UnifiedActionExecutor.

This handler:
1. Optionally fetches latest warehouse inventory via logistics provider
2. Aggregates inventory from multiple sources (WB stock, logistics, order history)
3. Validates aggregated data consistency
4. Returns normalized inventory dict and updated CSV file path
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "assets/config.yaml"
INVENTORY_INPUT = ROOT / "data" / "inventory_decision_input.csv"
SKU_BY_VENDOR = {
    "wb1xx5bipa": "MD-700",
    "wbffpchf2": "MD-4090 PRO",
    "wbvekz0hmy": "TX-850 PRO",
    "wbfqr1iycq": "TX-850",
    "wbs7jfvwmm": "MD-4090",
    "wbgd52d0ib": "MD-700 BLACK",
}


class InventoryAggregationError(Exception):
    """Raised when inventory aggregation fails."""
    pass


class InventoryActionHandler(ActionHandler):
    """Handles inventory aggregation and validation for WB_CN.

    Aggregates inventory from multiple sources:
    - WB backend stock snapshots (JSON)
    - EasyWarehouse physical inventory (CSV from logistics provider)
    - Recent order rates (JSON from historical diagnostics)

    This is a read-only handler — no platform state modifications occur.
    """

    def __init__(
        self,
        client_id: str,
        mode: str = "sync_and_aggregate",
        fetch_logistics: bool = False,
    ):
        """Initialize handler with aggregation mode.

        Args:
            client_id: WB client identifier (e.g., "wb_cn")
            mode: Aggregation mode:
                - "sync_and_aggregate": Run full sync with all sources
                - "fetch_only": Only fetch latest logistics data
            fetch_logistics: Whether to call fetch_logistics_inventory.py script
        """
        self.client_id = str(client_id)
        self.mode = mode
        self.fetch_logistics = fetch_logistics
        self.inventory_before = None
        self.inventory_after = None
        self.aggregation_report = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute inventory aggregation per content_for_approval.

        Args:
            content: Approval content with mode and options

        Returns:
            Dict with aggregated inventory, file paths, and aggregation details
        """
        # Optionally fetch latest logistics inventory
        logistics_csv = None
        if self.fetch_logistics:
            logistics_csv = self._fetch_logistics_inventory()

        # Read inventory state before aggregation
        self.inventory_before = self._read_inventory_csv(INVENTORY_INPUT)

        # Run aggregation sync
        aggregated_csv = self._run_sync_aggregation(INVENTORY_INPUT)

        # Read aggregated inventory state
        self.inventory_after = self._read_inventory_csv(aggregated_csv)

        # Parse aggregated data
        aggregated_dict = self._parse_inventory_rows(self.inventory_after)

        return {
            "mode": self.mode,
            "inventory_before": self.inventory_before,
            "inventory_after": self.inventory_after,
            "aggregated_dict": aggregated_dict,
            "output_csv": str(aggregated_csv),
            "logistics_csv": str(logistics_csv) if logistics_csv else None,
            "row_count_before": len(self.inventory_before or []),
            "row_count_after": len(self.inventory_after or []),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution validation of aggregated inventory data.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with consistency checks and status
        """
        inventory_after = execution_result.get("inventory_after", [])
        aggregated_dict = execution_result.get("aggregated_dict", {})

        validation_checks = {
            "csv_exists": False,
            "csv_readable": False,
            "all_rows_have_required_columns": False,
            "all_sku_mappings_valid": False,
            "all_numeric_fields_valid": False,
            "row_count_increased_or_stable": False,
        }

        error_details = []

        # Check 1: CSV file exists and is readable
        output_csv = execution_result.get("output_csv")
        if output_csv:
            csv_path = Path(output_csv)
            if csv_path.exists():
                validation_checks["csv_exists"] = True
                try:
                    with open(csv_path, "r", encoding="utf-8") as f:
                        csv.DictReader(f)
                    validation_checks["csv_readable"] = True
                except Exception as e:
                    error_details.append(f"CSV read error: {e}")
            else:
                error_details.append(f"Output CSV not found: {output_csv}")

        # Check 2: All rows have required columns
        required_columns = {
            "sku", "platform", "location", "available_qty", "in_transit_qty", "locked_qty"
        }
        if inventory_after:
            missing_columns = set()
            for row in inventory_after:
                for col in required_columns:
                    if col not in row or row[col] is None:
                        missing_columns.add(col)
            if not missing_columns:
                validation_checks["all_rows_have_required_columns"] = True
            else:
                error_details.append(f"Missing columns: {missing_columns}")

        # Check 3: All SKU mappings are valid
        if aggregated_dict:
            invalid_skus = []
            for sku in aggregated_dict.keys():
                # Validate SKU format or presence in mapping
                if not self._is_valid_sku(sku):
                    invalid_skus.append(sku)
            if not invalid_skus:
                validation_checks["all_sku_mappings_valid"] = True
            else:
                error_details.append(f"Invalid SKUs: {invalid_skus}")

        # Check 4: All numeric fields are valid and consistent
        numeric_valid = True
        for row in inventory_after:
            try:
                avail = int(row.get("available_qty") or 0)
                in_transit = int(row.get("in_transit_qty") or 0)
                locked = int(row.get("locked_qty") or 0)
                # Basic consistency: quantities should be non-negative
                if avail < 0 or in_transit < 0 or locked < 0:
                    numeric_valid = False
                    error_details.append(
                        f"Negative quantities for {row.get('sku')}: "
                        f"avail={avail}, transit={in_transit}, locked={locked}"
                    )
            except (ValueError, TypeError):
                numeric_valid = False
                error_details.append(f"Non-numeric quantity in row: {row}")
        validation_checks["all_numeric_fields_valid"] = numeric_valid

        # Check 5: Row count increased or stayed stable
        before_count = execution_result.get("row_count_before", 0)
        after_count = execution_result.get("row_count_after", 0)
        if after_count >= before_count:
            validation_checks["row_count_increased_or_stable"] = True

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_inventory_aggregation" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "row_count_delta": after_count - before_count,
            "sku_count": len(aggregated_dict),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _fetch_logistics_inventory(self) -> Path | None:
        """Call fetch_logistics_inventory.py to get latest warehouse data.

        Returns:
            Path to output CSV if successful, None if skipped or failed
        """
        script = ROOT / "scripts" / "fetch_logistics_inventory.py"
        if not script.exists():
            return None

        try:
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                # Parse output to find CSV path
                # fetch_logistics_inventory.py should print the output path
                for line in result.stdout.split("\n"):
                    if "data/manual_overrides/" in line and ".csv" in line:
                        csv_path = ROOT / line.strip()
                        if csv_path.exists():
                            return csv_path
            else:
                raise InventoryAggregationError(
                    f"fetch_logistics_inventory.py failed: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            raise InventoryAggregationError("fetch_logistics_inventory.py timed out")
        except Exception as e:
            raise InventoryAggregationError(f"Failed to fetch logistics inventory: {e}")

        return None

    def _run_sync_aggregation(self, input_csv: Path) -> Path:
        """Run sync_wb_cn_inventory_inputs.py to aggregate all sources.

        Args:
            input_csv: Path to inventory decision input CSV

        Returns:
            Path to aggregated output CSV
        """
        script = ROOT / "scripts" / "sync_wb_cn_inventory_inputs.py"
        if not script.exists():
            raise InventoryAggregationError(f"Sync script not found: {script}")

        try:
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--skip-model",  # Don't run the model, just sync
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                raise InventoryAggregationError(
                    f"sync_wb_cn_inventory_inputs.py failed: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            raise InventoryAggregationError("sync_wb_cn_inventory_inputs.py timed out")
        except Exception as e:
            raise InventoryAggregationError(f"Failed to run sync aggregation: {e}")

        # Return the input CSV (it's been updated in-place)
        return input_csv

    def _read_inventory_csv(self, csv_path: Path) -> list[dict]:
        """Read inventory CSV into list of dicts.

        Args:
            csv_path: Path to inventory CSV

        Returns:
            List of inventory row dicts
        """
        if not csv_path.exists():
            return []

        rows = []
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            raise InventoryAggregationError(f"Failed to read CSV {csv_path}: {e}")

        return rows

    def _parse_inventory_rows(self, rows: list[dict]) -> dict[str, dict]:
        """Parse CSV rows into aggregated inventory dict.

        Args:
            rows: List of inventory row dicts from CSV

        Returns:
            Dict mapping SKU to aggregated inventory data
        """
        result = {}
        for row in rows:
            sku = row.get("sku", "").strip()
            if not sku:
                continue

            if sku not in result:
                result[sku] = {
                    "sku": sku,
                    "platform": row.get("platform", "WB_CN"),
                    "total_available": 0,
                    "total_in_transit": 0,
                    "total_locked": 0,
                    "locations": [],
                }

            try:
                avail = int(row.get("available_qty") or 0)
                transit = int(row.get("in_transit_qty") or 0)
                locked = int(row.get("locked_qty") or 0)

                result[sku]["total_available"] += avail
                result[sku]["total_in_transit"] += transit
                result[sku]["total_locked"] += locked

                location = row.get("location", "unknown")
                if location:
                    result[sku]["locations"].append(location)
            except (ValueError, TypeError):
                pass

        return result

    def _is_valid_sku(self, sku: str) -> bool:
        """Check if SKU is valid.

        Args:
            sku: SKU identifier

        Returns:
            True if SKU is valid, False otherwise
        """
        # Valid if it's a known WB_CN SKU
        known_skus = {
            "MD-700",
            "MD-700 BLACK",
            "MD-4090",
            "MD-4090 PRO",
            "TX-850",
            "TX-850 PRO",
        }
        return sku in known_skus

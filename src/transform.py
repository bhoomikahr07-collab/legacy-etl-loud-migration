"""
Transform: implements every rule in mapping_specs/source_to_target_mapping.md.

Each parsing helper returns `None` on failure rather than raising, so a
single bad row never crashes the batch — it gets tagged with a reason
and routed to quarantine, mirroring the legacy Lookup/error-redirect
pattern instead of the truncate-and-reload all-or-nothing behavior it
replaces.

Usage:
    python src/transform.py --env local
"""
import argparse
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from schema import CUSTOMER_TARGET_FIELDS, ORDER_TARGET_FIELDS, STATUS_CODE_MAP
from utils import load_config
from extract import extract


def parse_legacy_date(value: str):
    """MM/DD/YYYY -> ISO YYYY-MM-DD, or None if unparseable."""
    try:
        return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
    except (ValueError, AttributeError):
        return None


def parse_flag(value: str):
    """'Y'/'N' -> True/False, or None for anything else (incl. blank)."""
    v = (value or "").strip().upper()
    if v == "Y":
        return True
    if v == "N":
        return False
    return None


def parse_currency(value: str):
    """'$1,204.50' -> Decimal('1204.50'); rejects negative or unparsable
    values, or None if unparseable/invalid."""
    try:
        cleaned = value.strip().replace("$", "").replace(",", "")
        amount = Decimal(cleaned)
        if amount < 0:
            return None
        return amount
    except (InvalidOperation, AttributeError):
        return None


def map_status_code(value: str):
    return STATUS_CODE_MAP.get((value or "").strip().upper())


def transform_customers(customers):
    clean, quarantined = [], []
    for row in customers:
        reasons = []
        is_active = parse_flag(row.get("ACTIVE_FLG"))
        if is_active is None:
            reasons.append("invalid_active_flag")

        signup_date = parse_legacy_date(row.get("SIGNUP_DT"))
        if signup_date is None:
            reasons.append("invalid_signup_date")

        if reasons:
            quarantined.append({**row, "_reason": ",".join(reasons)})
            continue

        clean.append({
            "customer_id": row["CUST_ID"].strip(),
            "customer_name": row["CUST_NM"].strip(),
            "is_active": is_active,
            "signup_date": signup_date,
            "region_code": row["REGION_CD"].strip().upper(),
        })
    return clean, quarantined


def transform_orders(orders, valid_customer_ids: set):
    clean, quarantined = [], []
    for row in orders:
        reasons = []

        if row.get("CUST_ID") not in valid_customer_ids:
            reasons.append("orphaned_order_no_matching_customer")

        order_date = parse_legacy_date(row.get("ORD_DT"))
        if order_date is None:
            reasons.append("invalid_order_date")

        order_amount = parse_currency(row.get("ORD_AMT"))
        if order_amount is None:
            reasons.append("invalid_or_negative_order_amount")

        order_status = map_status_code(row.get("STATUS_CD"))
        if order_status is None:
            reasons.append("unmapped_status_code")

        if reasons:
            quarantined.append({**row, "_reason": ",".join(reasons)})
            continue

        clean.append({
            "order_id": row["ORD_ID"].strip(),
            "customer_id": row["CUST_ID"].strip(),
            "order_date": order_date,
            "order_amount": str(order_amount),
            "order_status": order_status,
        })
    return clean, quarantined


def run_transform(customers_raw, orders_raw):
    clean_customers, quarantined_customers = transform_customers(customers_raw)
    valid_customer_ids = {c["customer_id"] for c in clean_customers}
    clean_orders, quarantined_orders = transform_orders(orders_raw, valid_customer_ids)
    return {
        "customers": clean_customers,
        "customers_quarantined": quarantined_customers,
        "orders": clean_orders,
        "orders_quarantined": quarantined_orders,
    }


def main(env):
    cfg = load_config(env)
    customers_raw, orders_raw = extract(cfg["source_path"])
    result = run_transform(customers_raw, orders_raw)

    print(f"[transform] customers: {len(result['customers'])} clean, "
          f"{len(result['customers_quarantined'])} quarantined")
    print(f"[transform] orders: {len(result['orders'])} clean, "
          f"{len(result['orders_quarantined'])} quarantined")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["local", "dev", "test", "prod"], default="local")
    args = parser.parse_args()
    main(args.env)

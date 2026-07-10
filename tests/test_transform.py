"""
Unit tests for the mapping-spec transform logic. Pure stdlib unittest —
no Spark, no AWS — so this runs anywhere.

Usage:
    python -m unittest discover tests -v
"""
import os
import sys
import unittest
from decimal import Decimal

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from transform import (
    parse_legacy_date, parse_flag, parse_currency, map_status_code,
    transform_customers, transform_orders, run_transform,
)


class TestParsers(unittest.TestCase):
    def test_parse_legacy_date_valid(self):
        self.assertEqual(parse_legacy_date("06/01/2026"), "2026-06-01")

    def test_parse_legacy_date_invalid(self):
        self.assertIsNone(parse_legacy_date("13/40/2026"))
        self.assertIsNone(parse_legacy_date("not a date"))
        self.assertIsNone(parse_legacy_date(""))

    def test_parse_flag(self):
        self.assertTrue(parse_flag("Y"))
        self.assertFalse(parse_flag("N"))
        self.assertIsNone(parse_flag(""))
        self.assertIsNone(parse_flag("maybe"))

    def test_parse_currency_valid(self):
        self.assertEqual(parse_currency("$1,204.50"), Decimal("1204.50"))
        self.assertEqual(parse_currency("50.00"), Decimal("50.00"))

    def test_parse_currency_rejects_negative(self):
        self.assertIsNone(parse_currency("-$25.00"))

    def test_parse_currency_rejects_unparseable(self):
        self.assertIsNone(parse_currency("TBD"))

    def test_map_status_code(self):
        self.assertEqual(map_status_code("O"), "open")
        self.assertEqual(map_status_code("c"), "completed")
        self.assertIsNone(map_status_code("Z"))


class TestTransformCustomers(unittest.TestCase):
    def test_valid_row_passes(self):
        rows = [{"CUST_ID": "C1", "CUST_NM": "  Alice  ", "ACTIVE_FLG": "Y",
                 "SIGNUP_DT": "01/15/2025", "REGION_CD": "ne"}]
        clean, quarantined = transform_customers(rows)
        self.assertEqual(len(clean), 1)
        self.assertEqual(len(quarantined), 0)
        self.assertEqual(clean[0]["customer_name"], "Alice")
        self.assertEqual(clean[0]["region_code"], "NE")
        self.assertTrue(clean[0]["is_active"])

    def test_blank_flag_quarantined(self):
        rows = [{"CUST_ID": "C1", "CUST_NM": "Alice", "ACTIVE_FLG": "",
                 "SIGNUP_DT": "01/15/2025", "REGION_CD": "NE"}]
        clean, quarantined = transform_customers(rows)
        self.assertEqual(len(clean), 0)
        self.assertEqual(len(quarantined), 1)
        self.assertIn("invalid_active_flag", quarantined[0]["_reason"])

    def test_bad_date_quarantined(self):
        rows = [{"CUST_ID": "C1", "CUST_NM": "Alice", "ACTIVE_FLG": "Y",
                 "SIGNUP_DT": "13/40/2025", "REGION_CD": "NE"}]
        clean, quarantined = transform_customers(rows)
        self.assertEqual(len(clean), 0)
        self.assertIn("invalid_signup_date", quarantined[0]["_reason"])


class TestTransformOrders(unittest.TestCase):
    def test_valid_order_passes(self):
        rows = [{"ORD_ID": "O1", "CUST_ID": "C1", "ORD_DT": "06/01/2026",
                 "ORD_AMT": "$99.99", "STATUS_CD": "O"}]
        clean, quarantined = transform_orders(rows, valid_customer_ids={"C1"})
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["order_status"], "open")
        self.assertEqual(clean[0]["order_amount"], "99.99")

    def test_orphaned_order_quarantined(self):
        rows = [{"ORD_ID": "O1", "CUST_ID": "C999", "ORD_DT": "06/01/2026",
                 "ORD_AMT": "$99.99", "STATUS_CD": "O"}]
        clean, quarantined = transform_orders(rows, valid_customer_ids={"C1"})
        self.assertEqual(len(clean), 0)
        self.assertIn("orphaned_order_no_matching_customer", quarantined[0]["_reason"])

    def test_negative_amount_quarantined(self):
        rows = [{"ORD_ID": "O1", "CUST_ID": "C1", "ORD_DT": "06/01/2026",
                 "ORD_AMT": "-$25.00", "STATUS_CD": "O"}]
        clean, quarantined = transform_orders(rows, valid_customer_ids={"C1"})
        self.assertEqual(len(clean), 0)
        self.assertIn("invalid_or_negative_order_amount", quarantined[0]["_reason"])

    def test_unmapped_status_quarantined(self):
        rows = [{"ORD_ID": "O1", "CUST_ID": "C1", "ORD_DT": "06/01/2026",
                 "ORD_AMT": "$25.00", "STATUS_CD": "Z"}]
        clean, quarantined = transform_orders(rows, valid_customer_ids={"C1"})
        self.assertEqual(len(clean), 0)
        self.assertIn("unmapped_status_code", quarantined[0]["_reason"])

    def test_multiple_reasons_all_captured(self):
        rows = [{"ORD_ID": "O1", "CUST_ID": "C999", "ORD_DT": "bad",
                 "ORD_AMT": "TBD", "STATUS_CD": "Z"}]
        clean, quarantined = transform_orders(rows, valid_customer_ids={"C1"})
        reasons = quarantined[0]["_reason"]
        self.assertIn("orphaned_order_no_matching_customer", reasons)
        self.assertIn("invalid_order_date", reasons)
        self.assertIn("invalid_or_negative_order_amount", reasons)
        self.assertIn("unmapped_status_code", reasons)


class TestRunTransformIntegration(unittest.TestCase):
    def test_orphaned_order_uses_clean_customer_ids_only(self):
        customers = [{"CUST_ID": "C1", "CUST_NM": "Alice", "ACTIVE_FLG": "",
                      "SIGNUP_DT": "01/15/2025", "REGION_CD": "NE"}]
        orders = [{"ORD_ID": "O1", "CUST_ID": "C1", "ORD_DT": "06/01/2026",
                   "ORD_AMT": "$50.00", "STATUS_CD": "O"}]
        result = run_transform(customers, orders)
        self.assertEqual(len(result["customers"]), 0)
        self.assertEqual(len(result["orders"]), 0)
        self.assertIn("orphaned_order_no_matching_customer", result["orders_quarantined"][0]["_reason"])


if __name__ == "__main__":
    unittest.main()

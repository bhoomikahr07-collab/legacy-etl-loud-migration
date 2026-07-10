"""Target schema field lists — used to keep transform.py output columns
consistent with mapping_specs/source_to_target_mapping.md."""

CUSTOMER_TARGET_FIELDS = ["customer_id", "customer_name", "is_active", "signup_date", "region_code"]
ORDER_TARGET_FIELDS = ["order_id", "customer_id", "order_date", "order_amount", "order_status"]

STATUS_CODE_MAP = {"O": "open", "S": "shipped", "C": "completed", "X": "cancelled"}

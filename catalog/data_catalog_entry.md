# Data Catalog Entry

## Dataset: `customers`

| Field | Value |
|---|---|
| **Description** | Customer master data, migrated from the legacy `RPT_CUSTOMERS` SQL Server table |
| **Owner** | Data Engineering (migration), Customer Data team (business owner) |
| **Source system** | On-prem SQL Server → nightly flat-file extract (`CUST_EXTRACT.csv`) |
| **Target location** | `s3://<bucket>/curated/legacy-migration/customers.csv` |
| **Refresh cadence** | Daily, 01:00 UTC (matches legacy SSIS schedule) |
| **Schema** | `customer_id` (string, PK), `customer_name` (string), `is_active` (boolean), `signup_date` (date, ISO-8601), `region_code` (string, 2-char) |
| **PII** | `customer_name` — treat as PII; access restricted per standard data governance policy |
| **Lineage** | `CUST_EXTRACT.csv` (legacy SQL Server export) → `src/transform.py::transform_customers` → `customers.csv` |
| **Known data quality issues** | Rows with an invalid `ACTIVE_FLG` or unparseable `SIGNUP_DT` are routed to `quarantine/customers_quarantine.csv` rather than loaded — see `mapping_specs/source_to_target_mapping.md` |
| **Downstream consumers** | Analytics/BI tools reading from the curated S3 zone |

## Dataset: `orders`

| Field | Value |
|---|---|
| **Description** | Order transactions, migrated from the legacy `RPT_ORDERS` SQL Server table |
| **Owner** | Data Engineering (migration), Sales Ops (business owner) |
| **Source system** | On-prem SQL Server → nightly flat-file extract (`ORD_EXTRACT.csv`) |
| **Target location** | `s3://<bucket>/curated/legacy-migration/orders.csv` |
| **Refresh cadence** | Daily, 01:00 UTC |
| **Schema** | `order_id` (string, PK), `customer_id` (string, FK → `customers.customer_id`), `order_date` (date, ISO-8601), `order_amount` (decimal, 2dp), `order_status` (string: `open`\|`shipped`\|`completed`\|`cancelled`) |
| **PII** | None directly; joins to `customers` for PII |
| **Lineage** | `ORD_EXTRACT.csv` → `src/transform.py::transform_orders` → `orders.csv` |
| **Known data quality issues** | Orphaned orders (no matching `customer_id`), unparseable/negative amounts, and unmapped status codes are quarantined — see `mapping_specs/source_to_target_mapping.md` |
| **Downstream consumers** | Analytics/BI tools reading from the curated S3 zone |

## Sensitivity classification

- `customers.customer_name` → **Internal — PII**
- All other fields → **Internal — Non-PII**

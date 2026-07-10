# Source-to-Target Mapping Spec

**Source system**: on-prem SQL Server, nightly flat-file extract
**Target**: S3 curated zone (CSV), analytics-ready schema
**Owner**: Data Engineering
**Status**: Migrated (see `src/transform.py` for the implementation of every rule below)

## `customers`

| Source column (legacy) | Source type/format      | Target column   | Target type | Transformation rule                                          | Notes |
|---|---|---|---|---|---|
| `CUST_ID`         | string, e.g. `C10234`     | `customer_id`    | string        | direct copy                                                   | primary key |
| `CUST_NM`         | string                     | `customer_name`  | string        | trim whitespace                                               | |
| `ACTIVE_FLG`      | `Y` / `N`                  | `is_active`      | boolean       | `Y` → `true`, `N` → `false`, anything else → quarantine        | legacy source occasionally has blank values |
| `SIGNUP_DT`       | `MM/DD/YYYY` string        | `signup_date`    | date (ISO)    | parse `MM/DD/YYYY` → `YYYY-MM-DD`                              | invalid/unparseable dates → quarantine |
| `REGION_CD`       | 2-letter code              | `region_code`    | string        | uppercase                                                      | |

## `orders`

| Source column (legacy) | Source type/format      | Target column   | Target type | Transformation rule                                          | Notes |
|---|---|---|---|---|---|
| `ORD_ID`          | string, e.g. `O88213`     | `order_id`       | string        | direct copy                                                   | primary key |
| `CUST_ID`         | string                     | `customer_id`    | string        | direct copy                                                   | must exist in `customers` — orphaned orders are quarantined, mirroring the legacy Lookup transform's error-redirect |
| `ORD_DT`          | `MM/DD/YYYY` string        | `order_date`     | date (ISO)    | parse `MM/DD/YYYY` → `YYYY-MM-DD`                              | |
| `ORD_AMT`         | currency string, e.g. `$1,204.50` | `order_amount` | decimal(10,2) | strip `$`/commas, cast to decimal                              | negative or unparsable → quarantine |
| `STATUS_CD`       | `O`/`S`/`C`/`X`             | `order_status`   | string        | `O`→`open`, `S`→`shipped`, `C`→`completed`, `X`→`cancelled`     | unmapped codes → quarantine |

## Quarantine handling

Any row that fails a mapping rule (marked "quarantine" above) is written
to `<target>/quarantine/<table>/` with a `_reason` column appended,
instead of being silently dropped or crashing the job — same principle
used in the other pipelines in this portfolio.

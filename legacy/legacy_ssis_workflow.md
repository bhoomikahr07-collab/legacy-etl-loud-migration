# Legacy Workflow: `SSIS_Customer_Order_Extract`

This documents the legacy on-prem workflow being migrated. In a real
migration this section would summarize the actual `.dtsx` package(s);
here it's written out as the reference spec this project migrates from.

## Overview

- **Type**: SQL Server Integration Services (SSIS) package
- **Schedule**: SQL Server Agent job, nightly at 01:00 local time
- **Source**: `CUSTOMERS` and `ORDERS` tables in an on-prem SQL Server
  instance, exported nightly to flat files by an upstream DBA process
  (`CUST_EXTRACT_YYYYMMDD.csv`, `ORD_EXTRACT_YYYYMMDD.csv`)
- **Target (legacy)**: a reporting SQL Server database, `RPT_CUSTOMERS`
  and `RPT_ORDERS` tables, consumed by an on-prem SSRS report
- **Target (migrated)**: S3 (curated zone), consumed by downstream
  analytics/BI tools

## Control flow (legacy)

1. **File Watcher Task** — waits for both extract files to land in the
   drop folder.
2. **Data Flow Task: Load Customers**
   - Flat File Source → Derived Column (trim strings, standardize
     `ACTIVE_FLG`) → Data Conversion (legacy `MM/DD/YYYY` string dates →
     SQL `datetime`) → OLE DB Destination (`RPT_CUSTOMERS`, truncate +
     reload)
3. **Data Flow Task: Load Orders**
   - Flat File Source → Lookup (validate `CUST_ID` exists in
     `RPT_CUSTOMERS`, redirect no-match rows to an error file) → Derived
     Column (parse `ORD_AMT` currency string to decimal) → OLE DB
     Destination (`RPT_ORDERS`, truncate + reload)
4. **Send Mail Task** — emails the ops distribution list with row counts
   and any redirected error-row count.

## Known pain points (why this is being migrated)

- Truncate-and-reload has no incremental/idempotent story — a failed
  mid-run leaves the reporting tables half-loaded.
- No structured logging beyond the SSIS execution log; row-count anomalies
  are only caught if someone reads the email.
- Runs on a single on-prem SQL Server Agent job — no environment
  separation (dev/test changes are tested directly against prod-adjacent
  infrastructure).
- No automated tests; validation is "does the report look right."

## What the cloud-native version keeps the same

- Same source shape (customer + order flat-file extracts).
- Same core transformations (date parsing, currency parsing, active-flag
  normalization, orphaned-order validation).

## What it changes

- Truncate+reload → the target is rewritten per run but the *pipeline*
  is now versioned, tested, and environment-separated (dev/test/prod) via CI/CD.
- Email-only monitoring → structured logs + a documented runbook.
- No tests → unit-tested transform logic (`tests/test_transform.py`).
- Manual `.dtsx` editing → version-controlled Python in this repo.

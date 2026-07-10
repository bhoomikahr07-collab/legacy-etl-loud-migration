# Runbook: Legacy Customer/Order Migration Pipeline

**Purpose**: extracts, transforms, and loads customer and order data
from the legacy nightly SQL Server export into the S3 curated zone,
replacing the legacy SSIS package described in `legacy/legacy_ssis_workflow.md`.

**Owner**: Data Engineering
**Schedule**: Daily, 01:00 UTC, triggered as an AWS Glue Python Shell job
**On-call**: see team paging rotation (not included in this sample repo)

## Running it manually

```bash
# Local (no AWS needed)
python src/extract.py --env local
python src/transform.py --env local
python src/load.py --env local

# Against a real environment (requires AWS credentials with access to
# the target bucket)
python src/load.py --env dev
```

Or trigger the deployed Glue job directly:

```bash
aws glue start-job-run --job-name legacy-migration-<env>
```

## Monitoring

- Glue job run history: AWS Glue console → Jobs → `legacy-migration-<env>` → Runs.
- Row counts (`clean` vs `quarantined`) are printed to the job's
  CloudWatch log group on every run — check these first for anomalies.
- A sudden spike in quarantined rows usually means the upstream extract
  format changed (e.g., a new `STATUS_CD` value, or a currency format
  change) — check `mapping_specs/source_to_target_mapping.md` to see if
  the mapping needs updating.

## Common failures & fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Job fails at `extract()` with a missing-file error | Upstream extract didn't land in the source path in time | Check the upstream export job; re-run manually once the file exists |
| Large spike in `orders_quarantine.csv` with `orphaned_order_no_matching_customer` | Customer extract and order extract are from different dates (out of sync) | Confirm both extracts are from the same nightly batch before re-running |
| Large spike in `invalid_or_negative_order_amount` | Upstream changed the currency format, or a batch of refunds was miscoded as orders | Check a sample of quarantined rows; update `parse_currency()` in `src/transform.py` if the format genuinely changed, otherwise escalate to Sales Ops |
| `unmapped_status_code` spike | A new order status code was introduced upstream | Add the new code to `STATUS_CODE_MAP` in `src/schema.py` after confirming its meaning with Sales Ops |
| S3 upload step fails | Glue job role lacks `s3:PutObject` on the target bucket, or bucket policy changed | Check IAM role permissions for the Glue job |

## Rollback

The target write is a full overwrite of `customers.csv` / `orders.csv`
each run (matching the legacy truncate-and-reload behavior). To roll
back to a previous day's output:

1. S3 versioning should be enabled on the curated bucket (recommended
   but not yet enforced in this sample — see `catalog/data_catalog_entry.md`
   for the target location).
2. Restore the previous object version via `aws s3api list-object-versions`
   + `aws s3api copy-object`, or the S3 console's "Versions" tab.

## Escalation

- Mapping/business-logic questions → Sales Ops / Customer Data team (business owners, see `catalog/data_catalog_entry.md`)
- Infrastructure/Glue/IAM issues → Cloud Platform team
- Pipeline code issues → Data Engineering (this repo's maintainers)

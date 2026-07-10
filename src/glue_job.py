"""
AWS Glue Python Shell job entry point.

Deploy as a Glue **Python Shell** job (not Spark — see README for why).
Wraps extract/transform/load with the argument-parsing convention Glue
Python Shell jobs use (`--JOB_NAME` plus custom `--` args set on the job
or job run).

Glue job parameters:
    --ENV           dev | test | prod
    --SOURCE_PATH   s3://<bucket>/legacy-raw/   (or local path for testing)
    --TARGET_PATH   s3://<bucket>/curated/legacy-migration/
"""
import os
import sys

from awsglue.utils import getResolvedOptions

sys.path.append("/tmp/glue_deps")  # Glue job packaging drops extra .py files here
from extract import extract          # noqa: E402
from transform import run_transform  # noqa: E402
from load import write_csv_local, upload_to_s3  # noqa: E402
from schema import CUSTOMER_TARGET_FIELDS, ORDER_TARGET_FIELDS  # noqa: E402

args = getResolvedOptions(sys.argv, ["JOB_NAME", "ENV", "SOURCE_PATH", "TARGET_PATH"])

env = args["ENV"]
source_path = args["SOURCE_PATH"]
target_path = args["TARGET_PATH"]

print(f"[glue_job] starting legacy migration job, env={env}")

customers_raw, orders_raw = extract(source_path)
result = run_transform(customers_raw, orders_raw)

print(f"[glue_job] customers: {len(result['customers'])} clean, "
      f"{len(result['customers_quarantined'])} quarantined")
print(f"[glue_job] orders: {len(result['orders'])} clean, "
      f"{len(result['orders_quarantined'])} quarantined")

# Write locally to /tmp first (Glue Python Shell has a writable /tmp),
# then upload to S3 — avoids needing a streaming S3 writer for a job
# this size.

local_tmp = "/tmp/legacy_migration_output"
write_csv_local(result["customers"], CUSTOMER_TARGET_FIELDS, os.path.join(local_tmp, "customers.csv"))
write_csv_local(result["orders"], ORDER_TARGET_FIELDS, os.path.join(local_tmp, "orders.csv"))

if result["customers_quarantined"]:
    fields = list(result["customers_quarantined"][0].keys())
    write_csv_local(result["customers_quarantined"], fields, os.path.join(local_tmp, "quarantine", "customers_quarantine.csv"))
if result["orders_quarantined"]:
    fields = list(result["orders_quarantined"][0].keys())
    write_csv_local(result["orders_quarantined"], fields, os.path.join(local_tmp, "quarantine", "orders_quarantine.csv"))

bucket = target_path.replace("s3://", "").split("/")[0]
prefix = "/".join(target_path.replace("s3://", "").split("/")[1:]).rstrip("/")

for fname in ["customers.csv", "orders.csv"]:
    upload_to_s3(os.path.join(local_tmp, fname), bucket, f"{prefix}/{fname}")

print("[glue_job] complete")

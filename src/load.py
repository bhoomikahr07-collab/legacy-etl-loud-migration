"""
Load: writes transformed data to the target location. Locally that's a
plain folder (`data/target/`); for dev/test/prod it uploads to S3 via
boto3. Quarantined rows are written alongside clean data, not discarded,
so the mapping-spec violations documented in
mapping_specs/source_to_target_mapping.md stay visible and fixable.

Usage:
    python src/load.py --env local
"""
import argparse
import csv
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from schema import CUSTOMER_TARGET_FIELDS, ORDER_TARGET_FIELDS
from utils import load_config
from extract import extract
from transform import run_transform


def write_csv_local(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[load] wrote {len(rows)} rows -> {path}")


def upload_to_s3(local_path, bucket, key):
    """Only called for dev/test/prod — requires boto3 and AWS credentials
    (via the Glue job role in production, or the GitHub Actions deploy
    role's credentials when this runs as part of a CI smoke test)."""
    import boto3
    s3 = boto3.client("s3")
    s3.upload_file(local_path, bucket, key)
    print(f"[load] uploaded {local_path} -> s3://{bucket}/{key}")


def main(env):
    cfg = load_config(env)
    customers_raw, orders_raw = extract(cfg["source_path"])
    result = run_transform(customers_raw, orders_raw)

    target_path = cfg["target_path"]

    outputs = [
        (result["customers"], CUSTOMER_TARGET_FIELDS, os.path.join(target_path, "customers.csv")),
        (result["orders"], ORDER_TARGET_FIELDS, os.path.join(target_path, "orders.csv")),
    ]
    for rows, fields, path in outputs:
        write_csv_local(rows, fields, path)

    # Quarantine files keep the original legacy columns plus _reason.
    for rows, name in [
        (result["customers_quarantined"], "customers_quarantine.csv"),
        (result["orders_quarantined"], "orders_quarantine.csv"),
    ]:
        if rows:
            fields = list(rows[0].keys())
            write_csv_local(rows, fields, os.path.join(target_path, "quarantine", name))
        else:
            print(f"[load] no quarantined rows for {name}")

    if env != "local":
        bucket = cfg["s3_bucket"]
        prefix = cfg["s3_prefix"]
        for _, _, path in outputs:
            key = f"{prefix}/{os.path.basename(path)}"
            upload_to_s3(path, bucket, key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["local", "dev", "test", "prod"], default="local")
    args = parser.parse_args()
    main(args.env)

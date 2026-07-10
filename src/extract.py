"""
Extract: reads the legacy-style flat-file extract exactly as the
upstream DBA process produces it — no transformation here, just parsing
the CSV into plain dicts. Keeping extract dumb-and-literal mirrors the
legacy Flat File Source component and makes the transform step (where
all the actual mapping-spec logic lives) independently testable.

Usage:
    python src/extract.py --env local
"""
import argparse
import csv
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import load_config


def read_legacy_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def extract(source_path):
    customers = read_legacy_csv(os.path.join(source_path, "CUST_EXTRACT.csv"))
    orders = read_legacy_csv(os.path.join(source_path, "ORD_EXTRACT.csv"))
    return customers, orders


def main(env):
    cfg = load_config(env)
    customers, orders = extract(cfg["source_path"])
    print(f"[extract] customers: {len(customers)} rows, orders: {len(orders)} rows")
    return customers, orders


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["local", "dev", "test", "prod"], default="local")
    args = parser.parse_args()
    main(args.env)

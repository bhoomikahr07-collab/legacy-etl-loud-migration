"""
Simulates the legacy on-prem SQL Server flat-file extract: legacy column
names, MM/DD/YYYY dates, Y/N flags, currency-formatted amounts, and a
handful of planted issues (blank flag, bad date, unparseable amount, an
orphaned order) for the transform's quarantine logic to catch.

Usage:
    python data/generate_legacy_source.py
"""
import csv
import os
import random
from datetime import date, timedelta

random.seed(11)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")

REGIONS = ["ne", "mw", "so", "we"]
STATUS_CODES = ["O", "S", "C", "X"]

N_CUSTOMERS = 25


def ensure_dir():
    os.makedirs(RAW_DIR, exist_ok=True)


def write_csv(filename, header, rows):
    path = os.path.join(RAW_DIR, filename)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"wrote {len(rows):>6} rows -> {path}")


def random_legacy_date(start: date, end: date) -> str:
    delta_days = (end - start).days
    d = start + timedelta(days=random.randint(0, delta_days))
    return d.strftime("%m/%d/%Y")   # legacy MM/DD/YYYY format


def generate_customers():
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        active_flg = random.choice(["Y", "N"])
        rows.append([
            f"C{10000 + i}",
            f"  Customer {i}  ",   # legacy data with stray whitespace
            active_flg,
            random_legacy_date(date(2022, 1, 1), date(2026, 1, 1)),
            random.choice(REGIONS).upper(),
        ])

    # planted issue: blank ACTIVE_FLG
    rows.append(["C19999", "Edge Case Customer", "", "01/15/2025", "NE"])
    # planted issue: unparseable SIGNUP_DT
    rows.append(["C19998", "Bad Date Customer", "Y", "13/40/2025", "SO"])

    write_csv("CUST_EXTRACT.csv", ["CUST_ID", "CUST_NM", "ACTIVE_FLG", "SIGNUP_DT", "REGION_CD"], rows)
    return [f"C{10000 + i}" for i in range(1, N_CUSTOMERS + 1)]


def generate_orders(customer_ids):
    rows = []
    for i in range(1, 201):
        amount = round(random.uniform(15.0, 850.0), 2)
        rows.append([
            f"O{80000 + i}",
            random.choice(customer_ids),
            random_legacy_date(date(2026, 5, 1), date(2026, 6, 30)),
            f"${amount:,.2f}",
            random.choice(STATUS_CODES),
        ])

    # planted issue: orphaned order (customer doesn't exist in extract)
    rows.append(["O99991", "C99999", "06/01/2026", "$120.00", "O"])
    # planted issue: unparseable amount
    rows.append(["O99992", customer_ids[0], "06/02/2026", "TBD", "O"])
    # planted issue: unmapped status code
    rows.append(["O99993", customer_ids[0], "06/03/2026", "$50.00", "Z"])
    # planted issue: negative amount (refund miscoded as an order)
    rows.append(["O99994", customer_ids[0], "06/04/2026", "-$25.00", "C"])

    write_csv("ORD_EXTRACT.csv", ["ORD_ID", "CUST_ID", "ORD_DT", "ORD_AMT", "STATUS_CD"], rows)


if __name__ == "__main__":
    ensure_dir()
    customer_ids = generate_customers()
    generate_orders(customer_ids)
    print("\nSample legacy extract generated in data/raw/ (includes planted DQ issues)")

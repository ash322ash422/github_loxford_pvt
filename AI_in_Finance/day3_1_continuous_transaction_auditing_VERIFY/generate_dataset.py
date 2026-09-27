"""
generate_dataset.py
--------------------
Builds a synthetic accounts-payable transaction ledger for the
"Continuous Transaction Auditing" workshop demo.

Produces data/transactions.csv with ~6,000 "normal" transactions plus a
known set of embedded anomalies of several types, so the demo script can
show precision/recall style results (we know the ground truth).

Anomaly types embedded (see `is_planted_anomaly` / `anomaly_type` columns,
which the demo script drops before analysis and only reveals at the end):
  1. Duplicate payments        - same vendor/amount/date-ish paid twice
  2. Just-below-threshold      - amounts clustered just under $10,000 approval limit
  3. Weekend / after-hours     - postings at odd times, incl. holidays
  4. Round-dollar amounts      - suspiciously round invoice values
  5. Benford-violating batch   - a vendor with fabricated invoice numbers/amounts
  6. New/shell vendor spike    - a vendor created and immediately paid large sums
  7. Statistical outliers      - amounts far outside a vendor's normal range
"""

import numpy as np
import pandas as pd
from faker import Faker
from datetime import datetime, timedelta
import random

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

N_NORMAL = 6000
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)

DEPARTMENTS = ["Procurement", "Facilities", "IT", "Marketing", "Operations", "HR", "Legal"]
APPROVAL_THRESHOLD = 10000  # amounts >= this require secondary approval

# ---------------------------------------------------------------------
# 1. Build a vendor master (realistic Benford-compliant spend patterns)
# ---------------------------------------------------------------------
N_VENDORS = 140
vendors = []
for i in range(N_VENDORS):
    # Benford-ish: vendor "typical size" drawn log-uniformly so leading
    # digits of resulting invoice amounts approximate Benford's Law.
    typical_size = 10 ** np.random.uniform(2, 5)  # 100 to 100,000
    vendors.append({
        "vendor_id": f"V{1000+i}",
        "vendor_name": fake.company(),
        "typical_amount": typical_size,
        "amount_std": typical_size * 0.35,
        "created_date": fake.date_between(start_date="-6y", end_date="-1y"),
    })
vendor_df = pd.DataFrame(vendors)

def random_business_datetime(start, end, weekend_ok=False):
    delta_days = (end - start).days
    while True:
        d = start + timedelta(days=random.randint(0, delta_days))
        if weekend_ok or d.weekday() < 5:
            hour = int(np.clip(np.random.normal(13, 3), 7, 19))
            minute = random.randint(0, 59)
            return d.replace(hour=hour, minute=minute)

# ---------------------------------------------------------------------
# 2. Generate normal transactions
# ---------------------------------------------------------------------
rows = []
txn_counter = 100000

for _ in range(N_NORMAL):
    v = vendor_df.sample(1, weights=vendor_df["typical_amount"]).iloc[0]
    amount = max(5.0, np.random.lognormal(
        mean=np.log(v["typical_amount"]), sigma=0.5))
    amount = round(amount, 2)
    dt = random_business_datetime(START_DATE, END_DATE)
    txn_counter += 1
    rows.append({
        "transaction_id": f"T{txn_counter}",
        "vendor_id": v["vendor_id"],
        "vendor_name": v["vendor_name"],
        "department": random.choice(DEPARTMENTS),
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": amount,
        "posting_datetime": dt,
        "approved_by": fake.first_name() + " " + fake.last_name()[0] + ".",
        "is_planted_anomaly": False,
        "anomaly_type": "",
    })

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------
# 3. Plant anomalies
# ---------------------------------------------------------------------
anomaly_rows = []

# 3a. Duplicate payments (18 pairs) -----------------------------------
dupe_base = df.sample(18, random_state=1)
for _, r in dupe_base.iterrows():
    txn_counter += 1
    dup = r.copy()
    dup["transaction_id"] = f"T{txn_counter}"
    dup["posting_datetime"] = r["posting_datetime"] + timedelta(days=random.choice([0, 1, 2]))
    dup["is_planted_anomaly"] = True
    dup["anomaly_type"] = "duplicate_payment"
    anomaly_rows.append(dup.to_dict())

# 3b. Just-below-threshold clustering (25 txns, single "Facilities" actor) --
for _ in range(25):
    v = vendor_df.sample(1).iloc[0]
    txn_counter += 1
    amount = round(random.uniform(9700, 9995), 2)
    dt = random_business_datetime(START_DATE, END_DATE)
    anomaly_rows.append({
        "transaction_id": f"T{txn_counter}", "vendor_id": v["vendor_id"],
        "vendor_name": v["vendor_name"], "department": "Facilities",
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": amount, "posting_datetime": dt,
        "approved_by": "Renee K.", "is_planted_anomaly": True,
        "anomaly_type": "just_below_threshold",
    })

# 3c. Weekend / after-hours postings (20 txns) -------------------------
for _ in range(20):
    v = vendor_df.sample(1).iloc[0]
    txn_counter += 1
    amount = round(np.random.lognormal(np.log(v["typical_amount"]), 0.5), 2)
    dt = random_business_datetime(START_DATE, END_DATE, weekend_ok=True)
    # force weekend + odd hour
    while dt.weekday() < 5:
        dt += timedelta(days=1)
    dt = dt.replace(hour=random.choice([1, 2, 3, 23]))
    anomaly_rows.append({
        "transaction_id": f"T{txn_counter}", "vendor_id": v["vendor_id"],
        "vendor_name": v["vendor_name"], "department": random.choice(DEPARTMENTS),
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": amount, "posting_datetime": dt,
        "approved_by": fake.first_name() + " " + fake.last_name()[0] + ".",
        "is_planted_anomaly": True, "anomaly_type": "weekend_after_hours",
    })

# 3d. Suspiciously round amounts (15 txns) ------------------------------
for _ in range(15):
    v = vendor_df.sample(1).iloc[0]
    txn_counter += 1
    amount = float(random.choice([5000, 7500, 10000, 12000, 15000, 20000, 2500, 3000]))
    dt = random_business_datetime(START_DATE, END_DATE)
    anomaly_rows.append({
        "transaction_id": f"T{txn_counter}", "vendor_id": v["vendor_id"],
        "vendor_name": v["vendor_name"], "department": random.choice(DEPARTMENTS),
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": amount, "posting_datetime": dt,
        "approved_by": fake.first_name() + " " + fake.last_name()[0] + ".",
        "is_planted_anomaly": True, "anomaly_type": "round_dollar",
    })

# 3e. Fabricated-invoice vendor (Benford violation, ~40 txns) -----------
fake_vendor = {
    "vendor_id": "V9999", "vendor_name": "Meridian Consulting Partners LLC",
}
for _ in range(40):
    txn_counter += 1
    # fabricated numbers cluster on leading digits 5-9 (violates Benford)
    leading = random.choice([5, 6, 7, 8, 9])
    amount = round(leading * 1000 + random.uniform(0, 999), 2)
    dt = random_business_datetime(START_DATE, END_DATE)
    anomaly_rows.append({
        "transaction_id": f"T{txn_counter}", "vendor_id": fake_vendor["vendor_id"],
        "vendor_name": fake_vendor["vendor_name"], "department": "Operations",
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": amount, "posting_datetime": dt,
        "approved_by": "Marcus T.", "is_planted_anomaly": True,
        "anomaly_type": "fabricated_invoice_benford",
    })

# 3f. New/shell vendor spike (12 txns, vendor created & paid same week) --
shell_created = datetime(2025, 6, 2)
for i in range(12):
    txn_counter += 1
    dt = shell_created + timedelta(days=random.randint(0, 6))
    anomaly_rows.append({
        "transaction_id": f"T{txn_counter}", "vendor_id": "V9998",
        "vendor_name": "Quantum Edge Supply Co.", "department": "IT",
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": round(random.uniform(18000, 45000), 2), "posting_datetime": dt,
        "approved_by": "Marcus T.", "is_planted_anomaly": True,
        "anomaly_type": "shell_vendor_spike",
    })

# 3g. Statistical outliers relative to vendor norm (15 txns) ------------
outlier_vendors = vendor_df.sample(15, random_state=2)
for _, v in outlier_vendors.iterrows():
    txn_counter += 1
    amount = round(v["typical_amount"] * random.uniform(8, 15), 2)
    dt = random_business_datetime(START_DATE, END_DATE)
    anomaly_rows.append({
        "transaction_id": f"T{txn_counter}", "vendor_id": v["vendor_id"],
        "vendor_name": v["vendor_name"], "department": random.choice(DEPARTMENTS),
        "invoice_number": f"INV-{random.randint(10000,99999)}",
        "amount": amount, "posting_datetime": dt,
        "approved_by": fake.first_name() + " " + fake.last_name()[0] + ".",
        "is_planted_anomaly": True, "anomaly_type": "statistical_outlier",
    })

anomaly_df = pd.DataFrame(anomaly_rows)
full_df = pd.concat([df, anomaly_df], ignore_index=True)
full_df = full_df.sort_values("posting_datetime").reset_index(drop=True)
full_df["amount"] = full_df["amount"].round(2)

import os
os.makedirs("/tmp/cta_workshop/data", exist_ok=True)
full_df.to_csv("/tmp/cta_workshop/data/transactions.csv", index=False)

print(f"Total transactions: {len(full_df)}")
print(f"Planted anomalies:  {full_df['is_planted_anomaly'].sum()}")
print(full_df["anomaly_type"].value_counts())

"""
seed_db.py — Creates and populates a sample bank lending SQLite database.
Run once before launching the app:  python database/seed_db.py
"""

import sqlite3
import random
from datetime import date, timedelta

DB_PATH = "database/lending.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id     INTEGER PRIMARY KEY,
    name            TEXT,
    age             INTEGER,
    city            TEXT,
    credit_score    INTEGER,
    annual_income   REAL
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id         INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    loan_type       TEXT,          -- Personal, Home, Auto, Business
    amount          REAL,
    interest_rate   REAL,
    tenure_months   INTEGER,
    issue_date      TEXT,
    status          TEXT,          -- Active, Closed, Defaulted
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS repayments (
    repayment_id    INTEGER PRIMARY KEY,
    loan_id         INTEGER,
    payment_date    TEXT,
    amount_paid     REAL,
    on_time         INTEGER,       -- 1 = Yes, 0 = No
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
);
"""

CITIES   = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata"]
LOAN_TYPES = ["Personal", "Home", "Auto", "Business"]
STATUSES   = ["Active", "Closed", "Defaulted"]

random.seed(42)

def random_date(start_year=2020, end_year=2024):
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.executescript(SCHEMA)

    # Customers
    customers = []
    for i in range(1, 201):
        customers.append((
            i,
            f"Customer_{i}",
            random.randint(22, 65),
            random.choice(CITIES),
            random.randint(550, 850),
            round(random.uniform(300_000, 2_000_000), 2),
        ))
    cur.executemany(
        "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?)", customers
    )

    # Loans
    loans = []
    for loan_id in range(1, 501):
        cid    = random.randint(1, 200)
        ltype  = random.choice(LOAN_TYPES)
        amount = round(random.uniform(50_000, 5_000_000), 2)
        rate   = round(random.uniform(7.5, 18.0), 2)
        tenure = random.choice([12, 24, 36, 48, 60, 84, 120])
        idate  = str(random_date())
        status = random.choices(STATUSES, weights=[0.55, 0.35, 0.10])[0]
        loans.append((loan_id, cid, ltype, amount, rate, tenure, idate, status))
    cur.executemany(
        "INSERT OR IGNORE INTO loans VALUES (?,?,?,?,?,?,?,?)", loans
    )

    # Repayments
    repayments = []
    rid = 1
    for loan_id, _, _, amount, _, tenure, idate, status in loans:
        payments = random.randint(1, min(tenure, 24))
        for _ in range(payments):
            pdate    = str(random_date(2020, 2024))
            paid     = round(amount / tenure * random.uniform(0.9, 1.1), 2)
            on_time  = 1 if random.random() > 0.15 else 0
            repayments.append((rid, loan_id, pdate, paid, on_time))
            rid += 1
    cur.executemany(
        "INSERT OR IGNORE INTO repayments VALUES (?,?,?,?,?)", repayments
    )

    conn.commit()
    conn.close()
    print(f"✅ Database seeded at {DB_PATH}")
    print(f"   Customers : 200")
    print(f"   Loans     : 500")
    print(f"   Repayments: {len(repayments)}")

if __name__ == "__main__":
    seed()

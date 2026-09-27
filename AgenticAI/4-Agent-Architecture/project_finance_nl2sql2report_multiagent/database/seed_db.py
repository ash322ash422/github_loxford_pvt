"""
database/seed_db.py
Run once to create and populate the Finance SQLite database.
    python database/seed_db.py
"""

import sqlite3, random
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent / "finance.db"
random.seed(42)

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY,
    name          TEXT,
    age           INTEGER,
    city          TEXT,
    credit_score  INTEGER,
    annual_income REAL
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id       INTEGER PRIMARY KEY,
    customer_id   INTEGER,
    loan_type     TEXT,
    amount        REAL,
    interest_rate REAL,
    tenure_months INTEGER,
    issue_date    TEXT,
    status        TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS repayments (
    repayment_id INTEGER PRIMARY KEY,
    loan_id      INTEGER,
    payment_date TEXT,
    amount_paid  REAL,
    on_time      INTEGER,
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id       INTEGER PRIMARY KEY,
    customer_id  INTEGER,
    txn_date     TEXT,
    txn_type     TEXT,
    category     TEXT,
    amount       REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
"""

CITIES     = ["Mumbai","Delhi","Bangalore","Chennai","Hyderabad","Pune","Kolkata"]
LOAN_TYPES = ["Personal","Home","Auto","Business"]
STATUSES   = ["Active","Closed","Defaulted"]
TXN_TYPES  = ["Credit","Debit"]
CATEGORIES = ["Salary","EMI","Grocery","Utilities","Investment","Medical","Travel","Shopping"]

def rdate(y0=2020, y1=2024):
    s = date(y0,1,1); e = date(y1,12,31)
    return str(s + timedelta(days=random.randint(0,(e-s).days)))

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
cur.executescript(SCHEMA)

customers = [(i, f"Customer_{i}", random.randint(22,65), random.choice(CITIES),
              random.randint(550,850), round(random.uniform(3e5,2e6),2))
             for i in range(1,201)]
cur.executemany("INSERT OR IGNORE INTO customers VALUES(?,?,?,?,?,?)", customers)

loans = [(lid, random.randint(1,200), random.choice(LOAN_TYPES),
          round(random.uniform(5e4,5e6),2), round(random.uniform(7.5,18.0),2),
          random.choice([12,24,36,48,60,84,120]), rdate(),
          random.choices(STATUSES, weights=[.55,.35,.10])[0])
         for lid in range(1,501)]
cur.executemany("INSERT OR IGNORE INTO loans VALUES(?,?,?,?,?,?,?,?)", loans)

reps=[]; rid=1
for lid,_,_,amt,_,ten,_,_ in loans:
    for _ in range(random.randint(1,min(ten,24))):
        reps.append((rid,lid,rdate(),round(amt/ten*random.uniform(.9,1.1),2),
                     1 if random.random()>0.15 else 0)); rid+=1
cur.executemany("INSERT OR IGNORE INTO repayments VALUES(?,?,?,?,?)", reps)

txns=[]
for tid in range(1,2001):
    cid  = random.randint(1,200)
    ttyp = random.choice(TXN_TYPES)
    cat  = random.choice(CATEGORIES)
    amt  = round(random.uniform(500,200000),2)
    txns.append((tid,cid,rdate(),ttyp,cat,amt))
cur.executemany("INSERT OR IGNORE INTO transactions VALUES(?,?,?,?,?,?)", txns)

conn.commit(); conn.close()
print(f"✅  Finance DB seeded → {DB_PATH}")
print(f"   customers={len(customers)}  loans={len(loans)}  repayments={len(reps)}  transactions={len(txns)}")

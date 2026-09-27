"""
database/seed_db.py
Creates and populates the fraud detection SQLite database.
Run once:  python database/seed_db.py
"""

import sqlite3, random
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "fraud.db"
random.seed(42)

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id      TEXT PRIMARY KEY,
    name             TEXT,
    email            TEXT,
    country          TEXT,
    account_age_days INTEGER,
    avg_txn_amount   REAL,
    total_txns       INTEGER,
    is_vip           INTEGER
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id           TEXT PRIMARY KEY,
    customer_id      TEXT,
    amount           REAL,
    currency         TEXT,
    merchant         TEXT,
    merchant_country TEXT,
    txn_datetime     TEXT,
    channel          TEXT,
    is_fraud         INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS blacklist (
    entry_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT,
    value      TEXT,
    reason     TEXT,
    added_date TEXT
);
"""

COUNTRIES  = ["US","GB","IN","SG","DE","FR","AU","CA","NG","RU"]
MERCHANTS  = ["Amazon","Walmart","Steam","Uber","Netflix","Unknown_Vendor","ShadyShop","FastCash"]
CHANNELS   = ["web","mobile","pos","api"]
CURRENCIES = ["USD","GBP","EUR","INR","SGD"]

def rdt(days_back=365):
    base = datetime.now() - timedelta(days=random.randint(0, days_back))
    return base.strftime("%Y-%m-%d %H:%M:%S")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
cur.executescript(SCHEMA)

customers = []
for i in range(1, 301):
    cid = f"CUST_{i:04d}"
    customers.append((
        cid, f"Customer {i}", f"user{i}@email.com",
        random.choice(COUNTRIES),
        random.randint(30, 3000),
        round(random.uniform(20, 2000), 2),
        random.randint(5, 500),
        1 if random.random() < 0.1 else 0,
    ))
cur.executemany("INSERT OR IGNORE INTO customers VALUES(?,?,?,?,?,?,?,?)", customers)

transactions = []
for i in range(1, 2001):
    cid      = f"CUST_{random.randint(1,300):04d}"
    is_fraud = 1 if random.random() < 0.06 else 0
    amount   = round(random.uniform(500, 15000) if is_fraud else random.uniform(5, 800), 2)
    transactions.append((
        f"TXN_{i:05d}", cid, amount,
        random.choice(CURRENCIES),
        random.choice(MERCHANTS),
        random.choice(COUNTRIES),
        rdt(), random.choice(CHANNELS), is_fraud,
    ))
cur.executemany("INSERT OR IGNORE INTO transactions VALUES(?,?,?,?,?,?,?,?,?)", transactions)

blacklist = [
    ("email",    "fraud123@scam.com",    "Known fraudster",          "2023-01-10"),
    ("email",    "stolen@hacker.net",    "Account takeover",         "2023-03-15"),
    ("merchant", "ShadyShop",            "Chargeback rate >40%",     "2023-06-01"),
    ("merchant", "FastCash",             "Money laundering suspect", "2024-01-20"),
    ("ip",       "192.168.99.1",         "TOR exit node",            "2023-09-05"),
    ("ip",       "10.0.0.255",           "Flagged proxy",            "2024-02-11"),
    ("card",     "4111111111111111",      "Reported stolen",          "2023-11-30"),
    ("card",     "5500000000000004",      "Cloned card",              "2024-03-01"),
]
cur.executemany(
    "INSERT OR IGNORE INTO blacklist(entry_type,value,reason,added_date) VALUES(?,?,?,?)",
    blacklist,
)

conn.commit()
conn.close()
print(f"✅  Fraud DB seeded → {DB_PATH}")
print(f"   customers={len(customers)}  transactions={len(transactions)}  blacklist={len(blacklist)}")

"""
Build the sample retail dataset used throughout the Data Modeling workshop.
Scenario: "BrightMart" - a small electronics retail chain.
Produces CSVs for dimension tables and a fact table, at grain:
    one row per (product, store, date, transaction line)
"""
import pandas as pd
import os

OUT = "/tmp/dm_workshop/data"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------
# DIM_DATE
# ---------------------------------------------------------------
dim_date = pd.DataFrame([
    {"date_key": 20260601, "full_date": "2026-06-01", "day_name": "Monday",    "month": 6, "month_name": "June", "quarter": "Q2", "year": 2026, "is_weekend": False},
    {"date_key": 20260602, "full_date": "2026-06-02", "day_name": "Tuesday",   "month": 6, "month_name": "June", "quarter": "Q2", "year": 2026, "is_weekend": False},
    {"date_key": 20260606, "full_date": "2026-06-06", "day_name": "Saturday",  "month": 6, "month_name": "June", "quarter": "Q2", "year": 2026, "is_weekend": True},
    {"date_key": 20260615, "full_date": "2026-06-15", "day_name": "Monday",    "month": 6, "month_name": "June", "quarter": "Q2", "year": 2026, "is_weekend": False},
    {"date_key": 20260701, "full_date": "2026-07-01", "day_name": "Wednesday", "month": 7, "month_name": "July", "quarter": "Q3", "year": 2026, "is_weekend": False},
])
dim_date.to_csv(f"{OUT}/dim_date.csv", index=False)

# ---------------------------------------------------------------
# DIM_STORE  (used for STAR schema: flattened city/region/country)
# ---------------------------------------------------------------
dim_store_star = pd.DataFrame([
    {"store_key": 1, "store_id": "ST-101", "store_name": "BrightMart Andheri",  "city": "Mumbai",     "region": "West",  "country": "India"},
    {"store_key": 2, "store_id": "ST-102", "store_name": "BrightMart Koramangala","city": "Bengaluru", "region": "South", "country": "India"},
    {"store_key": 3, "store_id": "ST-103", "store_name": "BrightMart Salt Lake", "city": "Kolkata",    "region": "East",  "country": "India"},
])
dim_store_star.to_csv(f"{OUT}/dim_store_star.csv", index=False)

# ---------------------------------------------------------------
# SNOWFLAKE version: store normalized into Store -> City -> Region -> Country
# ---------------------------------------------------------------
dim_store_snow = pd.DataFrame([
    {"store_key": 1, "store_id": "ST-101", "store_name": "BrightMart Andheri",   "city_key": 10},
    {"store_key": 2, "store_id": "ST-102", "store_name": "BrightMart Koramangala","city_key": 20},
    {"store_key": 3, "store_id": "ST-103", "store_name": "BrightMart Salt Lake",  "city_key": 30},
])
dim_city = pd.DataFrame([
    {"city_key": 10, "city_name": "Mumbai",    "region_key": 100},
    {"city_key": 20, "city_name": "Bengaluru", "region_key": 200},
    {"city_key": 30, "city_name": "Kolkata",   "region_key": 300},
])
dim_region = pd.DataFrame([
    {"region_key": 100, "region_name": "West",  "country_key": 1000},
    {"region_key": 200, "region_name": "South", "country_key": 1000},
    {"region_key": 300, "region_name": "East",  "country_key": 1000},
])
dim_country = pd.DataFrame([
    {"country_key": 1000, "country_name": "India"},
])
dim_store_snow.to_csv(f"{OUT}/dim_store_snow.csv", index=False)
dim_city.to_csv(f"{OUT}/dim_city.csv", index=False)
dim_region.to_csv(f"{OUT}/dim_region.csv", index=False)
dim_country.to_csv(f"{OUT}/dim_country.csv", index=False)

# ---------------------------------------------------------------
# DIM_PRODUCT (star: category/subcategory flattened in)
# ---------------------------------------------------------------
dim_product_star = pd.DataFrame([
    {"product_key": 1, "sku": "SKU-5001", "product_name": "AeroBuds Pro",      "category": "Electronics", "subcategory": "Audio",       "brand": "Aero"},
    {"product_key": 2, "sku": "SKU-5002", "product_name": "AeroBuds Pro",      "category": "Electronics", "subcategory": "Audio",       "brand": "Aero"},  # note: created later as v2 (SCD2 illustration)
    {"product_key": 3, "sku": "SKU-6010", "product_name": "VoltCharge 65W",    "category": "Electronics", "subcategory": "Power",       "brand": "Volt"},
    {"product_key": 4, "sku": "SKU-7020", "product_name": "PixelView 24 Monitor","category": "Electronics","subcategory": "Computing",  "brand": "Pixel"},
])
dim_product_star.to_csv(f"{OUT}/dim_product_star.csv", index=False)

dim_product_snow = pd.DataFrame([
    {"product_key": 1, "sku": "SKU-5001", "product_name": "AeroBuds Pro",        "subcat_key": 900},
    {"product_key": 3, "sku": "SKU-6010", "product_name": "VoltCharge 65W",      "subcat_key": 901},
    {"product_key": 4, "sku": "SKU-7020", "product_name": "PixelView 24 Monitor","subcat_key": 902},
])
dim_subcategory = pd.DataFrame([
    {"subcat_key": 900, "subcategory_name": "Audio",     "category_key": 90},
    {"subcat_key": 901, "subcategory_name": "Power",     "category_key": 90},
    {"subcat_key": 902, "subcategory_name": "Computing", "category_key": 90},
])
dim_category = pd.DataFrame([
    {"category_key": 90, "category_name": "Electronics"},
])
dim_product_snow.to_csv(f"{OUT}/dim_product_snow.csv", index=False)
dim_subcategory.to_csv(f"{OUT}/dim_subcategory.csv", index=False)
dim_category.to_csv(f"{OUT}/dim_category.csv", index=False)

# ---------------------------------------------------------------
# DIM_CUSTOMER (Type 1/2/3 SCD illustration lives here)
# ---------------------------------------------------------------
dim_customer_current = pd.DataFrame([
    {"customer_key": 501, "customer_id": "CUST-01", "customer_name": "Ritu Sharma", "city": "Mumbai",  "loyalty_tier": "Gold"},
    {"customer_key": 502, "customer_id": "CUST-02", "customer_name": "Arjun Mehta", "city": "Pune",    "loyalty_tier": "Silver"},
])
dim_customer_current.to_csv(f"{OUT}/dim_customer_current.csv", index=False)

# ---------------------------------------------------------------
# FACT_SALES  (grain: one row per product sold, per store, per transaction line)
# ---------------------------------------------------------------
fact_sales = pd.DataFrame([
    {"sales_key": 1, "date_key": 20260601, "store_key": 1, "product_key": 1, "customer_key": 501, "transaction_id": "TXN-9001", "quantity": 2, "unit_price": 2499, "sales_amount": 4998},
    {"sales_key": 2, "date_key": 20260601, "store_key": 1, "product_key": 3, "customer_key": 501, "transaction_id": "TXN-9001", "quantity": 1, "unit_price": 1299, "sales_amount": 1299},
    {"sales_key": 3, "date_key": 20260602, "store_key": 2, "product_key": 4, "customer_key": 502, "transaction_id": "TXN-9002", "quantity": 1, "unit_price": 13999,"sales_amount": 13999},
    {"sales_key": 4, "date_key": 20260606, "store_key": 3, "product_key": 1, "customer_key": 502, "transaction_id": "TXN-9003", "quantity": 3, "unit_price": 2499, "sales_amount": 7497},
    {"sales_key": 5, "date_key": 20260615, "store_key": 1, "product_key": 2, "customer_key": 501, "transaction_id": "TXN-9004", "quantity": 1, "unit_price": 2799, "sales_amount": 2799},
    {"sales_key": 6, "date_key": 20260701, "store_key": 2, "product_key": 3, "customer_key": 502, "transaction_id": "TXN-9005", "quantity": 2, "unit_price": 1299, "sales_amount": 2598},
])
fact_sales.to_csv(f"{OUT}/fact_sales.csv", index=False)

print("All CSVs written to", OUT)
for f in sorted(os.listdir(OUT)):
    print(" -", f)

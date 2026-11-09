"""
Data Cleaning Pipeline
----------------------
Reads raw CSVs from data/raw/, profiles and cleans them, then writes:
- Clean CSVs to data/processed/
- A SQLite database at data/processed/ecommerce.db for SQL analysis (Phase 2)
"""

import pandas as pd
import numpy as np
import sqlite3
import os

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
os.makedirs(PROCESSED_DIR, exist_ok=True)

pd.set_option("display.width", 120)

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
print("Loading raw data...")
customers = pd.read_csv(f"{RAW_DIR}/customers.csv", parse_dates=["acquisition_date"])
orders = pd.read_csv(f"{RAW_DIR}/orders.csv", parse_dates=["order_date"])
order_items = pd.read_csv(f"{RAW_DIR}/order_items.csv")
products = pd.read_csv(f"{RAW_DIR}/products.csv")

# ---------------------------------------------------------------------------
# Profile BEFORE cleaning
# ---------------------------------------------------------------------------
print("\n=== BEFORE CLEANING ===")
print(f"customers: {len(customers):,} rows | nulls:\n{customers.isnull().sum()}\n")
print(f"orders: {len(orders):,} rows | duplicates: {orders.duplicated().sum()} | nulls:\n{orders.isnull().sum()}\n")
print(f"order_items: {len(order_items):,} rows | negative qty rows: {(order_items['quantity'] < 0).sum()}")
print(f"order_items category values: {sorted(order_items['category'].unique())}\n")

# ---------------------------------------------------------------------------
# Clean: customers
# ---------------------------------------------------------------------------
print("Cleaning customers...")
customers["region"] = customers["region"].fillna("Unknown")
customers = customers.drop_duplicates(subset=["customer_id"])

# ---------------------------------------------------------------------------
# Clean: orders
# ---------------------------------------------------------------------------
print("Cleaning orders...")
before = len(orders)
orders = orders.drop_duplicates(subset=["order_id"])
print(f"  Removed {before - len(orders)} duplicate order rows")

orders["sales_channel"] = orders["sales_channel"].fillna("Unknown")

# ---------------------------------------------------------------------------
# Clean: order_items
# ---------------------------------------------------------------------------
print("Cleaning order_items...")

order_items["category"] = order_items["category"].str.strip().str.title()

neg_count = (order_items["quantity"] < 0).sum()
order_items["quantity"] = order_items["quantity"].abs()
print(f"  Fixed {neg_count} negative-quantity rows")

order_items["line_revenue"] = (order_items["quantity"] * order_items["unit_price"]).round(2)

before = len(order_items)
order_items = order_items[order_items["order_id"].isin(orders["order_id"])]
print(f"  Dropped {before - len(order_items)} orphaned order_item rows")

# ---------------------------------------------------------------------------
# Referential integrity checks
# ---------------------------------------------------------------------------
print("\nChecking referential integrity...")
orphan_orders = orders[~orders["customer_id"].isin(customers["customer_id"])]
print(f"  Orders with unknown customer_id: {len(orphan_orders)}")
orphan_items = order_items[~order_items["product_id"].isin(products["product_id"])]
print(f"  Order items with unknown product_id: {len(orphan_items)}")

# ---------------------------------------------------------------------------
# Profile AFTER cleaning
# ---------------------------------------------------------------------------
print("\n=== AFTER CLEANING ===")
print(f"customers: {len(customers):,} rows | nulls: {customers.isnull().sum().sum()}")
print(f"orders: {len(orders):,} rows | duplicates: {orders.duplicated().sum()} | nulls: {orders.isnull().sum().sum()}")
print(f"order_items: {len(order_items):,} rows | negative qty rows: {(order_items['quantity'] < 0).sum()}")
print(f"order_items category values: {sorted(order_items['category'].unique())}")

# ---------------------------------------------------------------------------
# Save clean CSVs
# ---------------------------------------------------------------------------
print("\nSaving cleaned CSVs...")
customers.to_csv(f"{PROCESSED_DIR}/customers_clean.csv", index=False)
orders.to_csv(f"{PROCESSED_DIR}/orders_clean.csv", index=False)
order_items.to_csv(f"{PROCESSED_DIR}/order_items_clean.csv", index=False)
products.to_csv(f"{PROCESSED_DIR}/products_clean.csv", index=False)

# ---------------------------------------------------------------------------
# Load into SQLite for Phase 2 SQL analysis
# ---------------------------------------------------------------------------
print("Loading into SQLite database...")
db_path = f"{PROCESSED_DIR}/ecommerce.db"
conn = sqlite3.connect(db_path)

customers.to_sql("customers", conn, if_exists="replace", index=False)
orders.to_sql("orders", conn, if_exists="replace", index=False)
order_items.to_sql("order_items", conn, if_exists="replace", index=False)
products.to_sql("products", conn, if_exists="replace", index=False)

cur = conn.cursor()
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id)")
conn.commit()
conn.close()

print(f"\nDone. SQLite DB written to {db_path}")
print("Tables: customers, orders, order_items, products")
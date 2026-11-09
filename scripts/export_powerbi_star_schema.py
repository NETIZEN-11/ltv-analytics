"""
Power BI Star Schema Export
-----------------------------
Builds a clean star schema for Power BI import:

  FACT:
    fact_order_items  -- one row per order line item, with keys to dimensions

  DIMENSIONS:
    dim_customers   -- customer_id, acquisition info, region, channel
    dim_products    -- product_id, category
    dim_date        -- full date dimension table (for time intelligence DAX)

Also merges in customer_ltv.csv / rfm_segments.csv fields onto dim_customers
so Power BI can slice by segment without extra joins.

Output: powerbi/*.csv  (import these directly into Power BI Desktop)
"""

import pandas as pd
import sqlite3
import os

DB_PATH = "data/processed/ecommerce.db"
PROCESSED_DIR = "data/processed"
PBI_DIR = "powerbi"
os.makedirs(PBI_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
customers = pd.read_sql_query("SELECT * FROM customers", conn, parse_dates=["acquisition_date"])
orders = pd.read_sql_query("SELECT * FROM orders", conn, parse_dates=["order_date"])
order_items = pd.read_sql_query("SELECT * FROM order_items", conn)
products = pd.read_sql_query("SELECT * FROM products", conn)
conn.close()

customer_ltv = pd.read_csv(f"{PROCESSED_DIR}/customer_ltv.csv")

# ---------------------------------------------------------------------------
# FACT TABLE: one row per order line item
# ---------------------------------------------------------------------------
print("Building fact_order_items...")

fact = order_items.merge(orders[["order_id", "customer_id", "order_date", "sales_channel"]],
                          on="order_id", how="left")

fact = fact[[
    "order_item_id", "order_id", "customer_id", "product_id",
    "order_date", "sales_channel", "category", "quantity",
    "unit_price", "line_revenue", "is_returned"
]]

fact.to_csv(f"{PBI_DIR}/fact_order_items.csv", index=False)
print(f"  {len(fact):,} rows -> {PBI_DIR}/fact_order_items.csv")

# ---------------------------------------------------------------------------
# DIM: customers (enriched with segment + LTV fields)
# ---------------------------------------------------------------------------
print("Building dim_customers...")

dim_customers = customers.merge(
    customer_ltv[["customer_id", "historical_ltv", "total_orders", "segment",
                  "recency_days", "frequency", "monetary", "RFM_score"]],
    on="customer_id", how="left"
)

dim_customers["historical_ltv"] = dim_customers["historical_ltv"].fillna(0)
dim_customers["total_orders"] = dim_customers["total_orders"].fillna(0)
dim_customers["segment"] = dim_customers["segment"].fillna("No Purchases")

dim_customers.to_csv(f"{PBI_DIR}/dim_customers.csv", index=False)
print(f"  {len(dim_customers):,} rows -> {PBI_DIR}/dim_customers.csv")

# ---------------------------------------------------------------------------
# DIM: products
# ---------------------------------------------------------------------------
print("Building dim_products...")
products.to_csv(f"{PBI_DIR}/dim_products.csv", index=False)
print(f"  {len(products):,} rows -> {PBI_DIR}/dim_products.csv")

# ---------------------------------------------------------------------------
# DIM: date (full calendar table for DAX time intelligence)
# ---------------------------------------------------------------------------
print("Building dim_date...")

min_date = fact["order_date"].min()
max_date = fact["order_date"].max()
date_range = pd.date_range(min_date, max_date, freq="D")

dim_date = pd.DataFrame({"date": date_range})
dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
dim_date["year"] = dim_date["date"].dt.year
dim_date["month"] = dim_date["date"].dt.month
dim_date["month_name"] = dim_date["date"].dt.strftime("%b")
dim_date["month_year"] = dim_date["date"].dt.strftime("%Y-%m")
dim_date["quarter"] = "Q" + dim_date["date"].dt.quarter.astype(str)
dim_date["year_quarter"] = dim_date["year"].astype(str) + "-" + dim_date["quarter"]
dim_date["day_of_week"] = dim_date["date"].dt.day_name()
dim_date["is_weekend"] = dim_date["date"].dt.dayofweek >= 5

dim_date.to_csv(f"{PBI_DIR}/dim_date.csv", index=False)
print(f"  {len(dim_date):,} rows -> {PBI_DIR}/dim_date.csv")

# add a date_key to the fact table too, to join cleanly on an integer key
fact_dated = order_items.merge(orders[["order_id", "customer_id", "order_date", "sales_channel"]],
                                on="order_id", how="left")
fact_dated["date_key"] = pd.to_datetime(fact_dated["order_date"]).dt.strftime("%Y%m%d").astype(int)
fact_dated = fact_dated[[
    "order_item_id", "order_id", "customer_id", "product_id", "date_key",
    "sales_channel", "category", "quantity", "unit_price", "line_revenue", "is_returned"
]]
fact_dated.to_csv(f"{PBI_DIR}/fact_order_items.csv", index=False)

print("\nAll Power BI import files ready in powerbi/")
print("  fact_order_items.csv  (fact table, join to dim_date via date_key)")
print("  dim_customers.csv")
print("  dim_products.csv")
print("  dim_date.csv")
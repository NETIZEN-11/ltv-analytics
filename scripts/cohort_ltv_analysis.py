"""
Cohort Analysis & LTV Modeling
-------------------------------
1. Builds a monthly cohort retention matrix (acquisition month x months since acquisition)
2. Computes historical (observed) LTV per customer
3. Computes a segment-level LTV projection: AOV x Purchase Frequency x Avg Lifespan
4. Performs RFM (Recency, Frequency, Monetary) segmentation to isolate high-value buyers

Outputs (all to data/processed/):
- cohort_retention_matrix.csv
- cohort_retention_pct.csv
- customer_ltv.csv
- rfm_segments.csv
- ltv_by_segment_channel.csv
"""

import pandas as pd
import numpy as np
import sqlite3

pd.set_option("display.width", 140)
pd.set_option("display.max_columns", 20)

DB_PATH = "data/processed/ecommerce.db"
OUT_DIR = "data/processed"

conn = sqlite3.connect(DB_PATH)
customers = pd.read_sql_query("SELECT * FROM customers", conn, parse_dates=["acquisition_date"])
orders = pd.read_sql_query("SELECT * FROM orders", conn, parse_dates=["order_date"])
order_items = pd.read_sql_query("SELECT * FROM order_items", conn)
conn.close()

order_items_net = order_items[order_items["is_returned"] == 0]
order_revenue = order_items_net.groupby("order_id")["line_revenue"].sum().reset_index()
order_revenue.columns = ["order_id", "order_revenue"]

orders_full = orders.merge(order_revenue, on="order_id", how="left")
orders_full["order_revenue"] = orders_full["order_revenue"].fillna(0)
orders_full = orders_full.merge(customers, on="customer_id", how="left")

# ---------------------------------------------------------------------------
# 1. COHORT RETENTION MATRIX
# Cohort is defined by each customer's FIRST ORDER month (standard cohort
# methodology) rather than the acquisition_date field, since a customer's
# actual first purchase can land a few days into the following month.
# ---------------------------------------------------------------------------
print("Building cohort retention matrix...")

orders_full["order_month"] = orders_full["order_date"].dt.to_period("M")

first_order_month = orders_full.groupby("customer_id")["order_month"].min()
orders_full["cohort_month"] = orders_full["customer_id"].map(first_order_month)

orders_full["cohort_index"] = (
    (orders_full["order_month"].dt.year - orders_full["cohort_month"].dt.year) * 12
    + (orders_full["order_month"].dt.month - orders_full["cohort_month"].dt.month)
)

cohort_data = (
    orders_full.groupby(["cohort_month", "cohort_index"])["customer_id"]
    .nunique()
    .reset_index()
)

cohort_counts = cohort_data.pivot(index="cohort_month", columns="cohort_index", values="customer_id")
cohort_sizes = cohort_counts[0]
retention_pct = cohort_counts.divide(cohort_sizes, axis=0).round(4) * 100

cohort_counts.to_csv(f"{OUT_DIR}/cohort_retention_matrix.csv")
retention_pct.to_csv(f"{OUT_DIR}/cohort_retention_pct.csv")

print("Sample retention % (first 6 cohorts, first 6 months):")
print(retention_pct.iloc[:6, :6].round(1))

# ---------------------------------------------------------------------------
# 2. HISTORICAL LTV PER CUSTOMER
# ---------------------------------------------------------------------------
print("\nComputing historical LTV per customer...")

customer_ltv = orders_full.groupby("customer_id").agg(
    total_orders=("order_id", "nunique"),
    historical_ltv=("order_revenue", "sum"),
    first_order_date=("order_date", "min"),
    last_order_date=("order_date", "max"),
    acquisition_channel=("acquisition_channel", "first"),
    region=("region", "first"),
).reset_index()

customer_ltv["customer_lifespan_days"] = (
    customer_ltv["last_order_date"] - customer_ltv["first_order_date"]
).dt.days
customer_ltv["avg_order_value"] = (
    customer_ltv["historical_ltv"] / customer_ltv["total_orders"]
).round(2)

# ---------------------------------------------------------------------------
# 3. RFM SEGMENTATION (Recency, Frequency, Monetary)
# ---------------------------------------------------------------------------
print("Computing RFM segments...")

analysis_date = orders_full["order_date"].max() + pd.Timedelta(days=1)

rfm = orders_full.groupby("customer_id").agg(
    recency_days=("order_date", lambda x: (analysis_date - x.max()).days),
    frequency=("order_id", "nunique"),
    monetary=("order_revenue", "sum"),
).reset_index()

rfm["R_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M_score"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)

rfm["RFM_score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

def segment_customer(row):
    if row["RFM_score"] >= 13:
        return "High-Value / Champion"
    elif row["RFM_score"] >= 10:
        return "Loyal / Growing"
    elif row["RFM_score"] >= 7:
        return "At Risk"
    else:
        return "Low-Value / Churned"

rfm["segment"] = rfm.apply(segment_customer, axis=1)

print("\nCustomer segment distribution:")
print(rfm["segment"].value_counts())

customer_ltv = customer_ltv.merge(rfm[["customer_id", "recency_days", "frequency", "monetary",
                                        "RFM_score", "segment"]], on="customer_id", how="left")

customer_ltv.to_csv(f"{OUT_DIR}/customer_ltv.csv", index=False)
rfm.to_csv(f"{OUT_DIR}/rfm_segments.csv", index=False)

# ---------------------------------------------------------------------------
# 4. SEGMENT-LEVEL PREDICTIVE LTV
#    LTV = Avg Order Value x Purchase Frequency (orders/month) x Avg Lifespan (months)
# ---------------------------------------------------------------------------
print("\nComputing predictive LTV by segment and acquisition channel...")

customer_ltv["lifespan_months"] = (customer_ltv["customer_lifespan_days"] / 30).clip(lower=1)
customer_ltv["purchase_freq_per_month"] = customer_ltv["total_orders"] / customer_ltv["lifespan_months"]

segment_stats = customer_ltv.groupby(["segment", "acquisition_channel"]).agg(
    avg_order_value=("avg_order_value", "mean"),
    avg_purchase_freq_per_month=("purchase_freq_per_month", "mean"),
    avg_lifespan_months=("lifespan_months", "mean"),
    customer_count=("customer_id", "count"),
    avg_historical_ltv=("historical_ltv", "mean"),
).reset_index()

segment_stats["predicted_ltv"] = (
    segment_stats["avg_order_value"]
    * segment_stats["avg_purchase_freq_per_month"]
    * segment_stats["avg_lifespan_months"]
).round(2)

segment_stats = segment_stats.round(2).sort_values("predicted_ltv", ascending=False)
segment_stats.to_csv(f"{OUT_DIR}/ltv_by_segment_channel.csv", index=False)

print("\nTop segment/channel combos by predicted LTV:")
print(segment_stats.head(10).to_string(index=False))

print("\nAll outputs saved to data/processed/")
print("  - cohort_retention_matrix.csv")
print("  - cohort_retention_pct.csv")
print("  - customer_ltv.csv")
print("  - rfm_segments.csv")
print("  - ltv_by_segment_channel.csv")
"""
Synthetic E-Commerce Data Generator
------------------------------------
Generates a realistic multi-year e-commerce transactional dataset with:
- Customers acquired over time via different channels
- Channel/value-tier-dependent retention behavior (so cohort analysis finds real signal)
- Seasonality (holiday spikes)
- Regional + product category mix
- Returns/refunds
- 200,000+ order line items

Output: data/raw/customers.csv, data/raw/orders.csv, data/raw/order_items.csv, data/raw/products.csv
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
import random

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
START_DATE = date(2022, 1, 1)
END_DATE = date(2024, 12, 31)
N_CUSTOMERS = 26000
TARGET_ORDER_ITEMS = 220_000

REGIONS = ["Northeast", "Midwest", "South", "West", "International"]
REGION_WEIGHTS = [0.22, 0.20, 0.28, 0.24, 0.06]

CHANNELS = ["Organic Search", "Paid Social", "Email", "Affiliate", "Direct"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.15, 0.10, 0.20]

# Channel quality affects monthly churn probability (lower = stickier customers)
CHANNEL_MONTHLY_CHURN = {
    "Organic Search": 0.06,
    "Paid Social": 0.13,
    "Email": 0.08,
    "Affiliate": 0.11,
    "Direct": 0.05,
}

CATEGORIES = {
    "Electronics":      (40, 900),
    "Home & Kitchen":   (15, 300),
    "Apparel":          (10, 150),
    "Beauty":           (8, 80),
    "Sports & Outdoors":(12, 250),
    "Toys & Games":     (8, 120),
    "Books":            (5, 40),
}

SALES_CHANNEL = ["Web", "Mobile App", "Marketplace"]
SALES_CHANNEL_WEIGHTS = [0.45, 0.35, 0.20]

def days_between(d1, d2):
    return (d2 - d1).days

TOTAL_DAYS = days_between(START_DATE, END_DATE)

# ---------------------------------------------------------------------------
# 1. Customers
# ---------------------------------------------------------------------------
print("Generating customers...")

customer_ids = [f"CUST{100000+i}" for i in range(N_CUSTOMERS)]

acq_offsets = []
for _ in range(N_CUSTOMERS):
    u = np.random.beta(1.6, 1.4)
    offset = int(u * TOTAL_DAYS)
    acq_offsets.append(offset)

acquisition_dates = [START_DATE + timedelta(days=o) for o in acq_offsets]

channels = np.random.choice(CHANNELS, size=N_CUSTOMERS, p=CHANNEL_WEIGHTS)
regions = np.random.choice(REGIONS, size=N_CUSTOMERS, p=REGION_WEIGHTS)

value_tier = np.random.choice(
    ["High", "Medium", "Low"], size=N_CUSTOMERS, p=[0.15, 0.45, 0.40]
)
tier_freq_multiplier = {"High": 2.6, "Medium": 1.3, "Low": 0.6}
tier_aov_multiplier = {"High": 1.6, "Medium": 1.1, "Low": 0.85}

customers = pd.DataFrame({
    "customer_id": customer_ids,
    "acquisition_date": acquisition_dates,
    "acquisition_channel": channels,
    "region": regions,
    "value_tier": value_tier,
})

# ---------------------------------------------------------------------------
# 2. Simulate each customer's order timeline until churn or END_DATE
# ---------------------------------------------------------------------------
print("Simulating customer purchase timelines (this creates realistic retention curves)...")

orders_rows = []
order_id_counter = 1

for idx, row in customers.iterrows():
    cust_id = row["customer_id"]
    acq_date = row["acquisition_date"]
    channel = row["acquisition_channel"]
    tier = row["value_tier"]

    monthly_churn = CHANNEL_MONTHLY_CHURN[channel]
    freq_mult = tier_freq_multiplier[tier]

    base_monthly_purchase_prob = min(0.9, 0.30 * freq_mult * np.random.uniform(0.7, 1.3))

    current_date = acq_date
    active = True
    months_since_acq = 0

    while active and current_date <= END_DATE:
        if months_since_acq == 0:
            will_purchase = True
        else:
            will_purchase = np.random.random() < base_monthly_purchase_prob

        if will_purchase:
            jitter_days = np.random.randint(0, 28)
            order_date = current_date + timedelta(days=jitter_days)
            if order_date > END_DATE:
                break

            seasonal_extra = order_date.month in (11, 12)

            n_orders_this_cycle = 1
            if seasonal_extra and np.random.random() < 0.35:
                n_orders_this_cycle = 2

            for _ in range(n_orders_this_cycle):
                orders_rows.append({
                    "order_id": f"ORD{order_id_counter:07d}",
                    "customer_id": cust_id,
                    "order_date": order_date,
                    "sales_channel": np.random.choice(SALES_CHANNEL, p=SALES_CHANNEL_WEIGHTS),
                })
                order_id_counter += 1

        if months_since_acq > 0 and np.random.random() < monthly_churn:
            active = False

        current_date = current_date + timedelta(days=30)
        months_since_acq += 1

        if months_since_acq > 40:
            break

orders_df = pd.DataFrame(orders_rows)
print(f"Generated {len(orders_df):,} orders for {N_CUSTOMERS:,} customers.")

# ---------------------------------------------------------------------------
# 3. Products
# ---------------------------------------------------------------------------
print("Generating product catalog...")

products_rows = []
product_id_counter = 1
N_PRODUCTS = 500
cat_list = list(CATEGORIES.keys())
for i in range(N_PRODUCTS):
    cat = random.choice(cat_list)
    lo, hi = CATEGORIES[cat]
    price = round(np.random.uniform(lo, hi), 2)
    products_rows.append({
        "product_id": f"PROD{1000+product_id_counter}",
        "category": cat,
        "unit_price": price,
    })
    product_id_counter += 1

products_df = pd.DataFrame(products_rows)

# ---------------------------------------------------------------------------
# 4. Order line items (this is where we hit 200,000+ rows)
# ---------------------------------------------------------------------------
print("Generating order line items...")

order_items_rows = []
item_id_counter = 1

orders_df = orders_df.merge(customers[["customer_id", "value_tier"]], on="customer_id", how="left")

for _, o in orders_df.iterrows():
    tier = o["value_tier"]
    aov_mult = tier_aov_multiplier[tier]
    n_items = np.random.choice([1, 2, 3, 4], p=[0.45, 0.30, 0.15, 0.10])

    for _ in range(n_items):
        prod = products_df.sample(1).iloc[0]
        qty = np.random.choice([1, 1, 1, 2, 3], p=[0.55, 0.15, 0.15, 0.10, 0.05])
        unit_price = round(prod["unit_price"] * aov_mult * np.random.uniform(0.9, 1.1), 2)

        is_returned = np.random.random() < 0.04

        order_items_rows.append({
            "order_item_id": f"OI{item_id_counter:08d}",
            "order_id": o["order_id"],
            "product_id": prod["product_id"],
            "category": prod["category"],
            "quantity": qty,
            "unit_price": unit_price,
            "line_revenue": round(unit_price * qty, 2),
            "is_returned": is_returned,
        })
        item_id_counter += 1

    if item_id_counter > TARGET_ORDER_ITEMS:
        break

order_items_df = pd.DataFrame(order_items_rows)
print(f"Generated {len(order_items_df):,} order line items.")

valid_order_ids = set(order_items_df["order_id"].unique())
orders_df = orders_df[orders_df["order_id"].isin(valid_order_ids)].drop(columns=["value_tier"])

# ---------------------------------------------------------------------------
# 5. Introduce realistic messiness for the "cleaning" step to be meaningful
# ---------------------------------------------------------------------------
print("Injecting realistic data-quality issues (nulls, dupes, formatting)...")

dupe_sample = orders_df.sample(frac=0.005, random_state=1)
orders_df = pd.concat([orders_df, dupe_sample], ignore_index=True)

mask = orders_df.sample(frac=0.01, random_state=2).index
orders_df.loc[mask, "sales_channel"] = None

mask2 = customers.sample(frac=0.008, random_state=3).index
customers.loc[mask2, "region"] = None

mask3 = order_items_df.sample(frac=0.02, random_state=4).index
order_items_df.loc[mask3, "category"] = order_items_df.loc[mask3, "category"].str.upper()

mask4 = order_items_df.sample(frac=0.002, random_state=5).index
order_items_df.loc[mask4, "quantity"] = -order_items_df.loc[mask4, "quantity"]

customers_raw = customers.drop(columns=["value_tier"])

# ---------------------------------------------------------------------------
# 6. Save
# ---------------------------------------------------------------------------
import os
out_dir = "data/raw"
os.makedirs(out_dir, exist_ok=True)

customers_raw.to_csv(f"{out_dir}/customers.csv", index=False)
orders_df.to_csv(f"{out_dir}/orders.csv", index=False)
order_items_df.to_csv(f"{out_dir}/order_items.csv", index=False)
products_df.to_csv(f"{out_dir}/products.csv", index=False)

customers[["customer_id", "value_tier"]].to_csv(f"{out_dir}/_ground_truth_value_tier.csv", index=False)

print("\n--- Summary ---")
print(f"Customers:    {len(customers_raw):,}")
print(f"Orders:       {len(orders_df):,}")
print(f"Order items:  {len(order_items_df):,}")
print(f"Products:     {len(products_df):,}")
print("Saved to data/raw/")
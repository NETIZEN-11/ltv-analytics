"""
Visualizations for Cohort & LTV Analysis
------------------------------------------
Reads the CSVs produced by cohort_ltv_analysis.py and generates:
- cohort_retention_heatmap.png
- ltv_by_segment_bar.png
- rfm_segment_distribution.png
- monthly_revenue_trend.png (from the SQL export)

Saved to docs/images/ for use in the README.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

OUT_DIR = "data/processed"
IMG_DIR = "docs/images"
os.makedirs(IMG_DIR, exist_ok=True)

sns.set_style("whitegrid")
plt.rcParams["figure.dpi"] = 120

# ---------------------------------------------------------------------------
# 1. Cohort retention heatmap
# ---------------------------------------------------------------------------
print("Building cohort retention heatmap...")
retention = pd.read_csv(f"{OUT_DIR}/cohort_retention_pct.csv", index_col=0)
retention.columns = retention.columns.astype(int)
retention = retention.iloc[:, :12]

plt.figure(figsize=(14, 9))
sns.heatmap(retention, annot=True, fmt=".0f", cmap="YlGnBu", vmin=0, vmax=100,
            cbar_kws={"label": "% of cohort retained"})
plt.title("Monthly Cohort Retention Heatmap (%)", fontsize=14, fontweight="bold")
plt.xlabel("Months Since First Purchase")
plt.ylabel("Acquisition Cohort (First Purchase Month)")
plt.tight_layout()
plt.savefig(f"{IMG_DIR}/cohort_retention_heatmap.png")
plt.close()
print(f"  Saved {IMG_DIR}/cohort_retention_heatmap.png")

# ---------------------------------------------------------------------------
# 2. LTV by segment & channel bar chart
# ---------------------------------------------------------------------------
print("Building LTV by segment/channel chart...")
ltv_seg = pd.read_csv(f"{OUT_DIR}/ltv_by_segment_channel.csv")

plt.figure(figsize=(12, 7))
order = ["High-Value / Champion", "Loyal / Growing", "At Risk", "Low-Value / Churned"]
sns.barplot(data=ltv_seg, x="acquisition_channel", y="predicted_ltv", hue="segment",
            hue_order=order, palette="viridis")
plt.title("Predicted LTV by Segment & Acquisition Channel", fontsize=14, fontweight="bold")
plt.xlabel("Acquisition Channel")
plt.ylabel("Predicted LTV ($)")
plt.xticks(rotation=20)
plt.legend(title="Segment", bbox_to_anchor=(1.02, 1), loc="upper left")
plt.tight_layout()
plt.savefig(f"{IMG_DIR}/ltv_by_segment_bar.png")
plt.close()
print(f"  Saved {IMG_DIR}/ltv_by_segment_bar.png")

# ---------------------------------------------------------------------------
# 3. RFM segment distribution (pie/donut)
# ---------------------------------------------------------------------------
print("Building RFM segment distribution chart...")
rfm = pd.read_csv(f"{OUT_DIR}/rfm_segments.csv")
seg_counts = rfm["segment"].value_counts().reindex(order)

plt.figure(figsize=(8, 8))
colors = sns.color_palette("viridis", len(seg_counts))
plt.pie(seg_counts.values, labels=seg_counts.index, autopct="%1.1f%%",
        colors=colors, startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5})
plt.title("Customer Segment Distribution (RFM)", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{IMG_DIR}/rfm_segment_distribution.png")
plt.close()
print(f"  Saved {IMG_DIR}/rfm_segment_distribution.png")

# ---------------------------------------------------------------------------
# 4. Monthly revenue trend (from SQL export)
# ---------------------------------------------------------------------------
print("Building monthly revenue trend chart...")
rev = pd.read_csv(f"{OUT_DIR}/01_revenue_trends_result.csv")

fig, ax1 = plt.subplots(figsize=(14, 7))
ax1.bar(rev["order_month"], rev["net_revenue"], color="#2b6cb0", alpha=0.7, label="Net Revenue")
ax1.set_xlabel("Month")
ax1.set_ylabel("Net Revenue ($)", color="#2b6cb0")
ax1.tick_params(axis="x", rotation=90)

ax2 = ax1.twinx()
ax2.plot(rev["order_month"], rev["moving_avg_3mo"], color="#e53e3e", linewidth=2, label="3-Month Moving Avg")
ax2.set_ylabel("3-Month Moving Avg ($)", color="#e53e3e")

plt.title("Monthly Net Revenue Trend with 3-Month Moving Average", fontsize=14, fontweight="bold")
fig.tight_layout()
plt.savefig(f"{IMG_DIR}/monthly_revenue_trend.png")
plt.close()
print(f"  Saved {IMG_DIR}/monthly_revenue_trend.png")

print("\nAll charts saved to docs/images/")
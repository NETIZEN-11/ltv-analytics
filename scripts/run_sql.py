"""
SQL Runner
----------
Executes a .sql file against data/processed/ecommerce.db,
prints a preview of the results, and saves the full result to data/processed/.

Usage:
    python scripts/run_sql.py sql/01_revenue_trends.sql
"""

import sqlite3
import pandas as pd
import sys
import os

DB_PATH = "data/processed/ecommerce.db"

def run_sql_file(sql_path):
    with open(sql_path, "r") as f:
        query = f.read()

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"\n=== Results: {sql_path} ===")
    print(f"Rows returned: {len(df):,}\n")
    print(df.head(20).to_string(index=False))

    out_name = os.path.splitext(os.path.basename(sql_path))[0] + "_result.csv"
    out_path = f"data/processed/{out_name}"
    df.to_csv(out_path, index=False)
    print(f"\nFull results saved to {out_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/run_sql.py <path_to_sql_file>")
        sys.exit(1)
    run_sql_file(sys.argv[1])
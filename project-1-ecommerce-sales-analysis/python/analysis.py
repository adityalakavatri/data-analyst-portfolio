"""
End-to-end pipeline for Project 1.

raw CSVs -> SQLite -> SQL cleaning -> SQL analysis -> charts + CSV exports (for Power BI / Excel)

Run from the project folder:
    python python/generate_data.py     # only needed once
    python python/analysis.py
"""
import re
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, IMG, SQL = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "images", ROOT / "sql"
OUT.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)
DB = ROOT / "data" / "ecommerce.db"

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})
INR = lambda x, _=None: f"₹{x/1e6:.1f}M" if abs(x) >= 1e6 else f"₹{x/1e3:.0f}K"


# ------------------------------------------------------------------ 1. load raw -> SQLite
def load_raw(con):
    for name in ["customers", "products", "orders", "order_items"]:
        df = pd.read_csv(RAW / f"{name}.csv")
        df.to_sql(f"raw_{name}", con, if_exists="replace", index=False)
        print(f"loaded raw_{name:<12} {len(df):>6} rows")


# ------------------------------------------------------------------ 2. SQL cleaning
def clean(con):
    con.executescript((SQL / "01_cleaning.sql").read_text())
    before = con.execute("SELECT COUNT(*) FROM raw_orders").fetchone()[0]
    after = con.execute("SELECT COUNT(*) FROM orders_clean").fetchone()[0]
    print(f"cleaning: orders {before} -> {after} ({before - after} duplicates removed)")


# ------------------------------------------------------------------ 3. SQL analysis
def run_queries(con):
    text = (SQL / "02_analysis_queries.sql").read_text()
    blocks = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)[1:]
    results = {}
    for name, body in zip(blocks[0::2], blocks[1::2]):
        df = pd.read_sql_query(body.strip().rstrip(";"), con)
        df.to_csv(OUT / f"{name}.csv", index=False)
        results[name] = df
        print(f"query {name:<26} -> {len(df):>4} rows")
    return results


# ------------------------------------------------------------------ 4. charts
def charts(r):
    # monthly revenue + MoM
    m = r["monthly_revenue_mom"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(m["order_month"], m["revenue"], marker="o", color="#1f6feb")
    ax.set_title("Monthly revenue (Delivered orders) - festive spike in Oct/Nov", loc="left", fontweight="bold")
    ax.yaxis.set_major_formatter(INR)
    ax.set_xticks(range(0, len(m), 2))
    ax.set_xticklabels(m["order_month"].iloc[::2], rotation=45, ha="right")
    fig.tight_layout(); fig.savefig(IMG / "01_monthly_revenue.png"); plt.close(fig)

    # category revenue vs margin
    c = r["category_profitability"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(c["category"], c["revenue"], color="#8ab4f8", label="Revenue")
    ax.yaxis.set_major_formatter(INR)
    ax2 = ax.twinx()
    ax2.plot(c["category"], c["margin_pct"], color="#d93025", marker="o", label="Margin %")
    ax2.set_ylabel("Profit margin %"); ax2.grid(False)
    ax.set_title("Revenue vs profit margin by category", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "02_category_margin.png"); plt.close(fig)

    # discount impact
    d = r["discount_impact"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(d["discount_pct"].astype(str) + "%", d["margin_pct"], color="#34a853")
    ax.set_title("Profit margin by discount level", loc="left", fontweight="bold")
    ax.set_ylabel("Margin %")
    fig.tight_layout(); fig.savefig(IMG / "03_discount_margin.png"); plt.close(fig)

    # RFM segments
    s = r["rfm_segment_summary"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(s["segment"][::-1], s["revenue_share_pct"][::-1], color="#fbbc04")
    ax.set_title("Revenue share by RFM customer segment (%)", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "04_rfm_segments.png"); plt.close(fig)

    # cohort heatmap
    h = r["cohort_retention"].pivot(index="cohort_month", columns="months_since", values="retention_pct")
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(h.values, cmap="Blues", aspect="auto", vmin=0, vmax=50)
    ax.set_xticks(range(h.shape[1])); ax.set_xticklabels(h.columns)
    ax.set_yticks(range(h.shape[0])); ax.set_yticklabels(h.index, fontsize=7)
    ax.set_xlabel("Months since first order"); ax.grid(False)
    ax.set_title("Cohort retention % (repeat purchase)", loc="left", fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig.tight_layout(); fig.savefig(IMG / "05_cohort_retention.png"); plt.close(fig)


# ------------------------------------------------------------------ 5. exports for Power BI / Excel
def export_for_bi(con):
    fact = pd.read_sql_query("SELECT * FROM sales_fact", con)
    fact.to_csv(OUT / "sales_fact.csv", index=False)
    pd.read_sql_query("SELECT * FROM customers_clean", con).to_csv(OUT / "dim_customers.csv", index=False)
    pd.read_sql_query("SELECT * FROM products_clean", con).to_csv(OUT / "dim_products.csv", index=False)
    print(f"exported sales_fact.csv ({len(fact)} rows) + dimension tables")


if __name__ == "__main__":
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    load_raw(con)
    clean(con)
    res = run_queries(con)
    charts(res)
    export_for_bi(con)
    con.close()
    print("\nKPIs:\n", res["kpi_summary"].T.to_string(header=False))
    print("\nDone. Charts in images/, tables in data/processed/")

"""
Generates a realistic, messy, SYNTHETIC Indian e-commerce dataset.

Synthetic data keeps the project fully reproducible with no licence issues.
Tip: swap in a Kaggle dataset (e.g. Superstore or Olist) and reuse the same pipeline.

Run from the project folder:  python python/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ---------- customers ----------
cities = {
    "Mumbai": ("Maharashtra", "West"), "Pune": ("Maharashtra", "West"), "Nashik": ("Maharashtra", "West"),
    "Ahmedabad": ("Gujarat", "West"), "Delhi": ("Delhi", "North"), "Jaipur": ("Rajasthan", "North"),
    "Lucknow": ("Uttar Pradesh", "North"), "Chandigarh": ("Chandigarh", "North"),
    "Bengaluru": ("Karnataka", "South"), "Chennai": ("Tamil Nadu", "South"),
    "Hyderabad": ("Telangana", "South"), "Kochi": ("Kerala", "South"),
    "Kolkata": ("West Bengal", "East"), "Bhubaneswar": ("Odisha", "East"), "Patna": ("Bihar", "East"),
}
city_names = list(cities)
city_weights = np.array([14, 8, 3, 6, 12, 4, 4, 3, 12, 8, 9, 3, 6, 3, 5], dtype=float)
city_weights /= city_weights.sum()

n_cust = 1500
cust = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(1, n_cust + 1)],
    "customer_name": [f"Customer {i}" for i in range(1, n_cust + 1)],
    "city": rng.choice(city_names, n_cust, p=city_weights),
    "segment": rng.choice(["Consumer", "Corporate", "Home Office"], n_cust, p=[0.6, 0.25, 0.15]),
    "signup_date": pd.to_datetime("2022-01-01") + pd.to_timedelta(rng.integers(0, 900, n_cust), unit="D"),
})
cust["state"] = cust["city"].map(lambda c: cities[c][0])
cust["region"] = cust["city"].map(lambda c: cities[c][1])

# ---------- products ----------
catalog = {
    "Electronics": {"Mobiles": (8000, 60000), "Headphones": (500, 15000), "Laptops": (30000, 120000)},
    "Fashion": {"Men Clothing": (400, 4000), "Women Clothing": (500, 6000), "Footwear": (600, 7000)},
    "Home & Kitchen": {"Cookware": (300, 5000), "Furniture": (2000, 40000), "Decor": (200, 6000)},
    "Grocery": {"Staples": (50, 800), "Snacks": (20, 400), "Beverages": (30, 600)},
}
margins = {"Electronics": 0.12, "Fashion": 0.45, "Home & Kitchen": 0.30, "Grocery": 0.15}
rows, pid = [], 1
for cat, subs in catalog.items():
    for sub, (lo, hi) in subs.items():
        for k in range(1, 9):
            price = round(float(rng.uniform(lo, hi)), -1)
            cost = round(price * (1 - max(0.03, rng.normal(margins[cat], 0.05))), 0)
            rows.append((f"P{pid:04d}", cat, sub, f"{sub} Item {k}", cost, price))
            pid += 1
prod = pd.DataFrame(rows, columns=["product_id", "category", "sub_category", "product_name", "unit_cost", "unit_price"])

# ---------- orders ----------
n_orders = 12000
season = np.array([1.0, 0.9, 0.95, 0.95, 1.0, 0.95, 0.95, 1.05, 1.1, 1.5, 1.6, 1.3])  # festive Oct/Nov spike
days = pd.date_range("2023-01-01", "2024-12-31")
w = np.array([season[d.month - 1] * (1 + 0.0006 * (d - days[0]).days) for d in days])
order_dates = rng.choice(days, n_orders, p=w / w.sum())
cust_idx = rng.choice(n_cust, n_orders, p=rng.dirichlet(np.ones(n_cust) * 0.6))

orders = pd.DataFrame({
    "order_id": [f"O{i:06d}" for i in range(1, n_orders + 1)],
    "customer_id": cust["customer_id"].values[cust_idx],
    "order_date": pd.to_datetime(order_dates),
    "ship_mode": rng.choice(["Standard", "Express", "Same Day"], n_orders, p=[0.6, 0.3, 0.1]),
    "discount_pct": rng.choice([0, 5, 10, 15, 20, 30], n_orders, p=[0.35, 0.2, 0.2, 0.12, 0.08, 0.05]),
    "status": rng.choice(["Delivered", "Returned", "Cancelled"], n_orders, p=[0.89, 0.07, 0.04]),
})
# customers can only order on/after their signup date
signup = cust.set_index("customer_id")["signup_date"]
orders["order_date"] = np.maximum(orders["order_date"], orders["customer_id"].map(signup))
orders["order_date"] = np.minimum(orders["order_date"], pd.Timestamp("2024-12-31"))

# ---------- order items ----------
items = []
for oid in orders["order_id"]:
    n_lines = int(rng.choice([1, 2, 3, 4], p=[0.55, 0.28, 0.12, 0.05]))
    for p in rng.choice(prod["product_id"], n_lines, replace=False):
        items.append((oid, p, int(rng.choice([1, 1, 1, 2, 3]))))
items = pd.DataFrame(items, columns=["order_id", "product_id", "quantity"])

# ---------- inject realistic dirt (so the cleaning step is genuine) ----------
dirty_orders = orders.copy()
dirty_orders["order_date"] = dirty_orders["order_date"].dt.strftime("%Y-%m-%d")

idx = dirty_orders.sample(120, random_state=3).index
dirty_orders.loc[idx, "status"] = dirty_orders.loc[idx, "status"].str.lower()      # inconsistent case

idx = dirty_orders.sample(90, random_state=2).index
dirty_orders.loc[idx, "ship_mode"] = None                                          # missing values

dirty_orders = pd.concat([dirty_orders, dirty_orders.sample(60, random_state=1)],  # 60 duplicate rows
                         ignore_index=True)

dirty_cust = cust.copy()
dirty_cust["signup_date"] = dirty_cust["signup_date"].dt.strftime("%Y-%m-%d")
idx = dirty_cust.sample(80, random_state=4).index
dirty_cust.loc[idx, "city"] = dirty_cust.loc[idx, "city"].str.upper() + " "         # case + trailing spaces

dirty_cust.to_csv(RAW / "customers.csv", index=False)
prod.to_csv(RAW / "products.csv", index=False)
dirty_orders.to_csv(RAW / "orders.csv", index=False)
items.to_csv(RAW / "order_items.csv", index=False)

print("Generated rows:", {
    "customers": len(dirty_cust), "products": len(prod),
    "orders": len(dirty_orders), "order_items": len(items),
})

"""
Generates a SYNTHETIC HR dataset (1,500 employees) where attrition depends on realistic drivers:
overtime, low job satisfaction, low pay, long gaps since promotion, short tenure and long commutes.

Some dirt is injected on purpose (duplicates, missing income, inconsistent text) so cleaning is genuine.
Tip: you can replace this with the public IBM HR Analytics dataset from Kaggle; the pipeline logic is the same.

Run from the project folder:  python python/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

n = 1500
roles = {
    "Sales": ["Sales Executive", "Sales Manager", "Business Development"],
    "Technology": ["Software Engineer", "Data Analyst", "QA Engineer", "DevOps Engineer"],
    "Finance": ["Accountant", "Financial Analyst"],
    "HR": ["HR Executive", "Recruiter"],
    "Operations": ["Operations Associate", "Supply Chain Analyst"],
}
dept = rng.choice(list(roles), n, p=[0.28, 0.32, 0.12, 0.08, 0.20])
job_role = np.array([rng.choice(roles[d]) for d in dept])

age = np.clip(rng.normal(34, 8, n).round(), 20, 60).astype(int)
years_at_company = np.clip((age - 21) * rng.beta(1.3, 3.0, n), 0, 30).round().astype(int)
base_income = {"Sales": 42000, "Technology": 65000, "Finance": 52000, "HR": 38000, "Operations": 36000}
income = np.array([base_income[d] for d in dept]) * rng.lognormal(0, 0.28, n) * (1 + 0.04 * years_at_company)
income = (income / 500).round() * 500

df = pd.DataFrame({
    "employee_id": [f"E{i:04d}" for i in range(1, n + 1)],
    "age": age,
    "gender": rng.choice(["Male", "Female"], n, p=[0.58, 0.42]),
    "department": dept,
    "job_role": job_role,
    "education": rng.choice(["Bachelors", "Masters", "Diploma", "PhD"], n, p=[0.5, 0.3, 0.17, 0.03]),
    "monthly_income": income,
    "years_at_company": years_at_company,
    "years_since_last_promotion": np.minimum(rng.integers(0, 9, n), years_at_company),
    "overtime": rng.choice(["Yes", "No"], n, p=[0.3, 0.7]),
    "job_satisfaction": rng.choice([1, 2, 3, 4], n, p=[0.15, 0.2, 0.35, 0.3]),
    "work_life_balance": rng.choice([1, 2, 3, 4], n, p=[0.08, 0.22, 0.5, 0.2]),
    "distance_from_home_km": np.clip(rng.gamma(2.0, 7.0, n).round(), 1, 60).astype(int),
    "performance_rating": rng.choice([3, 4], n, p=[0.82, 0.18]),
    "num_companies_worked": rng.choice([0, 1, 2, 3, 4, 5], n, p=[0.12, 0.35, 0.2, 0.15, 0.1, 0.08]),
})

# ---------- attrition = logistic function of the drivers above ----------
inc_rel = np.log(df["monthly_income"] / df.groupby("department")["monthly_income"].transform("median"))
logit = (
    -2.1
    + 1.0 * (df["overtime"] == "Yes")
    - 0.45 * (df["job_satisfaction"] - 2.5)
    - 0.30 * (df["work_life_balance"] - 2.5)
    - 1.2 * inc_rel
    + 0.30 * (df["years_since_last_promotion"] >= 5)
    + 0.60 * (df["years_at_company"] <= 2)
    + 0.025 * df["distance_from_home_km"]
    + 0.30 * (df["department"] == "Sales")
    + 0.08 * df["num_companies_worked"]
)
prob = 1 / (1 + np.exp(-logit))
df["attrition"] = np.where(rng.random(n) < prob, "Yes", "No")

# ---------- inject realistic dirt ----------
df.loc[df.sample(45, random_state=1).index, "monthly_income"] = np.nan             # missing income
idx = df.sample(60, random_state=2).index
df.loc[idx, "department"] = df.loc[idx, "department"].str.upper()                  # inconsistent case
idx = df.sample(40, random_state=3).index
df.loc[idx, "overtime"] = df.loc[idx, "overtime"].map({"Yes": "Y", "No": "N"})     # inconsistent coding
df = pd.concat([df, df.sample(25, random_state=4)], ignore_index=True)             # duplicate rows

df.to_csv(RAW / "hr_employees.csv", index=False)
print(f"Generated {len(df)} rows (incl. 25 duplicates). Attrition rate (raw): {(df.attrition == 'Yes').mean():.1%}")

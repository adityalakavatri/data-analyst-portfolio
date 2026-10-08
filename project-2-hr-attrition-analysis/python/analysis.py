"""
End-to-end pipeline for Project 2 (HR attrition).

raw CSV -> pandas cleaning -> SQLite -> SQL analysis -> statistical tests -> logistic regression
        -> charts + CSV exports (for Excel / Power BI)

Run from the project folder:
    python python/generate_data.py   # only needed once
    python python/analysis.py
"""
import re
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, IMG, SQL = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "images", ROOT / "sql"
OUT.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})


# ------------------------------------------------------------------ 1. cleaning (pandas)
def clean():
    df = pd.read_csv(RAW / "hr_employees.csv")
    log = {"rows_raw": len(df)}

    df = df.drop_duplicates()
    log["duplicates_removed"] = log["rows_raw"] - len(df)

    df["department"] = df["department"].str.strip().str.title().replace({"Hr": "HR"})  # .title() turns HR into Hr
    df["overtime"] = df["overtime"].replace({"Y": "Yes", "N": "No"})

    log["missing_income"] = int(df["monthly_income"].isna().sum())
    # impute with the median of the same job role (more accurate than one global median)
    df["monthly_income"] = df["monthly_income"].fillna(df.groupby("job_role")["monthly_income"].transform("median"))

    assert df["employee_id"].is_unique and df.isna().sum().sum() == 0, "cleaning left problems"
    df.to_csv(OUT / "employees_clean.csv", index=False)
    pd.Series(log).to_csv(OUT / "cleaning_log.csv", header=["value"])
    print("cleaning:", log)
    return df


# ------------------------------------------------------------------ 2. SQL analysis
def run_sql(df):
    con = sqlite3.connect(":memory:")
    df.to_sql("employees", con, index=False)
    text = (SQL / "analysis_queries.sql").read_text()
    blocks = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)[1:]
    res = {}
    for name, body in zip(blocks[0::2], blocks[1::2]):
        q = pd.read_sql_query(body.strip().rstrip(";"), con)
        q.to_csv(OUT / f"{name}.csv", index=False)
        res[name] = q
        print(f"query {name:<30} -> {len(q):>3} rows")
    con.close()
    return res


# ------------------------------------------------------------------ 3. statistical tests
def tests(df):
    rows = []
    for col in ["overtime", "department", "job_satisfaction"]:
        chi2, p, dof, _ = stats.chi2_contingency(pd.crosstab(df[col], df["attrition"]))
        rows.append({"test": f"Chi-square: attrition vs {col}", "statistic": round(chi2, 2), "p_value": p})
    leave, stay = df.loc[df.attrition == "Yes", "monthly_income"], df.loc[df.attrition == "No", "monthly_income"]
    u, p = stats.mannwhitneyu(leave, stay)
    rows.append({"test": "Mann-Whitney U: income, leavers vs stayers", "statistic": round(u, 0), "p_value": p})
    t = pd.DataFrame(rows)
    t["significant_at_5pct"] = t["p_value"] < 0.05
    t["p_value"] = t["p_value"].map(lambda x: f"{x:.2e}")
    t.to_csv(OUT / "statistical_tests.csv", index=False)
    print("\n", t.to_string(index=False))


# ------------------------------------------------------------------ 4. predictive model
def model(df):
    y = (df["attrition"] == "Yes").astype(int)
    X = df.drop(columns=["attrition", "employee_id"])
    num = X.select_dtypes("number").columns.tolist()
    cat = X.select_dtypes(exclude="number").columns.tolist()

    pre = ColumnTransformer([("num", StandardScaler(), num),
                             ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cat)])
    pipe = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    pipe.fit(Xtr, ytr)
    proba = pipe.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)
    rep = classification_report(yte, pipe.predict(Xte), target_names=["Stayed", "Left"], output_dict=True)
    print(f"\nModel: logistic regression | test ROC-AUC = {auc:.3f}")
    print(classification_report(yte, pipe.predict(Xte), target_names=["Stayed", "Left"]))

    names = pipe.named_steps["pre"].get_feature_names_out()
    coefs = pipe.named_steps["clf"].coef_[0]
    drivers = (pd.DataFrame({"feature": [n.split("__")[1] for n in names], "coef": coefs,
                             "odds_ratio": np.exp(coefs)})
               .assign(abs_coef=lambda d: d.coef.abs())
               .sort_values("abs_coef", ascending=False).drop(columns="abs_coef").round(3))
    drivers.to_csv(OUT / "model_drivers.csv", index=False)
    pd.DataFrame({"metric": ["roc_auc", "recall_left", "precision_left"],
                  "value": [auc, rep["Left"]["recall"], rep["Left"]["precision"]]}).round(3) \
        .to_csv(OUT / "model_metrics.csv", index=False)

    # score CURRENT employees -> list of flight-risk employees (what HR would actually act on)
    current = df[df.attrition == "No"].copy()
    current["attrition_risk"] = pipe.predict_proba(current.drop(columns=["attrition", "employee_id"]))[:, 1].round(3)
    risk = current.sort_values("attrition_risk", ascending=False)
    risk[["employee_id", "department", "job_role", "monthly_income", "overtime",
          "job_satisfaction", "years_since_last_promotion", "attrition_risk"]].head(50) \
        .to_csv(OUT / "high_risk_employees.csv", index=False)
    return drivers, auc


# ------------------------------------------------------------------ 5. charts
def charts(df, res, drivers):
    d = res["attrition_by_department"]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(d["department"], d["attrition_rate_pct"], color="#1f6feb")
    ov = res["attrition_overall"]["attrition_rate_pct"].iloc[0]
    ax.axhline(ov, color="#d93025", ls="--", label=f"Company average {ov}%")
    ax.set_ylabel("Attrition rate %"); ax.legend()
    ax.set_title("Attrition rate by department", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "01_attrition_by_department.png"); plt.close(fig)

    o, s = res["attrition_by_overtime"], res["attrition_by_satisfaction"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(o["overtime"], o["attrition_rate_pct"], color=["#34a853", "#d93025"])
    axes[0].set_title("Attrition % by overtime", loc="left", fontweight="bold")
    axes[1].bar(s["job_satisfaction"].astype(str), s["attrition_rate_pct"], color="#fbbc04")
    axes[1].set_title("Attrition % by job satisfaction (1=low, 4=high)", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "02_overtime_satisfaction.png"); plt.close(fig)

    t = res["attrition_by_tenure_band"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(t["tenure_band"].str[3:], t["attrition_rate_pct"], color="#8ab4f8")
    ax.set_title("Attrition % by tenure: early-tenure exits dominate", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "03_tenure.png"); plt.close(fig)

    top = drivers.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(top["feature"], top["coef"], color=np.where(top["coef"] > 0, "#d93025", "#34a853"))
    ax.set_title("Model drivers (red = raises attrition risk, green = lowers it)", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "04_model_drivers.png"); plt.close(fig)


if __name__ == "__main__":
    data = clean()
    results = run_sql(data)
    tests(data)
    drv, auc = model(data)
    charts(data, results, drv)
    print("\nOverall:\n", results["attrition_overall"].to_string(index=False))
    print("\nTop drivers:\n", drv.head(8).to_string(index=False))
    print("\nDone. Charts in images/, tables in data/processed/")

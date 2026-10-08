# Data Analyst Portfolio

Two end-to-end analytics projects that use the core data analyst toolkit: **SQL · Python/R · Excel · Power BI**.
Each project follows the real workflow: messy data → cleaning → SQL analysis → statistics/modelling → business insights and recommendations.

| # | Project | Business question | Tools | Headline result |
|---|---|---|---|---|
| 1 | [E-commerce Sales & Customer Analytics](project-1-ecommerce-sales-analysis/) | Where do we make (and lose) money? | SQL, Python, Excel, Power BI | Electronics is 75% of revenue at a 3% margin; discounts of 20%+ make orders loss-making |
| 2 | [HR Attrition Analysis & Flight-Risk Model](project-2-hr-attrition-analysis/) | Who leaves, why, and what does it cost? | SQL, Python, R, Excel, Power BI | Overtime doubles attrition (42.5% vs 19.3%); department is not a significant driver |

> **About the data:** both datasets are synthetic (generated with fixed random seeds, with messy data injected on purpose) so every result is reproducible.
> Findings describe this data and demonstrate the method. Each README explains how to swap in a real Kaggle dataset.

## Quick start
```bash
git clone https://github.com/<your-username>/data-analyst-portfolio.git
cd data-analyst-portfolio/project-1-ecommerce-sales-analysis
pip install -r requirements.txt
python python/generate_data.py && python python/analysis.py && python python/build_excel.py
```
(Repeat inside `project-2-hr-attrition-analysis/`.) Requires Python 3.9+; the SQL uses window functions, so SQLite 3.25+.

## Skills at a glance
- **SQL:** CTEs, joins, window functions (`LAG`, `RANK`, `NTILE`, running totals), cohort retention, RFM segmentation
- **Python:** pandas cleaning pipelines, SciPy hypothesis tests, scikit-learn modelling, matplotlib charts
- **R:** logistic regression, odds ratios, ggplot2
- **Excel:** Tables, SUMIFS/COUNTIFS, PivotTables with slicers
- **Power BI:** star-schema model, DAX time intelligence, dashboard design
- **Thinking:** stating assumptions, catching confounding, reporting model limits honestly, turning numbers into recommendations

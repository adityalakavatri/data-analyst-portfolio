-- =====================================================================
-- analysis_queries.sql  |  SQLite dialect (3.25+ for window functions)
-- Reads the cleaned `employees` table that python/analysis.py loads.
-- Each query starts with "-- name: <id>"; results are saved to data/processed/<id>.csv
-- =====================================================================

-- name: attrition_overall
SELECT
    COUNT(*)                                                        AS employees,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)              AS leavers,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM employees;

-- name: attrition_by_department
SELECT
    department,
    COUNT(*)                                                        AS employees,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)              AS leavers,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM employees
GROUP BY department
ORDER BY attrition_rate_pct DESC;

-- name: attrition_by_overtime
SELECT
    overtime,
    COUNT(*)                                                        AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM employees
GROUP BY overtime;

-- name: attrition_by_tenure_band
SELECT
    CASE
        WHEN years_at_company <= 2  THEN '1. 0-2 yrs'
        WHEN years_at_company <= 5  THEN '2. 3-5 yrs'
        WHEN years_at_company <= 10 THEN '3. 6-10 yrs'
        ELSE                             '4. 10+ yrs'
    END                                                             AS tenure_band,
    COUNT(*)                                                        AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM employees
GROUP BY tenure_band
ORDER BY tenure_band;

-- name: attrition_by_income_quartile
-- Pay quartiles computed WITHIN each department (so a Sales salary is not compared to an Engineer's).
WITH q AS (
    SELECT *,
           NTILE(4) OVER (PARTITION BY department ORDER BY monthly_income) AS pay_quartile
    FROM employees
)
SELECT
    pay_quartile,
    COUNT(*)                                                        AS employees,
    ROUND(AVG(monthly_income), 0)                                   AS avg_income,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM q
GROUP BY pay_quartile
ORDER BY pay_quartile;

-- name: attrition_by_satisfaction
SELECT
    job_satisfaction,
    COUNT(*)                                                        AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM employees
GROUP BY job_satisfaction
ORDER BY job_satisfaction;

-- name: attrition_by_promotion_gap
SELECT
    CASE WHEN years_since_last_promotion >= 5 THEN '5+ yrs since promotion' ELSE '0-4 yrs' END AS promotion_gap,
    COUNT(*)                                                        AS employees,
    ROUND(100.0 * SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 1) AS attrition_rate_pct
FROM employees
GROUP BY promotion_gap;

-- name: attrition_cost_by_department
-- ASSUMPTION (editable): replacing an employee costs ~50% of their annual salary
-- (recruiting + onboarding + lost productivity). This is a common rule of thumb, not a measured figure.
SELECT
    department,
    SUM(CASE WHEN attrition = 'Yes' THEN 1 ELSE 0 END)                           AS leavers,
    ROUND(SUM(CASE WHEN attrition = 'Yes' THEN monthly_income * 12 * 0.5 END), 0) AS est_replacement_cost_inr
FROM employees
GROUP BY department
ORDER BY est_replacement_cost_inr DESC;

-- name: rule_based_risk_flags
-- Transparent, rule-based flight-risk score for CURRENT employees (0-6 points).
-- Python adds a model-based probability on top of this in high_risk_employees.csv.
WITH dept_median AS (
    -- SQLite has no MEDIAN(); use the average as the department pay benchmark
    SELECT department, AVG(monthly_income) AS avg_income FROM employees GROUP BY department
)
SELECT
    e.employee_id, e.department, e.job_role, e.monthly_income,
      (CASE WHEN e.overtime = 'Yes'                          THEN 2 ELSE 0 END)
    + (CASE WHEN e.job_satisfaction <= 2                     THEN 1 ELSE 0 END)
    + (CASE WHEN e.years_since_last_promotion >= 5           THEN 1 ELSE 0 END)
    + (CASE WHEN e.monthly_income < 0.9 * d.avg_income       THEN 1 ELSE 0 END)
    + (CASE WHEN e.years_at_company <= 2                     THEN 1 ELSE 0 END) AS risk_points
FROM employees e
JOIN dept_median d USING (department)
WHERE e.attrition = 'No'
ORDER BY risk_points DESC, e.monthly_income DESC
LIMIT 50;

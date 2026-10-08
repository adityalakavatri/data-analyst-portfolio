# Power BI Dashboard Guide: HR Attrition

Power BI Desktop files (`.pbix`) can only be created inside Power BI Desktop, so this guide gives you the data model,
DAX and layout to build it in about 60 minutes. Save the result as `powerbi/HR_Attrition_Dashboard.pbix`
and add 2-3 screenshots to `images/`.

## 1. Load the data (Get Data > Text/CSV, from `data/processed/`)
| File | Use |
|---|---|
| `employees_clean.csv` | Main table (one row per employee) |
| `high_risk_employees.csv` | Top 50 current employees by model-based risk score |
| `model_drivers.csv` | Model coefficients and odds ratios (for a "what drives exits" visual) |

In Power Query: set data types, then add a calculated column for tenure band (below).

## 2. Calculated columns (on `employees_clean`)
```DAX
Tenure Band =
SWITCH ( TRUE (),
    employees_clean[years_at_company] <= 2,  "1. 0-2 yrs",
    employees_clean[years_at_company] <= 5,  "2. 3-5 yrs",
    employees_clean[years_at_company] <= 10, "3. 6-10 yrs",
    "4. 10+ yrs" )

Age Group =
SWITCH ( TRUE (),
    employees_clean[age] < 25, "<25",
    employees_clean[age] < 35, "25-34",
    employees_clean[age] < 45, "35-44",
    "45+" )

Left Flag = IF ( employees_clean[attrition] = "Yes", 1, 0 )
```

## 3. Measures
```DAX
Headcount        = COUNTROWS ( employees_clean )
Leavers          = CALCULATE ( COUNTROWS ( employees_clean ), employees_clean[attrition] = "Yes" )
Attrition %      = DIVIDE ( [Leavers], [Headcount] )
Avg Income       = AVERAGE ( employees_clean[monthly_income] )
Avg Satisfaction = AVERAGE ( employees_clean[job_satisfaction] )
Overtime %       = DIVIDE ( CALCULATE ( [Headcount], employees_clean[overtime] = "Yes" ), [Headcount] )

// Attrition vs company average, for conditional formatting
Attrition vs Avg =
VAR company = CALCULATE ( [Attrition %], ALL ( employees_clean ) )
RETURN [Attrition %] - company

// Editable assumption: replacement cost = 50% of annual salary (rule of thumb, not a measured figure)
Replacement Cost Assumption = 0.5
Est. Attrition Cost =
SUMX (
    FILTER ( employees_clean, employees_clean[attrition] = "Yes" ),
    employees_clean[monthly_income] * 12 * [Replacement Cost Assumption]
)
```
Tip: turn `Replacement Cost Assumption` into a What-If parameter (Modeling > New Parameter) so viewers can change it.

## 4. Layout
**Page 1: Attrition Overview**
```
+------------------------------------------------------------+
| Title  |  Slicers: Department | Overtime | Tenure Band      |
+--------+----------+------------+-----------+---------------+
| Headcount | Leavers | Attrition % | Avg Income | Est. Cost  |   <- KPI cards
+-----------+---------+------------+------------+-------------+
| Bar: Attrition % by Department (avg line) | Column: by Tenure |
+-------------------------------------------+------------------+
| Clustered bar: Overtime Yes vs No         | Line: by Job     |
| attrition %                               | Satisfaction     |
+-------------------------------------------+------------------+
```

**Page 2: Drivers & Flight Risk**
- Bar chart from `model_drivers.csv` (top 8 by |coef|)
- Table from `high_risk_employees.csv` with data bars on `attrition_risk`
- Scatter: monthly_income vs job_satisfaction, coloured by attrition

## 5. Design tips
- Use red only for "bad" (high attrition) and one neutral blue elsewhere.
- Titles should state the finding ("Overtime employees leave at more than twice the rate").
- Add a text box with the data period, the data source (synthetic) and the replacement-cost assumption.
- Treat `high_risk_employees` as a list for HR conversations (manager check-ins, workload review), not for punishing anyone. Say so on the page.

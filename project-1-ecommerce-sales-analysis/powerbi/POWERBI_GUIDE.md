# Power BI Dashboard Guide: E-commerce Sales

Power BI Desktop files (`.pbix`) can only be created inside Power BI Desktop, so this guide gives you everything
needed to build the dashboard in about 60-90 minutes. When you finish, save it as
`powerbi/Ecommerce_Sales_Dashboard.pbix` and add 2-3 screenshots to `images/` so recruiters can see it without opening Power BI.

## 1. Load the data
Home > Get Data > Text/CSV, and load these three files from `data/processed/`:

| File | Role |
|---|---|
| `sales_fact.csv` | Fact table (one row per order line) |
| `dim_customers.csv` | Customer dimension |
| `dim_products.csv` | Product dimension |

Optional extras: `customer_rfm.csv`, `cohort_retention.csv`, `monthly_revenue_mom.csv`.

## 2. Model
Create relationships (many-to-one, single direction):
- `sales_fact[customer_id]` -> `dim_customers[customer_id]`
- `sales_fact[product_id]`  -> `dim_products[product_id]`

Create a Date table (Modeling > New table) and relate it to `sales_fact[order_date]`:
```DAX
DimDate =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2023, 1, 1 ), DATE ( 2024, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "Month No", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM yy" ),
    "Quarter", "Q" & QUARTER ( [Date] )
)
```
Set `Month` to sort by `Month No`, and mark `DimDate` as the date table. In Power Query, set `order_date` to Date type.

## 3. DAX measures
Create a table called `_Measures` (Enter Data) and add:
```DAX
Revenue            = CALCULATE ( SUM ( sales_fact[revenue] ), sales_fact[status] = "Delivered" )
Profit             = CALCULATE ( SUM ( sales_fact[profit] ),  sales_fact[status] = "Delivered" )
Margin %           = DIVIDE ( [Profit], [Revenue] )
Orders             = CALCULATE ( DISTINCTCOUNT ( sales_fact[order_id] ), sales_fact[status] = "Delivered" )
Avg Order Value    = DIVIDE ( [Revenue], [Orders] )
Active Customers   = CALCULATE ( DISTINCTCOUNT ( sales_fact[customer_id] ), sales_fact[status] = "Delivered" )

Revenue LY         = CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( DimDate[Date] ) )
YoY Growth %       = DIVIDE ( [Revenue] - [Revenue LY], [Revenue LY] )
Revenue MoM %      = VAR prev = CALCULATE ( [Revenue], DATEADD ( DimDate[Date], -1, MONTH ) )
                     RETURN DIVIDE ( [Revenue] - prev, prev )
Revenue YTD        = TOTALYTD ( [Revenue], DimDate[Date] )

Return Rate %      = DIVIDE (
                        CALCULATE ( DISTINCTCOUNT ( sales_fact[order_id] ), sales_fact[status] = "Returned" ),
                        DISTINCTCOUNT ( sales_fact[order_id] ) )
Loss-making Revenue = CALCULATE ( [Revenue], FILTER ( sales_fact, sales_fact[profit] < 0 ) )
```

## 4. Page layout (build 2 pages)

**Page 1: Executive Overview**
```
+--------------------------------------------------------------+
| Title bar   |  Slicers: Year | Region | Category             |
+-------------+----------+----------+-----------+--------------+
| Revenue     | Profit   | Margin % | Orders    | Avg Order    |   <- 5 KPI cards
+-------------+----------+----------+-----------+--------------+
| Line chart: Revenue by Month (+ LY line)  | Map / bar: Region |
+-------------------------------------------+-------------------+
| Column + line: Category revenue & margin  | Discount vs margin|
+-------------------------------------------+-------------------+
```

**Page 2: Customer Insights**
- Donut: customers by RFM segment (from `customer_rfm.csv`)
- Bar: revenue share by RFM segment
- Matrix heatmap: cohort retention (rows = cohort_month, columns = months_since, values = retention_pct, conditional formatting)
- Table: top 10 customers by revenue with a drill-through to order detail

## 5. Design rules that make it look professional
- One colour palette (3 colours max + grey); use red only for negative margin.
- Titles that state the insight ("Discounts above 15% turn orders loss-making") rather than labels ("Discount chart").
- Align all visuals to a grid; leave white space; add a subtitle with the data period.
- Add a tooltip page and bookmarks (Overview / Details) for interactivity.
- Publish to Power BI Service (free account) and paste the public link in the README if your organisation or college allows it.

## 6. Insights your dashboard should surface (verify against your own visuals)
These come from the SQL output in `data/processed/`:
- Electronics is about 75% of revenue but only about 3% margin; Fashion is about 7% of revenue at about 40% margin.
- Orders with 20% or 30% discounts have negative margins.
- Revenue peaks in the festive months (Oct-Dec) in both years, with Nov 2024 the single highest month.

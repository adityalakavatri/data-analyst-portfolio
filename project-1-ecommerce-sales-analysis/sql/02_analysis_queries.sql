-- =====================================================================
-- 02_analysis_queries.sql  |  SQLite dialect (needs SQLite 3.25+ for window functions)
-- Each query starts with a "-- name: <id>" marker; python/analysis.py runs them
-- one by one and saves each result to data/processed/<id>.csv
-- =====================================================================

-- name: kpi_summary
-- Headline KPIs for Delivered orders.
SELECT
    ROUND(SUM(revenue), 0)                                   AS total_revenue,
    ROUND(SUM(profit), 0)                                    AS total_profit,
    ROUND(100.0 * SUM(profit) / SUM(revenue), 1)             AS profit_margin_pct,
    COUNT(DISTINCT order_id)                                 AS orders,
    COUNT(DISTINCT customer_id)                              AS active_customers,
    ROUND(SUM(revenue) / COUNT(DISTINCT order_id), 0)        AS avg_order_value
FROM sales_fact
WHERE status = 'Delivered';

-- name: monthly_revenue_mom
-- Monthly revenue with month-over-month growth and a running total (window functions).
WITH monthly AS (
    SELECT order_month, ROUND(SUM(revenue), 0) AS revenue, ROUND(SUM(profit), 0) AS profit
    FROM sales_fact
    WHERE status = 'Delivered'
    GROUP BY order_month
)
SELECT
    order_month,
    revenue,
    profit,
    LAG(revenue) OVER (ORDER BY order_month)                                         AS prev_month_revenue,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
          / LAG(revenue) OVER (ORDER BY order_month), 1)                             AS mom_growth_pct,
    SUM(revenue) OVER (ORDER BY order_month)                                         AS running_revenue
FROM monthly
ORDER BY order_month;

-- name: category_profitability
-- Which categories make money, and how thin are the margins?
SELECT
    category,
    ROUND(SUM(revenue), 0)                           AS revenue,
    ROUND(SUM(profit), 0)                            AS profit,
    ROUND(100.0 * SUM(profit) / SUM(revenue), 1)     AS margin_pct,
    ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) AS revenue_share_pct
FROM sales_fact
WHERE status = 'Delivered'
GROUP BY category
ORDER BY profit DESC;

-- name: top_products_per_category
-- Top 3 products by profit inside each category (RANK + PARTITION BY).
WITH ranked AS (
    SELECT
        category, product_name,
        ROUND(SUM(profit), 0) AS profit,
        RANK() OVER (PARTITION BY category ORDER BY SUM(profit) DESC) AS rnk
    FROM sales_fact
    WHERE status = 'Delivered'
    GROUP BY category, product_name
)
SELECT category, rnk, product_name, profit
FROM ranked
WHERE rnk <= 3
ORDER BY category, rnk;

-- name: regional_performance
SELECT
    region,
    COUNT(DISTINCT customer_id)                      AS customers,
    COUNT(DISTINCT order_id)                         AS orders,
    ROUND(SUM(revenue), 0)                           AS revenue,
    ROUND(SUM(revenue) / COUNT(DISTINCT order_id), 0) AS avg_order_value,
    ROUND(100.0 * SUM(profit) / SUM(revenue), 1)     AS margin_pct
FROM sales_fact
WHERE status = 'Delivered'
GROUP BY region
ORDER BY revenue DESC;

-- name: discount_impact
-- Do heavier discounts actually hurt profit?
SELECT
    discount_pct,
    COUNT(DISTINCT order_id)                         AS orders,
    ROUND(SUM(revenue), 0)                           AS revenue,
    ROUND(SUM(profit), 0)                            AS profit,
    ROUND(100.0 * SUM(profit) / SUM(revenue), 1)     AS margin_pct
FROM sales_fact
WHERE status = 'Delivered'
GROUP BY discount_pct
ORDER BY discount_pct;

-- name: return_rate_by_category
SELECT
    category,
    COUNT(DISTINCT order_id)                                                        AS orders,
    COUNT(DISTINCT CASE WHEN status = 'Returned' THEN order_id END)                 AS returned_orders,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN status = 'Returned' THEN order_id END)
          / COUNT(DISTINCT order_id), 1)                                            AS return_rate_pct
FROM sales_fact
GROUP BY category
ORDER BY return_rate_pct DESC;

-- name: customer_rfm
-- RFM segmentation: Recency, Frequency, Monetary scored 1-4 with NTILE.
WITH ref AS (SELECT DATE(MAX(order_date), '+1 day') AS ref_date FROM sales_fact),
base AS (
    SELECT
        customer_id,
        CAST(JULIANDAY((SELECT ref_date FROM ref)) - JULIANDAY(MAX(order_date)) AS INT) AS recency_days,
        COUNT(DISTINCT order_id)                                                         AS frequency,
        ROUND(SUM(revenue), 0)                                                           AS monetary
    FROM sales_fact
    WHERE status = 'Delivered'
    GROUP BY customer_id
),
scored AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,   -- recent buyers get the high score
        NTILE(4) OVER (ORDER BY frequency)         AS f_score,
        NTILE(4) OVER (ORDER BY monetary)          AS m_score
    FROM base
)
SELECT
    customer_id, recency_days, frequency, monetary, r_score, f_score, m_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 2                  THEN 'Loyal / Potential'
        WHEN r_score = 4                                    THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        WHEN r_score = 1  AND f_score <= 2                  THEN 'Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM scored;

-- name: rfm_segment_summary
-- Rolls the RFM table up (re-uses the logic by wrapping it in a CTE).
WITH ref AS (SELECT DATE(MAX(order_date), '+1 day') AS ref_date FROM sales_fact),
base AS (
    SELECT customer_id,
        CAST(JULIANDAY((SELECT ref_date FROM ref)) - JULIANDAY(MAX(order_date)) AS INT) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        ROUND(SUM(revenue), 0)   AS monetary
    FROM sales_fact WHERE status = 'Delivered' GROUP BY customer_id
),
scored AS (
    SELECT *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency)         AS f_score,
        NTILE(4) OVER (ORDER BY monetary)          AS m_score
    FROM base
),
seg AS (
    SELECT *,
        CASE
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 2                  THEN 'Loyal / Potential'
            WHEN r_score = 4                                    THEN 'New Customers'
            WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
            WHEN r_score = 1  AND f_score <= 2                  THEN 'Lost'
            ELSE 'Needs Attention'
        END AS segment
    FROM scored
)
SELECT
    segment,
    COUNT(*)                                          AS customers,
    ROUND(SUM(monetary), 0)                           AS revenue,
    ROUND(100.0 * SUM(monetary) / SUM(SUM(monetary)) OVER (), 1) AS revenue_share_pct
FROM seg
GROUP BY segment
ORDER BY revenue DESC;

-- name: pareto_customers
-- Do the top 20% of customers drive ~80% of revenue? Deciles + cumulative share (window functions).
WITH cust AS (
    SELECT customer_id, SUM(revenue) AS revenue
    FROM sales_fact WHERE status = 'Delivered'
    GROUP BY customer_id
),
ranked AS (
    SELECT customer_id, revenue,
           NTILE(10) OVER (ORDER BY revenue DESC)                    AS decile,
           SUM(revenue) OVER (ORDER BY revenue DESC, customer_id)    AS cum_revenue,
           SUM(revenue) OVER ()                                      AS total_revenue
    FROM cust
)
SELECT
    decile * 10                                              AS top_customer_pct,
    COUNT(*)                                                 AS customers,
    ROUND(SUM(revenue), 0)                                   AS revenue,
    ROUND(100.0 * MAX(cum_revenue) / MAX(total_revenue), 1)  AS cumulative_revenue_pct
FROM ranked
GROUP BY decile
ORDER BY decile;

-- name: cohort_retention
-- Monthly cohorts by first-order month: % of the cohort that orders again N months later.
WITH first_order AS (
    SELECT customer_id, MIN(order_month) AS cohort_month
    FROM sales_fact WHERE status = 'Delivered'
    GROUP BY customer_id
),
activity AS (
    SELECT DISTINCT f.customer_id, f.cohort_month, s.order_month,
        (CAST(SUBSTR(s.order_month, 1, 4) AS INT) - CAST(SUBSTR(f.cohort_month, 1, 4) AS INT)) * 12
        + (CAST(SUBSTR(s.order_month, 6, 2) AS INT) - CAST(SUBSTR(f.cohort_month, 6, 2) AS INT)) AS months_since
    FROM first_order f
    JOIN sales_fact s ON s.customer_id = f.customer_id AND s.status = 'Delivered'
),
sizes AS (SELECT cohort_month, COUNT(*) AS cohort_size FROM first_order GROUP BY cohort_month)
SELECT
    a.cohort_month,
    sz.cohort_size,
    a.months_since,
    COUNT(DISTINCT a.customer_id)                                       AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT a.customer_id) / sz.cohort_size, 1)    AS retention_pct
FROM activity a
JOIN sizes sz USING (cohort_month)
WHERE a.months_since BETWEEN 0 AND 6
GROUP BY a.cohort_month, a.months_since
ORDER BY a.cohort_month, a.months_since;

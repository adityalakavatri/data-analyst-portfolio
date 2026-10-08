-- =====================================================================
-- 01_cleaning.sql  |  SQLite dialect
-- Turns raw_* tables (loaded from data/raw/*.csv) into analysis-ready tables.
-- Issues fixed: duplicate orders, missing ship_mode, inconsistent text case,
--               trailing spaces in city names.
-- =====================================================================

DROP TABLE IF EXISTS customers_clean;
CREATE TABLE customers_clean AS
SELECT
    customer_id,
    customer_name,
    -- cities are single words, so UPPER(first letter) + LOWER(rest) is a safe proper-case
    UPPER(SUBSTR(TRIM(city), 1, 1)) || LOWER(SUBSTR(TRIM(city), 2)) AS city,
    state,
    region,
    segment,
    DATE(signup_date) AS signup_date
FROM raw_customers;

DROP TABLE IF EXISTS products_clean;
CREATE TABLE products_clean AS
SELECT product_id, category, sub_category, product_name, unit_cost, unit_price
FROM raw_products;

-- DISTINCT removes the exact duplicate rows that were injected into the export.
DROP TABLE IF EXISTS orders_clean;
CREATE TABLE orders_clean AS
SELECT DISTINCT
    order_id,
    customer_id,
    DATE(order_date)                                              AS order_date,
    COALESCE(NULLIF(TRIM(ship_mode), ''), 'Unknown')              AS ship_mode,
    discount_pct,
    UPPER(SUBSTR(TRIM(status), 1, 1)) || LOWER(SUBSTR(TRIM(status), 2)) AS status
FROM raw_orders;

DROP TABLE IF EXISTS order_items_clean;
CREATE TABLE order_items_clean AS
SELECT order_id, product_id, quantity FROM raw_order_items;

-- ---------------------------------------------------------------------
-- Integrity checks (each should return 0)
-- ---------------------------------------------------------------------
-- SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM orders_clean;
-- SELECT COUNT(*) FROM order_items_clean i LEFT JOIN orders_clean o USING(order_id) WHERE o.order_id IS NULL;

-- ---------------------------------------------------------------------
-- One denormalised fact table that every analysis query reads from.
-- Revenue/profit are counted for Delivered orders only; Returned and
-- Cancelled orders are kept in the table so return rate can be measured.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS sales_fact;
CREATE TABLE sales_fact AS
SELECT
    o.order_id,
    o.order_date,
    STRFTIME('%Y-%m', o.order_date)                               AS order_month,
    o.status,
    o.ship_mode,
    o.discount_pct,
    c.customer_id,
    c.city,
    c.state,
    c.region,
    c.segment,
    c.signup_date,
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    i.quantity,
    ROUND(i.quantity * p.unit_price * (1 - o.discount_pct / 100.0), 2) AS revenue,
    ROUND(i.quantity * p.unit_cost, 2)                                 AS cost,
    ROUND(i.quantity * p.unit_price * (1 - o.discount_pct / 100.0)
          - i.quantity * p.unit_cost, 2)                               AS profit
FROM order_items_clean i
JOIN orders_clean    o USING (order_id)
JOIN customers_clean c USING (customer_id)
JOIN products_clean  p USING (product_id);

CREATE INDEX IF NOT EXISTS idx_fact_month ON sales_fact(order_month);
CREATE INDEX IF NOT EXISTS idx_fact_cust  ON sales_fact(customer_id);

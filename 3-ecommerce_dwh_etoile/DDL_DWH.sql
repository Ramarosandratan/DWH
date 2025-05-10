-- 1. Schéma DWH
CREATE SCHEMA IF NOT EXISTS ecommerce_dwh_star;
SET search_path = ecommerce_dwh_star;

-- 2. Dimension Date
DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date
(
    date_key        INT, -- YYYYMMDD
    day             INT,
    month           INT,
    quarter         INT,
    year            INT,
    day_of_week     VARCHAR(10),
    day_of_week_num INT  -- 1 (lundi) … 7 (dimanche) ISO 8601
);

-- 3. Dimension Time
DROP TABLE IF EXISTS dim_time;
CREATE TABLE dim_time
(
    time_key INT, -- HHMMSS
    hour     INT,
    minute   INT,
    second   INT,
    am_pm    VARCHAR(2)
);

-- 4. Dimension Product (inchangée)
CREATE TABLE dim_product
(
    product_key   INT,
    product_id    INT,
    product_name  TEXT,
    category_id   INT,
    category_name TEXT,
    price         NUMERIC(10, 2)
);

-- 5. Dimension Customer (inchangée)
CREATE TABLE dim_customer
(
    customer_key INT,
    client_id    INT,
    full_name    TEXT,
    email        TEXT,
    signup_date  DATE
);

-- 6. Dimension Payment Method (inchangée)
CREATE TABLE dim_payment_method
(
    payment_method_key INT,
    method             VARCHAR(50)
);

-- 7. Table de faits : date_key et time_key en INT
CREATE TABLE fact_sales
(
    sale_key           INT,
    sale_id            INT,
    date_key           INT, -- devient INT
    time_key           INT, -- devient INT
    product_key        INT,
    customer_key       INT,
    quantity           INT,
    total_amount       NUMERIC(10, 2),
    payment_method_key INT
);

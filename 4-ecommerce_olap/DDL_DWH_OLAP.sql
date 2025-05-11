-- 1. Schéma cible
CREATE SCHEMA IF NOT EXISTS ecommerce_dwh;
SET search_path = ecommerce_dwh;

-- 2. Dimension Date
CREATE TABLE IF NOT EXISTS dim_date (
    date_key    DATE        PRIMARY KEY,
    day         SMALLINT    NOT NULL,
    month       SMALLINT    NOT NULL,
    quarter     SMALLINT    NOT NULL,
    year        SMALLINT    NOT NULL,
    day_of_week VARCHAR(10) NOT NULL
);

-- 3. Dimension Time
CREATE TABLE IF NOT EXISTS dim_time (
    time_key TIME        PRIMARY KEY,
    hour     SMALLINT    NOT NULL,
    minute   SMALLINT    NOT NULL,
    second   SMALLINT    NOT NULL,
    am_pm    VARCHAR(2)  NOT NULL
);

-- 4. Dimension Product
CREATE TABLE IF NOT EXISTS dim_product (
    product_key   SERIAL    PRIMARY KEY,
    product_id    INT        NOT NULL UNIQUE,
    product_name  TEXT       NOT NULL,
    category_id   INT        NOT NULL,
    category_name TEXT       NOT NULL,
    price         NUMERIC(10,2) NOT NULL
);

-- 5. Dimension Customer
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key SERIAL    PRIMARY KEY,
    client_id    INT       NOT NULL UNIQUE,
    full_name    TEXT      NOT NULL,
    email        TEXT      NOT NULL,
    signup_date  DATE      NOT NULL
);

-- 6. Dimension Payment Method
CREATE TABLE IF NOT EXISTS dim_payment_method (
    payment_method_key SERIAL     PRIMARY KEY,
    method             VARCHAR(50) UNIQUE NOT NULL
);

-- 7. Table de faits
CREATE TABLE IF NOT EXISTS fact_sales (
    sale_key           SERIAL     PRIMARY KEY,
    sale_id            INT        NOT NULL UNIQUE,
    date_key           DATE       NOT NULL REFERENCES dim_date(date_key),
    time_key           TIME       NOT NULL REFERENCES dim_time(time_key),
    product_key        INT        NOT NULL REFERENCES dim_product(product_key),
    customer_key       INT        NOT NULL REFERENCES dim_customer(customer_key),
    quantity           INT        NOT NULL,
    total_amount       NUMERIC(10,2) NOT NULL,
    payment_method_key INT        NOT NULL REFERENCES dim_payment_method(payment_method_key)
);

-- Index sur les clés de jointure dans la table de faits
CREATE INDEX IF NOT EXISTS idx_fact_date_key ON fact_sales(date_key);      -- dimension date :contentReference[oaicite:2]{index=2}
CREATE INDEX IF NOT EXISTS idx_fact_time_key ON fact_sales(time_key);      -- dimension time :contentReference[oaicite:3]{index=3}
CREATE INDEX IF NOT EXISTS idx_fact_product_key ON fact_sales(product_key);-- dimension product :contentReference[oaicite:4]{index=4}
CREATE INDEX IF NOT EXISTS idx_fact_customer_key ON fact_sales(customer_key);-- dimension customer :contentReference[oaicite:5]{index=5}
CREATE INDEX IF NOT EXISTS idx_fact_pm_key ON fact_sales(payment_method_key);-- dimension payment method :contentReference[oaicite:6]{index=6}

-- Index multi‑colonnes pour requêtes analytiques fréquent (ex. date + product)
CREATE INDEX IF NOT EXISTS idx_fact_date_product ON fact_sales(date_key, product_key);



/*

-- BRIDGE
-- 1) Dimension Promotion
CREATE TABLE dwh_star.dim_promotion
(
    promotion_key  SERIAL PRIMARY KEY,
    promotion_id   INT UNIQUE NOT NULL,
    promotion_name TEXT       NOT NULL,
    start_date     DATE       NOT NULL,
    end_date       DATE
);

-- Bridge table Product ↔ Promotion
CREATE TABLE dwh_star.bridge_product_promotion
(
    product_key    INT NOT NULL  -- FK vers dim_product.product_key
        REFERENCES dwh_star.dim_product (product_key),
    promotion_key  INT NOT NULL  -- FK vers dim_promotion.promotion_key
        REFERENCES dwh_star.dim_promotion (promotion_key),
    allocation_pct NUMERIC(5, 2) -- ex. % d’allocation de la promo
    ,
    PRIMARY KEY (product_key, promotion_key)
);



-- PRODUCT MINI DIMENSION
-- 1. Mini-dimension pour l’historique des prix produits
CREATE TABLE dwh_star.mini_dim_product_price
(
    price_key    SERIAL PRIMARY KEY,                  -- clé substitut de la mini-dimension
    product_key  INT            NOT NULL,             -- FK vers dim_product.product_key
    price        NUMERIC(10, 2) NOT NULL,             -- valeur du prix
    price_tier   VARCHAR(20)    NOT NULL,             -- ex. 'Low', 'Medium', 'High'
    start_date   DATE           NOT NULL,             -- début de validité de ce prix
    end_date     DATE           NULL,                 -- fin de validité (NULL = en vigueur)
    current_flag BOOLEAN        NOT NULL DEFAULT TRUE -- indicateur de l’enregistrement actif
);

-- 2. Exemple de population initiale (à lancer après remplissage de dim_product)

INSERT INTO dwh_star.mini_dim_product_price
    (product_key, price, price_tier, start_date, end_date, current_flag)
SELECT product_key,
       price,
       CASE
           WHEN price < 20 THEN 'Low'
           WHEN price < 100 THEN 'Medium'
           ELSE 'High'
           END      AS price_tier,
       CURRENT_DATE AS start_date,
       NULL         AS end_date,
       TRUE         AS current_flag
FROM dwh_star.dim_product;

-- 3. Lors d’un changement de prix pour un product_key donné,
--    il faut « fermer » l’enregistrement existant (end_date + current_flag=false)
--    puis en insérer un nouveau avec current_flag=true.

-- Exemple de procédure de mise à jour d’un prix :
WITH old AS (
    UPDATE dwh_star.mini_dim_product_price
        SET end_date = CURRENT_DATE - INTERVAL '1 day',
            current_flag = FALSE
        WHERE product_key = 42
            AND current_flag = TRUE
        RETURNING *)
INSERT
INTO dwh_star.mini_dim_product_price
    (product_key, price, price_tier, start_date, end_date, current_flag)
VALUES (42,
        49.99,
        CASE
            WHEN 49.99 < 20 THEN 'Low'
            WHEN 49.99 < 100 THEN 'Medium'
            ELSE 'High'
            END,
        CURRENT_DATE,
        NULL,
        TRUE);
*/
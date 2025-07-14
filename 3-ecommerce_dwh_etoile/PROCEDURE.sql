-- Helper function to parse both dd/mm/yyyy HH:MM:SS and yyyy-mm-dd HH24:MI:SS formats
CREATE OR REPLACE FUNCTION ecommerce_dwh_star.parse_datetime(ts_text TEXT)
  RETURNS TIMESTAMP WITHOUT TIME ZONE
  LANGUAGE plpgsql
  IMMUTABLE
AS $$
BEGIN
  ts_text := trim(ts_text);
  IF ts_text ~ '^\d{2}/\d{2}/\d{4}' THEN
    RETURN to_timestamp(ts_text, 'DD/MM/YYYY HH24:MI:SS');
  ELSE
    RETURN to_timestamp(ts_text, 'YYYY-MM-DD HH24:MI:SS');
  END IF;
END;
$$;

-- 2.1 dim_date
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_date()
  LANGUAGE plpgsql AS
$$
BEGIN
  INSERT INTO ecommerce_dwh_star.dim_date
      (date_key, day, month, quarter, year, day_of_week, day_of_week_num)
  SELECT (TO_CHAR(d, 'YYYYMMDD'))::INT AS date_key,
         EXTRACT(DAY FROM d)::INT      AS day,
         EXTRACT(MONTH FROM d)::INT    AS month,
         EXTRACT(QUARTER FROM d)::INT  AS quarter,
         EXTRACT(YEAR FROM d)::INT     AS year,
         TO_CHAR(d, 'FMDay')           AS day_of_week,
         EXTRACT(ISODOW FROM d)::INT   AS day_of_week_num
  FROM (
    SELECT DISTINCT parse_datetime(sale_date_time)::DATE AS d FROM raw.sales_raw
    UNION
    SELECT DISTINCT parse_datetime(created_at)::DATE            FROM raw.clients_raw
    UNION
    SELECT DISTINCT parse_datetime(payment_date)::DATE          FROM raw.payment_history_raw
    UNION
    SELECT DISTINCT parse_datetime(updated_at)::DATE            FROM raw.inventory_raw
  ) src(d)
  WHERE NOT EXISTS (
    SELECT 1
      FROM ecommerce_dwh_star.dim_date tgt
     WHERE tgt.date_key = (TO_CHAR(src.d, 'YYYYMMDD'))::INT
  );
END;
$$;

-- 2.2 dim_time
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_time()
  LANGUAGE plpgsql AS
$$
BEGIN
  INSERT INTO ecommerce_dwh_star.dim_time
      (time_key, hour, minute, second, am_pm)
  SELECT (EXTRACT(HOUR FROM t) * 10000
          + EXTRACT(MINUTE FROM t) * 100
          + EXTRACT(SECOND FROM t))::INT AS time_key,
         EXTRACT(HOUR FROM t)::INT           AS hour,
         EXTRACT(MINUTE FROM t)::INT         AS minute,
         EXTRACT(SECOND FROM t)::INT         AS second,
         CASE WHEN EXTRACT(HOUR FROM t) < 12 THEN 'AM' ELSE 'PM' END AS am_pm
  FROM (
    SELECT DISTINCT parse_datetime(sale_date_time)::TIME AS t FROM raw.sales_raw
    UNION
    SELECT DISTINCT parse_datetime(payment_date)::TIME   FROM raw.payment_history_raw
    UNION
    SELECT DISTINCT parse_datetime(updated_at)::TIME     FROM raw.inventory_raw
    UNION
    SELECT DISTINCT parse_datetime(created_at)::TIME     FROM raw.clients_raw
  ) src(t)
  WHERE NOT EXISTS (
    SELECT 1
      FROM ecommerce_dwh_star.dim_time tgt
     WHERE tgt.time_key = (
       EXTRACT(HOUR FROM src.t) * 10000
       + EXTRACT(MINUTE FROM src.t) * 100
       + EXTRACT(SECOND FROM src.t)
     )::INT
  );
END;
$$;

-- 2.3 dim_customer
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_customer()
  LANGUAGE plpgsql AS
$$
BEGIN
  INSERT INTO ecommerce_dwh_star.dim_customer
      (customer_key, client_id, full_name, email, signup_date)
  SELECT nextval('seq_dim_customer_key')
       , (trim(c.client_id))::INT
       , upper(trim(c.first_name)) || ' ' || upper(trim(c.last_name))
       , upper(trim(c.email))
       , parse_datetime(c.created_at)::DATE
  FROM raw.clients_raw c
  WHERE NOT EXISTS (
    SELECT 1
      FROM ecommerce_dwh_star.dim_customer tgt
     WHERE tgt.client_id = (trim(c.client_id))::INT
  );
END;
$$;

-- 2.4 load_dim_payment_method
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_payment_method()
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO ecommerce_dwh_star.dim_payment_method(payment_method_key, method)
  SELECT
    nextval('seq_dim_payment_method_key'),
    upper(trim(src.method))
  FROM (
    SELECT DISTINCT method
    FROM raw.payment_history_raw
    WHERE method IS NOT NULL
  ) AS src
  WHERE NOT EXISTS (
    SELECT 1
      FROM ecommerce_dwh_star.dim_payment_method tgt
     WHERE tgt.method = upper(trim(src.method))
  );
END;
$$;

-- 2.5 load_dim_product
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_product()
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO ecommerce_dwh_star.dim_product
      (product_key, product_id, product_name, category_id, category_name, price)
  SELECT
    nextval('seq_dim_product_key'),
    (trim(p.product_id))::INT,
    upper(trim(p.name)),
    (trim(p.category_id))::INT,
    upper(trim(c.name)),
    (replace(replace(trim(p.price), ' ', ''), ',', '.'))::NUMERIC(10,2)
  FROM raw.products_raw p
  LEFT JOIN raw.categories_raw c
    ON trim(p.category_id) = trim(c.category_id)
  WHERE NOT EXISTS (
    SELECT 1
      FROM ecommerce_dwh_star.dim_product tgt
     WHERE tgt.product_id = (trim(p.product_id))::INT
  );
END;
$$;



-- 2.6 fact_sales
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_fact_sales()
  LANGUAGE plpgsql AS
$$
BEGIN
  INSERT INTO ecommerce_dwh_star.fact_sales
      (sale_key, sale_id, date_key, time_key, product_key,
       customer_key, quantity, total_amount, payment_method_key)
  SELECT nextval('seq_fact_sales_key')
       , (trim(s.sale_id))::INT
       , (TO_CHAR(parse_datetime(s.sale_date_time)::DATE, 'YYYYMMDD'))::INT AS date_key
       , (EXTRACT(HOUR FROM parse_datetime(s.sale_date_time)::TIME) * 10000
          + EXTRACT(MINUTE FROM parse_datetime(s.sale_date_time)::TIME) * 100
          + EXTRACT(SECOND FROM parse_datetime(s.sale_date_time)::TIME) * 1)::INT AS time_key
       , dp.product_key
       , dc.customer_key
       , (trim(s.quantity))::INT
       , (replace(replace(trim(s.total_amount), ' ', ''), ',', '.'))::NUMERIC(10, 2)
       , pm.payment_method_key
  FROM raw.sales_raw s
  JOIN ecommerce_dwh_star.dim_product dp
    ON dp.product_id = (trim(s.product_id))::INT
  JOIN ecommerce_dwh_star.dim_customer dc
    ON dc.client_id = (trim(s.client_id))::INT
  LEFT JOIN raw.payment_history_raw ph
    ON trim(ph.sale_id) = trim(s.sale_id)
  LEFT JOIN ecommerce_dwh_star.dim_payment_method pm
    ON pm.method = upper(trim(ph.method))
  WHERE NOT EXISTS (
    SELECT 1
      FROM ecommerce_dwh_star.fact_sales tgt
     WHERE tgt.sale_id = (trim(s.sale_id))::INT
  );
END;
$$;

-- 3) Orchestrator (unchanged)
CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.etl_master()
  LANGUAGE plpgsql AS
$$
BEGIN
  CALL ecommerce_dwh_star.load_dim_date();
  CALL ecommerce_dwh_star.load_dim_time();
  CALL ecommerce_dwh_star.load_dim_payment_method();
  CALL ecommerce_dwh_star.load_dim_product();
  CALL ecommerce_dwh_star.load_dim_customer();
  CALL ecommerce_dwh_star.load_fact_sales();
END;
$$;


-- DWH_20250702.
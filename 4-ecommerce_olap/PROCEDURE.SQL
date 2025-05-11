-- 1) Se placer dans le bon schéma
CREATE SCHEMA IF NOT EXISTS ecommerce_dwh;
SET search_path = ecommerce_dwh;

-- 2) Procédure de TRUNCATE ordonné
CREATE OR REPLACE PROCEDURE ecommerce_dwh.truncate_all_tables()
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Faits (référence toutes les dimensions)
    TRUNCATE TABLE fact_sales CASCADE;

    -- 2. Dimensions
    TRUNCATE TABLE ecommerce_dwh.dim_time CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_date CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_product CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_customer CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_payment_method CASCADE;

    COMMIT;

  RAISE NOTICE 'All tables truncated in ecommerce_dwh';
END;
$$;

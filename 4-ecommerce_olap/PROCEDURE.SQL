-- 1) Se placer dans le bon schéma
CREATE SCHEMA IF NOT EXISTS ecommerce_dwh;
SET search_path = ecommerce_dwh;

-- 2) Procédure de TRUNCATE ordonné
CREATE OR REPLACE PROCEDURE ecommerce_dwh.truncate_all_tables()
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Faits (référence toutes les dimensions)
    TRUNCATE TABLE ecommerce_dwh.fact_sales CASCADE;

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


/*******/
-- 1. Faits (référence toutes les dimensions)
    TRUNCATE TABLE ecommerce_dwh.fact_sales
        RESTART IDENTITY
        CASCADE;

    -- 2. Dimensions
    TRUNCATE TABLE ecommerce_dwh.dim_time
        RESTART IDENTITY
        CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_date
        RESTART IDENTITY
        CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_product
        RESTART IDENTITY
        CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_customer
        RESTART IDENTITY
        CASCADE;
    TRUNCATE TABLE ecommerce_dwh.dim_payment_method
        RESTART IDENTITY
        CASCADE;
/*CREATE DATABASE ecommerce_dwh_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'fr_FR.UTF-8'
    LC_CTYPE = 'fr_FR.UTF-8'
    TEMPLATE template0;
*/

CREATE SCHEMA IF NOT EXISTS raw;
SET search_path = raw;


-- Tables RAW (tous les champs en TEXT, pas de PK, pas de FK)
CREATE TABLE categories_raw
(
    category_id TEXT,
    name        TEXT
);

CREATE TABLE products_raw
(
    product_id  TEXT,
    name        TEXT,
    category_id TEXT,
    price       TEXT
);

CREATE TABLE clients_raw
(
    client_id  TEXT,
    first_name TEXT,
    last_name  TEXT,
    email      TEXT,
    created_at TEXT
);

CREATE TABLE sales_raw
(
    sale_id        TEXT,
    client_id      TEXT,
    product_id     TEXT,
    sale_date_time TEXT,
    quantity       TEXT,
    total_amount   TEXT
);

CREATE TABLE inventory_raw
(
    product_id        TEXT,
    stock_quantity    TEXT,
    reorder_threshold TEXT,
    updated_at        TEXT
);

CREATE TABLE payment_history_raw
(
    payment_id   TEXT,
    sale_id      TEXT,
    client_id    TEXT,
    payment_date TEXT,
    amount       TEXT,
    method       TEXT,
    status       TEXT
);

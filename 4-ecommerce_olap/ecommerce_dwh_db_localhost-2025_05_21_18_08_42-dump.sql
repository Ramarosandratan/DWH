--
-- PostgreSQL database dump
--

-- Dumped from database version 16.9 (Postgres.app)
-- Dumped by pg_dump version 16.9 (Postgres.app)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: ecommerce_dwh_db; Type: DATABASE; Schema: -; Owner: nomena
--

CREATE DATABASE ecommerce_dwh_db WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'fr_FR.UTF-8';


ALTER DATABASE ecommerce_dwh_db OWNER TO nomena;

\connect ecommerce_dwh_db

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: ecommerce_dwh; Type: SCHEMA; Schema: -; Owner: nomena
--

CREATE SCHEMA ecommerce_dwh;


ALTER SCHEMA ecommerce_dwh OWNER TO nomena;

--
-- Name: truncate_all_tables(); Type: PROCEDURE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE PROCEDURE ecommerce_dwh.truncate_all_tables()
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


ALTER PROCEDURE ecommerce_dwh.truncate_all_tables() OWNER TO nomena;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: dim_customer; Type: TABLE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE TABLE ecommerce_dwh.dim_customer (
    customer_key integer NOT NULL,
    client_id integer NOT NULL,
    full_name text NOT NULL,
    email text NOT NULL,
    signup_date date NOT NULL
);


ALTER TABLE ecommerce_dwh.dim_customer OWNER TO nomena;

--
-- Name: dim_customer_customer_key_seq; Type: SEQUENCE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE SEQUENCE ecommerce_dwh.dim_customer_customer_key_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE ecommerce_dwh.dim_customer_customer_key_seq OWNER TO nomena;

--
-- Name: dim_customer_customer_key_seq; Type: SEQUENCE OWNED BY; Schema: ecommerce_dwh; Owner: nomena
--

ALTER SEQUENCE ecommerce_dwh.dim_customer_customer_key_seq OWNED BY ecommerce_dwh.dim_customer.customer_key;


--
-- Name: dim_date; Type: TABLE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE TABLE ecommerce_dwh.dim_date (
    date_key date NOT NULL,
    day smallint NOT NULL,
    month smallint NOT NULL,
    quarter smallint NOT NULL,
    year smallint NOT NULL,
    day_of_week character varying(10) NOT NULL
);


ALTER TABLE ecommerce_dwh.dim_date OWNER TO nomena;

--
-- Name: dim_payment_method; Type: TABLE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE TABLE ecommerce_dwh.dim_payment_method (
    payment_method_key integer NOT NULL,
    method character varying(50) NOT NULL
);


ALTER TABLE ecommerce_dwh.dim_payment_method OWNER TO nomena;

--
-- Name: dim_payment_method_payment_method_key_seq; Type: SEQUENCE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE SEQUENCE ecommerce_dwh.dim_payment_method_payment_method_key_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE ecommerce_dwh.dim_payment_method_payment_method_key_seq OWNER TO nomena;

--
-- Name: dim_payment_method_payment_method_key_seq; Type: SEQUENCE OWNED BY; Schema: ecommerce_dwh; Owner: nomena
--

ALTER SEQUENCE ecommerce_dwh.dim_payment_method_payment_method_key_seq OWNED BY ecommerce_dwh.dim_payment_method.payment_method_key;


--
-- Name: dim_product; Type: TABLE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE TABLE ecommerce_dwh.dim_product (
    product_key integer NOT NULL,
    product_id integer NOT NULL,
    product_name text NOT NULL,
    category_id integer NOT NULL,
    category_name text NOT NULL,
    price numeric(10,2) NOT NULL
);


ALTER TABLE ecommerce_dwh.dim_product OWNER TO nomena;

--
-- Name: dim_product_product_key_seq; Type: SEQUENCE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE SEQUENCE ecommerce_dwh.dim_product_product_key_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE ecommerce_dwh.dim_product_product_key_seq OWNER TO nomena;

--
-- Name: dim_product_product_key_seq; Type: SEQUENCE OWNED BY; Schema: ecommerce_dwh; Owner: nomena
--

ALTER SEQUENCE ecommerce_dwh.dim_product_product_key_seq OWNED BY ecommerce_dwh.dim_product.product_key;


--
-- Name: dim_time; Type: TABLE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE TABLE ecommerce_dwh.dim_time (
    time_key time without time zone NOT NULL,
    hour smallint NOT NULL,
    minute smallint NOT NULL,
    second smallint NOT NULL,
    am_pm character varying(2) NOT NULL
);


ALTER TABLE ecommerce_dwh.dim_time OWNER TO nomena;

--
-- Name: fact_sales; Type: TABLE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE TABLE ecommerce_dwh.fact_sales (
    sale_key integer NOT NULL,
    sale_id integer NOT NULL,
    date_key date NOT NULL,
    time_key time without time zone NOT NULL,
    product_key integer NOT NULL,
    customer_key integer NOT NULL,
    quantity integer NOT NULL,
    total_amount numeric(10,2) NOT NULL,
    payment_method_key integer NOT NULL
);


ALTER TABLE ecommerce_dwh.fact_sales OWNER TO nomena;

--
-- Name: fact_sales_sale_key_seq; Type: SEQUENCE; Schema: ecommerce_dwh; Owner: nomena
--

CREATE SEQUENCE ecommerce_dwh.fact_sales_sale_key_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE ecommerce_dwh.fact_sales_sale_key_seq OWNER TO nomena;

--
-- Name: fact_sales_sale_key_seq; Type: SEQUENCE OWNED BY; Schema: ecommerce_dwh; Owner: nomena
--

ALTER SEQUENCE ecommerce_dwh.fact_sales_sale_key_seq OWNED BY ecommerce_dwh.fact_sales.sale_key;


--
-- Name: dim_customer customer_key; Type: DEFAULT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_customer ALTER COLUMN customer_key SET DEFAULT nextval('ecommerce_dwh.dim_customer_customer_key_seq'::regclass);


--
-- Name: dim_payment_method payment_method_key; Type: DEFAULT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_payment_method ALTER COLUMN payment_method_key SET DEFAULT nextval('ecommerce_dwh.dim_payment_method_payment_method_key_seq'::regclass);


--
-- Name: dim_product product_key; Type: DEFAULT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_product ALTER COLUMN product_key SET DEFAULT nextval('ecommerce_dwh.dim_product_product_key_seq'::regclass);


--
-- Name: fact_sales sale_key; Type: DEFAULT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales ALTER COLUMN sale_key SET DEFAULT nextval('ecommerce_dwh.fact_sales_sale_key_seq'::regclass);


--
-- Data for Name: dim_customer; Type: TABLE DATA; Schema: ecommerce_dwh; Owner: nomena
--

INSERT INTO ecommerce_dwh.dim_customer (customer_key, client_id, full_name, email, signup_date) VALUES (49, 1, 'ALICE DUPONT', 'ALICE.DUPONT@EXAMPLE.COM', '2025-04-26');
INSERT INTO ecommerce_dwh.dim_customer (customer_key, client_id, full_name, email, signup_date) VALUES (50, 2, 'BOB MARTIN', 'BOB.MARTIN@EXAMPLE.COM', '2025-04-26');
INSERT INTO ecommerce_dwh.dim_customer (customer_key, client_id, full_name, email, signup_date) VALUES (51, 3, 'CLAIRE RENAULT', 'CLAIRE.RENAULT@EXAMPLE.COM', '2025-04-26');
INSERT INTO ecommerce_dwh.dim_customer (customer_key, client_id, full_name, email, signup_date) VALUES (52, 4, 'DAVID PETIT', 'DAVID.PETIT@EXAMPLE.COM', '2025-04-26');
INSERT INTO ecommerce_dwh.dim_customer (customer_key, client_id, full_name, email, signup_date) VALUES (53, 5, 'ÉMILIE DURAND', 'EMILIE.DURAND@EXAMPLE.COM', '2025-04-26');
INSERT INTO ecommerce_dwh.dim_customer (customer_key, client_id, full_name, email, signup_date) VALUES (54, 6, 'FABRICE LEMOINE', 'FABRICE.LEMOINE@EXAMPLE.COM', '2025-04-26');


--
-- Data for Name: dim_date; Type: TABLE DATA; Schema: ecommerce_dwh; Owner: nomena
--

INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-03', 3, 4, 2, 2025, 'Thursday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-26', 26, 4, 2, 2025, 'Saturday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-05', 5, 4, 2, 2025, 'Saturday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-06', 6, 4, 2, 2025, 'Sunday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-04', 4, 4, 2, 2025, 'Friday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-02', 2, 4, 2, 2025, 'Wednesday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-10', 10, 4, 2, 2025, 'Thursday');
INSERT INTO ecommerce_dwh.dim_date (date_key, day, month, quarter, year, day_of_week) VALUES ('2025-04-01', 1, 4, 2, 2025, 'Tuesday');


--
-- Data for Name: dim_payment_method; Type: TABLE DATA; Schema: ecommerce_dwh; Owner: nomena
--

INSERT INTO ecommerce_dwh.dim_payment_method (payment_method_key, method) VALUES (25, 'BANK_TRANSFER');
INSERT INTO ecommerce_dwh.dim_payment_method (payment_method_key, method) VALUES (26, 'CREDIT_CARD');
INSERT INTO ecommerce_dwh.dim_payment_method (payment_method_key, method) VALUES (27, 'PAYPAL');


--
-- Data for Name: dim_product; Type: TABLE DATA; Schema: ecommerce_dwh; Owner: nomena
--

INSERT INTO ecommerce_dwh.dim_product (product_key, product_id, product_name, category_id, category_name, price) VALUES (49, 1, 'T-SHIRT', 1, 'VÊTEMENTS', 19.99);
INSERT INTO ecommerce_dwh.dim_product (product_key, product_id, product_name, category_id, category_name, price) VALUES (50, 3, 'JEAN', 1, 'VÊTEMENTS', 49.99);
INSERT INTO ecommerce_dwh.dim_product (product_key, product_id, product_name, category_id, category_name, price) VALUES (51, 2, 'CASQUETTE', 2, 'ACCESSOIRES', 15.00);
INSERT INTO ecommerce_dwh.dim_product (product_key, product_id, product_name, category_id, category_name, price) VALUES (52, 5, 'SAC À DOS', 2, 'ACCESSOIRES', 35.00);
INSERT INTO ecommerce_dwh.dim_product (product_key, product_id, product_name, category_id, category_name, price) VALUES (53, 6, 'MONTRE', 2, 'ACCESSOIRES', 120.00);
INSERT INTO ecommerce_dwh.dim_product (product_key, product_id, product_name, category_id, category_name, price) VALUES (54, 4, 'CHAUSSURES', 3, 'CHAUSSURES', 79.90);


--
-- Data for Name: dim_time; Type: TABLE DATA; Schema: ecommerce_dwh; Owner: nomena
--

INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('08:15:00', 8, 15, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('08:25:00', 8, 25, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('15:35:00', 15, 35, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('08:10:00', 8, 10, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('11:30:00', 11, 30, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('13:05:00', 13, 5, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('13:00:00', 13, 0, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('17:10:00', 17, 10, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('12:05:00', 12, 5, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('09:45:00', 9, 45, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('15:30:00', 15, 30, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('11:35:00', 11, 35, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('17:15:00', 17, 15, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('14:20:00', 14, 20, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('10:50:00', 10, 50, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('10:00:00', 10, 0, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('10:05:00', 10, 5, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('09:50:00', 9, 50, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('16:20:00', 16, 20, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('12:00:00', 12, 0, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('07:43:45', 7, 43, 45, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('14:15:00', 14, 15, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('08:00:00', 8, 0, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('16:25:00', 16, 25, 0, 'PM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('08:05:00', 8, 5, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('08:20:00', 8, 20, 0, 'AM');
INSERT INTO ecommerce_dwh.dim_time (time_key, hour, minute, second, am_pm) VALUES ('10:55:00', 10, 55, 0, 'AM');


--
-- Data for Name: fact_sales; Type: TABLE DATA; Schema: ecommerce_dwh; Owner: nomena
--

INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (102, 1, '2025-04-01', '10:00:00', 49, 49, 2, 39.98, 26);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (103, 10, '2025-04-06', '10:50:00', 54, 52, 1, 79.90, 27);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (104, 2, '2025-04-02', '11:30:00', 51, 50, 1, 15.00, 27);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (105, 3, '2025-04-02', '14:15:00', 50, 51, 1, 49.99, 26);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (106, 4, '2025-04-03', '09:45:00', 54, 49, 1, 79.90, 25);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (107, 5, '2025-04-03', '16:20:00', 49, 52, 3, 59.97, 26);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (108, 6, '2025-04-04', '13:00:00', 52, 53, 1, 35.00, 27);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (109, 7, '2025-04-04', '17:10:00', 50, 50, 2, 99.98, 26);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (110, 8, '2025-04-05', '12:00:00', 53, 54, 1, 120.00, 25);
INSERT INTO ecommerce_dwh.fact_sales (sale_key, sale_id, date_key, time_key, product_key, customer_key, quantity, total_amount, payment_method_key) VALUES (111, 9, '2025-04-05', '15:30:00', 51, 51, 2, 30.00, 26);


--
-- Name: dim_customer_customer_key_seq; Type: SEQUENCE SET; Schema: ecommerce_dwh; Owner: nomena
--

SELECT pg_catalog.setval('ecommerce_dwh.dim_customer_customer_key_seq', 1, false);


--
-- Name: dim_payment_method_payment_method_key_seq; Type: SEQUENCE SET; Schema: ecommerce_dwh; Owner: nomena
--

SELECT pg_catalog.setval('ecommerce_dwh.dim_payment_method_payment_method_key_seq', 1, false);


--
-- Name: dim_product_product_key_seq; Type: SEQUENCE SET; Schema: ecommerce_dwh; Owner: nomena
--

SELECT pg_catalog.setval('ecommerce_dwh.dim_product_product_key_seq', 1, false);


--
-- Name: fact_sales_sale_key_seq; Type: SEQUENCE SET; Schema: ecommerce_dwh; Owner: nomena
--

SELECT pg_catalog.setval('ecommerce_dwh.fact_sales_sale_key_seq', 1, false);


--
-- Name: dim_customer dim_customer_client_id_key; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_customer
    ADD CONSTRAINT dim_customer_client_id_key UNIQUE (client_id);


--
-- Name: dim_customer dim_customer_pkey; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_customer
    ADD CONSTRAINT dim_customer_pkey PRIMARY KEY (customer_key);


--
-- Name: dim_date dim_date_pkey; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_date
    ADD CONSTRAINT dim_date_pkey PRIMARY KEY (date_key);


--
-- Name: dim_payment_method dim_payment_method_method_key; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_payment_method
    ADD CONSTRAINT dim_payment_method_method_key UNIQUE (method);


--
-- Name: dim_payment_method dim_payment_method_pkey; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_payment_method
    ADD CONSTRAINT dim_payment_method_pkey PRIMARY KEY (payment_method_key);


--
-- Name: dim_product dim_product_pkey; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_product
    ADD CONSTRAINT dim_product_pkey PRIMARY KEY (product_key);


--
-- Name: dim_product dim_product_product_id_key; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_product
    ADD CONSTRAINT dim_product_product_id_key UNIQUE (product_id);


--
-- Name: dim_time dim_time_pkey; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.dim_time
    ADD CONSTRAINT dim_time_pkey PRIMARY KEY (time_key);


--
-- Name: fact_sales fact_sales_pkey; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_pkey PRIMARY KEY (sale_key);


--
-- Name: fact_sales fact_sales_sale_id_key; Type: CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_sale_id_key UNIQUE (sale_id);


--
-- Name: idx_fact_customer_key; Type: INDEX; Schema: ecommerce_dwh; Owner: nomena
--

CREATE INDEX idx_fact_customer_key ON ecommerce_dwh.fact_sales USING btree (customer_key);


--
-- Name: idx_fact_date_key; Type: INDEX; Schema: ecommerce_dwh; Owner: nomena
--

CREATE INDEX idx_fact_date_key ON ecommerce_dwh.fact_sales USING btree (date_key);


--
-- Name: idx_fact_date_product; Type: INDEX; Schema: ecommerce_dwh; Owner: nomena
--

CREATE INDEX idx_fact_date_product ON ecommerce_dwh.fact_sales USING btree (date_key, product_key);


--
-- Name: idx_fact_pm_key; Type: INDEX; Schema: ecommerce_dwh; Owner: nomena
--

CREATE INDEX idx_fact_pm_key ON ecommerce_dwh.fact_sales USING btree (payment_method_key);


--
-- Name: idx_fact_product_key; Type: INDEX; Schema: ecommerce_dwh; Owner: nomena
--

CREATE INDEX idx_fact_product_key ON ecommerce_dwh.fact_sales USING btree (product_key);


--
-- Name: idx_fact_time_key; Type: INDEX; Schema: ecommerce_dwh; Owner: nomena
--

CREATE INDEX idx_fact_time_key ON ecommerce_dwh.fact_sales USING btree (time_key);


--
-- Name: fact_sales fact_sales_customer_key_fkey; Type: FK CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_customer_key_fkey FOREIGN KEY (customer_key) REFERENCES ecommerce_dwh.dim_customer(customer_key);


--
-- Name: fact_sales fact_sales_date_key_fkey; Type: FK CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_date_key_fkey FOREIGN KEY (date_key) REFERENCES ecommerce_dwh.dim_date(date_key);


--
-- Name: fact_sales fact_sales_payment_method_key_fkey; Type: FK CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_payment_method_key_fkey FOREIGN KEY (payment_method_key) REFERENCES ecommerce_dwh.dim_payment_method(payment_method_key);


--
-- Name: fact_sales fact_sales_product_key_fkey; Type: FK CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_product_key_fkey FOREIGN KEY (product_key) REFERENCES ecommerce_dwh.dim_product(product_key);


--
-- Name: fact_sales fact_sales_time_key_fkey; Type: FK CONSTRAINT; Schema: ecommerce_dwh; Owner: nomena
--

ALTER TABLE ONLY ecommerce_dwh.fact_sales
    ADD CONSTRAINT fact_sales_time_key_fkey FOREIGN KEY (time_key) REFERENCES ecommerce_dwh.dim_time(time_key);


--
-- PostgreSQL database dump complete
--


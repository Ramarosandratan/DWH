-- 1. Base de données
CREATE DATABASE IF NOT EXISTS ecommerce_ops_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecommerce_ops_db;

-- 2. Table des catégories de produits
CREATE TABLE categories
(
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL
);

-- 3. Table des produits
CREATE TABLE products
(
    product_id  INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)   NOT NULL,
    category_id INT            NOT NULL,
    price       DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

-- 4. Table des clients
CREATE TABLE clients
(
    client_id  INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50)         NOT NULL,
    last_name  VARCHAR(50)         NOT NULL,
    email      VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table des ventes
CREATE TABLE sales
(
    sale_id        INT AUTO_INCREMENT PRIMARY KEY,
    client_id      INT            NOT NULL,
    product_id     INT            NOT NULL,
    sale_date_time DATETIME       NOT NULL,
    quantity       INT            NOT NULL,
    total_amount   DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients (client_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

-- 6. Table de gestion des stocks
CREATE TABLE inventory
(
    product_id        INT      NOT NULL,
    stock_quantity    INT      NOT NULL DEFAULT 0,
    reorder_threshold INT      NOT NULL DEFAULT 10,
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

-- 7. Table de gestion des paiements
CREATE TABLE payment_history
(
    payment_id   INT PRIMARY KEY,
    sale_id      INT            NOT NULL,
    client_id    INT            NOT NULL,
    payment_date DATETIME       NOT NULL,
    amount       DECIMAL(10, 2) NOT NULL,
    method       VARCHAR(50)    NOT NULL,
    status       VARCHAR(20)    NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales (sale_id),
    FOREIGN KEY (client_id) REFERENCES clients (client_id)
);

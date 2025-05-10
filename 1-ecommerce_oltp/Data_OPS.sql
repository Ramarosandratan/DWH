-- Insertion de catégories
INSERT INTO categories (name)
VALUES ('Vêtements'),
       ('Accessoires'),
       ('Chaussures');

-- Insertion de produits
INSERT INTO products (name, category_id, price)
VALUES ('T-shirt', 1, 19.99),
       ('Casquette', 2, 15.00),
       ('Jean', 1, 49.99),
       ('Chaussures', 3, 79.90),
       ('Sac à dos', 2, 35.00),
       ('Montre', 2, 120.00);

-- Insertion de clients
INSERT INTO clients (first_name, last_name, email)
VALUES ('Alice', 'Dupont', 'alice.dupont@example.com'),
       ('Bob', 'Martin', 'bob.martin@example.com'),
       ('Claire', 'Renault', 'claire.renault@example.com'),
       ('David', 'Petit', 'david.petit@example.com'),
       ('Émilie', 'Durand', 'emilie.durand@example.com'),
       ('Fabrice', 'Lemoine', 'fabrice.lemoine@example.com');

-- Insertion de ventes
INSERT INTO sales (client_id, product_id, sale_date_time, quantity, total_amount)
VALUES (1, 1, '2025-04-01 10:00:00', 2, 39.98),
       (2, 2, '2025-04-02 11:30:00', 1, 15.00),
       (3, 3, '2025-04-02 14:15:00', 1, 49.99),
       (1, 4, '2025-04-03 09:45:00', 1, 79.90),
       (4, 1, '2025-04-03 16:20:00', 3, 59.97),
       (5, 5, '2025-04-04 13:00:00', 1, 35.00),
       (2, 3, '2025-04-04 17:10:00', 2, 99.98),
       (6, 6, '2025-04-05 12:00:00', 1, 120.00),
       (3, 2, '2025-04-05 15:30:00', 2, 30.00),
       (4, 4, '2025-04-06 10:50:00', 1, 79.90);


INSERT INTO inventory (product_id, stock_quantity, reorder_threshold, updated_at)
VALUES (1, 100, 20, '2025-04-10 08:00:00'),
       (2, 50, 10, '2025-04-10 08:05:00'),
       (3, 200, 30, '2025-04-10 08:10:00'),
       (4, 75, 15, '2025-04-10 08:15:00'),
       (5, 40, 10, '2025-04-10 08:20:00'),
       (6, 150, 25, '2025-04-10 08:25:00');


insert into payment_history (payment_id, sale_id, client_id, payment_date, amount, method, status)
values  ('1', '1', '1', '2025-04-01 10:05:00', '39.98', 'credit_card', 'completed'),
        ('2', '2', '2', '2025-04-02 11:35:00', '15.00', 'paypal', 'completed'),
        ('3', '3', '3', '2025-04-02 14:20:00', '49.99', 'credit_card', 'completed'),
        ('4', '4', '1', '2025-04-03 09:50:00', '79.90', 'bank_transfer', 'pending'),
        ('5', '5', '4', '2025-04-03 16:25:00', '59.97', 'credit_card', 'completed'),
        ('6', '6', '5', '2025-04-04 13:05:00', '35.00', 'paypal', 'completed'),
        ('7', '7', '2', '2025-04-04 17:15:00', '99.98', 'credit_card', 'failed'),
        ('8', '8', '6', '2025-04-05 12:05:00', '120.00', 'bank_transfer', 'completed'),
        ('9', '9', '3', '2025-04-05 15:35:00', '30.00', 'credit_card', 'completed'),
        ('10', '10', '4', '2025-04-06 10:55:00', '79.90', 'paypal', 'completed');
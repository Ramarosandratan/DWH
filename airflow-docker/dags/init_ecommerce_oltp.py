from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import logging

# Configuration des tables et données
DDL_STATEMENTS = {
    'create_database': """
        CREATE DATABASE IF NOT EXISTS ecommerce_ops_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """,
    'use_database': "USE ecommerce_ops_db;",
    'categories': """
        CREATE TABLE IF NOT EXISTS categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        );
    """,
    'products': """
        CREATE TABLE IF NOT EXISTS products (
            product_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            category_id INT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories (category_id)
        );
    """,
    'clients': """
        CREATE TABLE IF NOT EXISTS clients (
            client_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """,
    'sales': """
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INT AUTO_INCREMENT PRIMARY KEY,
            client_id INT NOT NULL,
            product_id INT NOT NULL,
            sale_date_time DATETIME NOT NULL,
            quantity INT NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients (client_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        );
    """,
    'inventory': """
        CREATE TABLE IF NOT EXISTS inventory (
            product_id INT NOT NULL,
            stock_quantity INT NOT NULL DEFAULT 0,
            reorder_threshold INT NOT NULL DEFAULT 10,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (product_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        );
    """,
    'payment_history': """
        CREATE TABLE IF NOT EXISTS payment_history (
            payment_id INT PRIMARY KEY,
            sale_id INT NOT NULL,
            client_id INT NOT NULL,
            payment_date DATETIME NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            method VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales (sale_id),
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        );
    """
}

DATA_STATEMENTS = {
    'categories': """
        INSERT IGNORE INTO categories (name) VALUES 
        ('Vêtements'),
        ('Accessoires'),
        ('Chaussures');
    """,
    'products': """
        INSERT IGNORE INTO products (name, category_id, price) VALUES 
        ('T-shirt', 1, 19.99),
        ('Casquette', 2, 15.00),
        ('Jean', 1, 49.99),
        ('Chaussures', 3, 79.90),
        ('Sac à dos', 2, 35.00),
        ('Montre', 2, 120.00);
    """,
    'clients': """
        INSERT IGNORE INTO clients (first_name, last_name, email) VALUES 
        ('Alice', 'Dupont', 'alice.dupont@example.com'),
        ('Bob', 'Martin', 'bob.martin@example.com'),
        ('Claire', 'Renault', 'claire.renault@example.com'),
        ('David', 'Petit', 'david.petit@example.com'),
        ('Émilie', 'Durand', 'emilie.durand@example.com'),
        ('Fabrice', 'Lemoine', 'fabrice.lemoine@example.com');
    """,
    'sales': """
        INSERT IGNORE INTO sales (client_id, product_id, sale_date_time, quantity, total_amount) VALUES 
        (1, 1, '2025-04-01 10:00:00', 2, 39.98),
        (2, 2, '2025-04-02 11:30:00', 1, 15.00),
        (3, 3, '2025-04-02 14:15:00', 1, 49.99),
        (1, 4, '2025-04-03 09:45:00', 1, 79.90),
        (4, 1, '2025-04-03 16:20:00', 3, 59.97),
        (5, 5, '2025-04-04 13:00:00', 1, 35.00),
        (2, 3, '2025-04-04 17:10:00', 2, 99.98),
        (6, 6, '2025-04-05 12:00:00', 1, 120.00),
        (3, 2, '2025-04-05 15:30:00', 2, 30.00),
        (4, 4, '2025-04-06 10:50:00', 1, 79.90);
    """,
    'inventory': """
        INSERT IGNORE INTO inventory (product_id, stock_quantity, reorder_threshold, updated_at) VALUES 
        (1, 100, 20, '2025-04-10 08:00:00'),
        (2, 50, 10, '2025-04-10 08:05:00'),
        (3, 200, 30, '2025-04-10 08:10:00'),
        (4, 75, 15, '2025-04-10 08:15:00'),
        (5, 40, 10, '2025-04-10 08:20:00'),
        (6, 150, 25, '2025-04-10 08:25:00');
    """,
    'payment_history': """
        INSERT IGNORE INTO payment_history (payment_id, sale_id, client_id, payment_date, amount, method, status) VALUES 
        (1, 1, 1, '2025-04-01 10:05:00', 39.98, 'credit_card', 'completed'),
        (2, 2, 2, '2025-04-02 11:35:00', 15.00, 'paypal', 'completed'),
        (3, 3, 3, '2025-04-02 14:20:00', 49.99, 'credit_card', 'completed'),
        (4, 4, 1, '2025-04-03 09:50:00', 79.90, 'bank_transfer', 'pending'),
        (5, 5, 4, '2025-04-03 16:25:00', 59.97, 'credit_card', 'completed'),
        (6, 6, 5, '2025-04-04 13:05:00', 35.00, 'paypal', 'completed'),
        (7, 7, 2, '2025-04-04 17:15:00', 99.98, 'credit_card', 'failed'),
        (8, 8, 6, '2025-04-05 12:05:00', 120.00, 'bank_transfer', 'completed'),
        (9, 9, 3, '2025-04-05 15:35:00', 30.00, 'credit_card', 'completed'),
        (10, 10, 4, '2025-04-06 10:55:00', 79.90, 'paypal', 'completed');
    """
}


def create_database():
    """Créer la base de données"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    try:
        mysql_hook.run(DDL_STATEMENTS['create_database'])
        logging.info("Base de données créée avec succès")
    except Exception as e:
        logging.error(f"Erreur lors de la création de la base de données: {e}")
        raise


def create_table(table_name):
    """Créer une table spécifique"""
    def _create():
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
        try:
            mysql_hook.run(DDL_STATEMENTS['use_database'])
            mysql_hook.run(DDL_STATEMENTS[table_name])
            logging.info(f"Table {table_name} créée avec succès")
        except Exception as e:
            logging.error(f"Erreur lors de la création de la table {table_name}: {e}")
            raise
    return _create


def insert_data(table_name):
    """Insérer des données dans une table spécifique"""
    def _insert():
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
        try:
            mysql_hook.run(DDL_STATEMENTS['use_database'])
            mysql_hook.run(DATA_STATEMENTS[table_name])
            logging.info(f"Données insérées dans {table_name} avec succès")
        except Exception as e:
            logging.error(f"Erreur lors de l'insertion des données dans {table_name}: {e}")
            raise
    return _insert


def verify_data():
    """Vérifier que les données ont été correctement insérées"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    try:
        mysql_hook.run(DDL_STATEMENTS['use_database'])
        
        # Vérifier chaque table
        tables = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        for table in tables:
            count = mysql_hook.get_first(f"SELECT COUNT(*) FROM {table}")[0]
            logging.info(f"Table {table}: {count} enregistrements")
            
        logging.info("Vérification des données terminée avec succès")
    except Exception as e:
        logging.error(f"Erreur lors de la vérification des données: {e}")
        raise


# Configuration du DAG
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='init_ecommerce_oltp',
    default_args=default_args,
    description='Initialisation de la base de données e-commerce OLTP',
    schedule=None,  # Exécution manuelle uniquement
    catchup=False,
    tags=['ecommerce', 'oltp', 'initialization'],
) as dag:

    # Tâche de création de la base de données
    create_db_task = PythonOperator(
        task_id='create_database',
        python_callable=create_database,
    )

    # Groupe de tâches pour la création des tables
    with TaskGroup(group_id='create_tables') as create_tables_group:
        table_order = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        
        table_tasks = {}
        for table in table_order:
            table_tasks[table] = PythonOperator(
                task_id=f'create_{table}',
                python_callable=create_table(table),
            )
        
        # Définir les dépendances entre les tables (clés étrangères)
        table_tasks['products'] >> table_tasks['inventory']
        table_tasks['categories'] >> table_tasks['products']
        table_tasks['clients'] >> table_tasks['sales']
        table_tasks['products'] >> table_tasks['sales']
        table_tasks['sales'] >> table_tasks['payment_history']

    # Groupe de tâches pour l'insertion des données
    with TaskGroup(group_id='insert_data') as insert_data_group:
        data_order = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        
        data_tasks = {}
        for table in data_order:
            data_tasks[table] = PythonOperator(
                task_id=f'insert_{table}',
                python_callable=insert_data(table),
            )
        
        # Définir les dépendances pour l'insertion des données
        data_tasks['categories'] >> data_tasks['products']
        data_tasks['products'] >> data_tasks['inventory']
        data_tasks['clients'] >> data_tasks['sales']
        data_tasks['products'] >> data_tasks['sales']
        data_tasks['sales'] >> data_tasks['payment_history']

    # Tâche de vérification finale
    verify_task = PythonOperator(
        task_id='verify_data',
        python_callable=verify_data,
    )

    # Définir les dépendances du DAG
    create_db_task >> create_tables_group >> insert_data_group >> verify_task
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Connection
from airflow.utils.db import provide_session
from datetime import datetime, timedelta
import logging


@provide_session
def create_mysql_connection(session=None):
    """Créer la connexion MySQL pour la base OLTP"""
    conn_id = 'mysql_ops'
    
    # Vérifier si la connexion existe déjà
    existing_conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    
    if existing_conn:
        logging.info(f"Connexion {conn_id} existe déjà, mise à jour...")
        existing_conn.host = 'mysql_ops_db'  # Nom du service Docker
        existing_conn.login = 'root'
        existing_conn.password = 'root_password'
        existing_conn.schema = 'ecommerce_ops_db'
        existing_conn.port = 3306
        existing_conn.conn_type = 'mysql'
    else:
        logging.info(f"Création de la connexion {conn_id}...")
        new_conn = Connection(
            conn_id=conn_id,
            conn_type='mysql',
            host='mysql_ops_db',  # Nom du service Docker
            login='root',
            password='root_password',
            schema='ecommerce_ops_db',
            port=3306
        )
        session.add(new_conn)
    
    session.commit()
    logging.info(f"Connexion MySQL {conn_id} configurée avec succès")


@provide_session
def create_postgres_connection(session=None):
    """Créer la connexion PostgreSQL pour la base RAW"""
    conn_id = 'postgres_raw'
    
    # Vérifier si la connexion existe déjà
    existing_conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    
    if existing_conn:
        logging.info(f"Connexion {conn_id} existe déjà, mise à jour...")
        existing_conn.host = 'postgres_raw_db'  # Nom du service Docker
        existing_conn.login = 'postgres'
        existing_conn.password = 'postgres_password'
        existing_conn.schema = 'ecommerce_raw_db'
        existing_conn.port = 5432
        existing_conn.conn_type = 'postgres'
    else:
        logging.info(f"Création de la connexion {conn_id}...")
        new_conn = Connection(
            conn_id=conn_id,
            conn_type='postgres',
            host='postgres_raw_db',  # Nom du service Docker
            login='postgres',
            password='postgres_password',
            schema='ecommerce_raw_db',
            port=5432
        )
        session.add(new_conn)
    
    session.commit()
    logging.info(f"Connexion PostgreSQL {conn_id} configurée avec succès")


@provide_session
def create_filesystem_connection(session=None):
    """Créer la connexion pour le système de fichiers"""
    conn_id = 'fs_default'
    
    # Vérifier si la connexion existe déjà
    existing_conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    
    if existing_conn:
        logging.info(f"Connexion {conn_id} existe déjà, mise à jour...")
        existing_conn.conn_type = 'fs'
        existing_conn.extra = '{"path": "/opt/airflow/resource"}'
    else:
        logging.info(f"Création de la connexion {conn_id}...")
        new_conn = Connection(
            conn_id=conn_id,
            conn_type='fs',
            extra='{"path": "/opt/airflow/resource"}'
        )
        session.add(new_conn)
    
    session.commit()
    logging.info(f"Connexion filesystem {conn_id} configurée avec succès")


def test_mysql_connection():
    """Tester la connexion MySQL"""
    try:
        from airflow.providers.mysql.hooks.mysql import MySqlHook
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
        result = mysql_hook.get_first("SELECT 1 as test")
        if result and result[0] == 1:
            logging.info("Test de connexion MySQL réussi")
        else:
            raise Exception("Test de connexion MySQL échoué")
    except Exception as e:
        logging.error(f"Erreur lors du test de connexion MySQL: {e}")
        # Ne pas faire échouer le DAG si la base n'est pas encore disponible
        logging.warning("La base MySQL n'est peut-être pas encore disponible")


def test_postgres_connection():
    """Tester la connexion PostgreSQL"""
    try:
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw')
        result = postgres_hook.get_first("SELECT 1 as test")
        if result and result[0] == 1:
            logging.info("Test de connexion PostgreSQL réussi")
        else:
            raise Exception("Test de connexion PostgreSQL échoué")
    except Exception as e:
        logging.error(f"Erreur lors du test de connexion PostgreSQL: {e}")
        # Ne pas faire échouer le DAG si la base n'est pas encore disponible
        logging.warning("La base PostgreSQL n'est peut-être pas encore disponible")


def display_connection_info():
    """Afficher les informations de connexion configurées"""
    logging.info("=== INFORMATIONS DE CONNEXION ===")
    logging.info("MySQL OLTP:")
    logging.info("  - Connexion ID: mysql_ops")
    logging.info("  - Host: mysql_ops_db")
    logging.info("  - Database: ecommerce_ops_db")
    logging.info("  - Port: 3306")
    
    logging.info("PostgreSQL RAW:")
    logging.info("  - Connexion ID: postgres_raw")
    logging.info("  - Host: postgres_raw_db")
    logging.info("  - Database: ecommerce_raw_db")
    logging.info("  - Port: 5432")
    
    logging.info("Filesystem:")
    logging.info("  - Connexion ID: fs_default")
    logging.info("  - Path: /opt/airflow/resource")


# Configuration du DAG
default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='setup_connections',
    default_args=default_args,
    description='Configuration des connexions Airflow pour le projet e-commerce',
    schedule=None,  # Exécution manuelle uniquement
    catchup=False,
    tags=['setup', 'connections', 'configuration'],
) as dag:

    # Création des connexions
    create_mysql_conn_task = PythonOperator(
        task_id='create_mysql_connection',
        python_callable=create_mysql_connection,
    )

    create_postgres_conn_task = PythonOperator(
        task_id='create_postgres_connection',
        python_callable=create_postgres_connection,
    )

    create_fs_conn_task = PythonOperator(
        task_id='create_filesystem_connection',
        python_callable=create_filesystem_connection,
    )

    # Tests de connexion
    test_mysql_task = PythonOperator(
        task_id='test_mysql_connection',
        python_callable=test_mysql_connection,
    )

    test_postgres_task = PythonOperator(
        task_id='test_postgres_connection',
        python_callable=test_postgres_connection,
    )

    # Affichage des informations
    display_info_task = PythonOperator(
        task_id='display_connection_info',
        python_callable=display_connection_info,
    )

    # Définir les dépendances
    [create_mysql_conn_task, create_postgres_conn_task, create_fs_conn_task] >> display_info_task
    create_mysql_conn_task >> test_mysql_task
    create_postgres_conn_task >> test_postgres_task
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import pandas as pd
import logging
import re
import os


def validate_csv_file():
    """Valider l'existence et la structure du fichier CSV"""
    csv_path = '/opt/airflow/resource/payment_history.csv'
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Le fichier CSV n'existe pas: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
        expected_columns = ['payment_id', 'sale_id', 'client_id', 'payment_date', 'amount', 'method', 'status']
        
        if not all(col in df.columns for col in expected_columns):
            raise ValueError(f"Colonnes manquantes. Attendues: {expected_columns}, Trouvées: {list(df.columns)}")
        
        logging.info(f"Fichier CSV validé: {len(df)} lignes trouvées")
        return True
        
    except Exception as e:
        logging.error(f"Erreur lors de la validation du CSV: {e}")
        raise


def clean_csv_data():
    """Nettoyer et transformer les données du CSV"""
    csv_path = '/opt/airflow/resource/payment_history.csv'
    cleaned_path = '/opt/airflow/resource/payment_history_cleaned.csv'
    
    try:
        df = pd.read_csv(csv_path)
        logging.info(f"Données originales: {len(df)} lignes")
        
        # Nettoyer la colonne amount (supprimer les espaces et remplacer les virgules par des points)
        def clean_amount(amount_str):
            if pd.isna(amount_str):
                return None
            # Convertir en string si ce n'est pas déjà le cas
            amount_str = str(amount_str)
            # Supprimer les espaces et remplacer les virgules par des points
            cleaned = re.sub(r'[^\d,.]', '', amount_str)
            cleaned = cleaned.replace(',', '.')
            try:
                return float(cleaned)
            except ValueError:
                logging.warning(f"Impossible de convertir le montant: {amount_str}")
                return None
        
        df['amount'] = df['amount'].apply(clean_amount)
        
        # Nettoyer la colonne payment_date
        def clean_date(date_str):
            if pd.isna(date_str):
                return None
            try:
                # Essayer de parser la date au format DD/MM/YYYY HH:MM:SS
                return pd.to_datetime(date_str, format='%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            except:
                try:
                    # Essayer d'autres formats
                    return pd.to_datetime(date_str).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    logging.warning(f"Impossible de convertir la date: {date_str}")
                    return None
        
        df['payment_date'] = df['payment_date'].apply(clean_date)
        
        # Supprimer les lignes avec des valeurs nulles critiques
        initial_count = len(df)
        df = df.dropna(subset=['payment_id', 'sale_id', 'client_id', 'amount', 'payment_date'])
        final_count = len(df)
        
        if initial_count != final_count:
            logging.warning(f"Suppression de {initial_count - final_count} lignes avec des valeurs nulles")
        
        # Valider les types de données
        df['payment_id'] = df['payment_id'].astype(int)
        df['sale_id'] = df['sale_id'].astype(int)
        df['client_id'] = df['client_id'].astype(int)
        
        # Sauvegarder le fichier nettoyé
        df.to_csv(cleaned_path, index=False)
        logging.info(f"Données nettoyées sauvegardées: {len(df)} lignes dans {cleaned_path}")
        
        return cleaned_path
        
    except Exception as e:
        logging.error(f"Erreur lors du nettoyage des données: {e}")
        raise


def validate_cleaned_data():
    """Valider les données nettoyées"""
    cleaned_path = '/opt/airflow/resource/payment_history_cleaned.csv'
    
    try:
        df = pd.read_csv(cleaned_path)
        
        # Vérifications de base
        assert len(df) > 0, "Aucune donnée après nettoyage"
        assert df['payment_id'].notna().all(), "Des payment_id sont manquants"
        assert df['amount'].notna().all(), "Des montants sont manquants"
        assert df['payment_date'].notna().all(), "Des dates sont manquantes"
        
        # Vérifier les valeurs dupliquées
        duplicates = df['payment_id'].duplicated().sum()
        if duplicates > 0:
            logging.warning(f"{duplicates} payment_id dupliqués trouvés")
        
        # Vérifier les montants négatifs
        negative_amounts = (df['amount'] < 0).sum()
        if negative_amounts > 0:
            logging.warning(f"{negative_amounts} montants négatifs trouvés")
        
        logging.info(f"Validation réussie: {len(df)} lignes valides")
        
    except Exception as e:
        logging.error(f"Erreur lors de la validation des données nettoyées: {e}")
        raise


def backup_existing_data():
    """Sauvegarder les données existantes avant mise à jour"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Créer une table de sauvegarde avec timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"payment_history_backup_{timestamp}"
        
        mysql_hook.run(f"""
            CREATE TABLE {backup_table} AS 
            SELECT * FROM payment_history;
        """)
        
        count = mysql_hook.get_first(f"SELECT COUNT(*) FROM {backup_table}")[0]
        logging.info(f"Sauvegarde créée: {backup_table} avec {count} enregistrements")
        
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde: {e}")
        raise


def load_csv_to_mysql():
    """Charger les données CSV nettoyées dans MySQL"""
    cleaned_path = '/opt/airflow/resource/payment_history_cleaned.csv'
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Lire le CSV nettoyé
        df = pd.read_csv(cleaned_path)
        
        # Préparer les données pour l'insertion
        records = []
        for _, row in df.iterrows():
            records.append((
                int(row['payment_id']),
                int(row['sale_id']),
                int(row['client_id']),
                row['payment_date'],
                float(row['amount']),
                row['method'],
                row['status']
            ))
        
        # Insérer ou mettre à jour les données
        insert_sql = """
            INSERT INTO payment_history 
            (payment_id, sale_id, client_id, payment_date, amount, method, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sale_id = VALUES(sale_id),
                client_id = VALUES(client_id),
                payment_date = VALUES(payment_date),
                amount = VALUES(amount),
                method = VALUES(method),
                status = VALUES(status)
        """
        
        mysql_hook.run(insert_sql, parameters=records)
        logging.info(f"Insertion/mise à jour de {len(records)} enregistrements réussie")
        
    except Exception as e:
        logging.error(f"Erreur lors du chargement en base: {e}")
        raise


def verify_data_integrity():
    """Vérifier l'intégrité des données après chargement"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Compter les enregistrements
        total_count = mysql_hook.get_first("SELECT COUNT(*) FROM payment_history")[0]
        
        # Vérifier les contraintes de clés étrangères
        invalid_sales = mysql_hook.get_first("""
            SELECT COUNT(*) FROM payment_history p 
            LEFT JOIN sales s ON p.sale_id = s.sale_id 
            WHERE s.sale_id IS NULL
        """)[0]
        
        invalid_clients = mysql_hook.get_first("""
            SELECT COUNT(*) FROM payment_history p 
            LEFT JOIN clients c ON p.client_id = c.client_id 
            WHERE c.client_id IS NULL
        """)[0]
        
        # Vérifier les montants négatifs
        negative_amounts = mysql_hook.get_first("""
            SELECT COUNT(*) FROM payment_history WHERE amount < 0
        """)[0]
        
        logging.info(f"Vérification d'intégrité:")
        logging.info(f"- Total des paiements: {total_count}")
        logging.info(f"- Ventes invalides: {invalid_sales}")
        logging.info(f"- Clients invalides: {invalid_clients}")
        logging.info(f"- Montants négatifs: {negative_amounts}")
        
        if invalid_sales > 0 or invalid_clients > 0:
            logging.warning("Des problèmes d'intégrité référentielle ont été détectés")
        
    except Exception as e:
        logging.error(f"Erreur lors de la vérification d'intégrité: {e}")
        raise


def cleanup_temp_files():
    """Nettoyer les fichiers temporaires"""
    temp_files = ['/opt/airflow/resource/payment_history_cleaned.csv']
    
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Fichier temporaire supprimé: {file_path}")
        except Exception as e:
            logging.warning(f"Impossible de supprimer {file_path}: {e}")


# Configuration du DAG
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='process_payment_csv',
    default_args=default_args,
    description='Traitement et chargement du fichier CSV des paiements',
    schedule='@daily',
    catchup=False,
    tags=['ecommerce', 'csv', 'payment', 'etl'],
) as dag:

    # Validation du fichier CSV
    validate_csv_task = PythonOperator(
        task_id='validate_csv_file',
        python_callable=validate_csv_file,
    )

    # Groupe de tâches pour le traitement des données
    with TaskGroup(group_id='data_processing') as processing_group:
        
        clean_data_task = PythonOperator(
            task_id='clean_csv_data',
            python_callable=clean_csv_data,
        )
        
        validate_cleaned_task = PythonOperator(
            task_id='validate_cleaned_data',
            python_callable=validate_cleaned_data,
        )
        
        clean_data_task >> validate_cleaned_task

    # Groupe de tâches pour le chargement en base
    with TaskGroup(group_id='database_loading') as loading_group:
        
        backup_task = PythonOperator(
            task_id='backup_existing_data',
            python_callable=backup_existing_data,
        )
        
        load_task = PythonOperator(
            task_id='load_csv_to_mysql',
            python_callable=load_csv_to_mysql,
        )
        
        verify_task = PythonOperator(
            task_id='verify_data_integrity',
            python_callable=verify_data_integrity,
        )
        
        backup_task >> load_task >> verify_task

    # Nettoyage final
    cleanup_task = PythonOperator(
        task_id='cleanup_temp_files',
        python_callable=cleanup_temp_files,
    )

    # Définir les dépendances du DAG
    validate_csv_task >> processing_group >> loading_group >> cleanup_task
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging
import pandas as pd

# Configuration par défaut des tâches
default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def create_raw_schema(**context):
    """Crée le schéma RAW et les tables dans PostgreSQL"""
    try:
        # Connexion à PostgreSQL RAW
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Lecture du fichier DDL
        ddl_sql = """
        CREATE SCHEMA IF NOT EXISTS raw;
        SET search_path = raw;

        -- Supprimer les tables existantes si elles existent
        DROP TABLE IF EXISTS payment_history_raw CASCADE;
        DROP TABLE IF EXISTS inventory_raw CASCADE;
        DROP TABLE IF EXISTS sales_raw CASCADE;
        DROP TABLE IF EXISTS clients_raw CASCADE;
        DROP TABLE IF EXISTS products_raw CASCADE;
        DROP TABLE IF EXISTS categories_raw CASCADE;
        DROP TABLE IF EXISTS regions_raw CASCADE;

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
            total_amount   TEXT,
            region_id      TEXT
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

        CREATE TABLE regions_raw
        (
            region_id   TEXT,
            region_name TEXT,
            region_code TEXT,
            created_at  TEXT
        );
        """
        
        # Exécution du DDL
        postgres_hook.run(ddl_sql)
        
        logging.info("✅ Schéma RAW et tables créés avec succès")
        return "Schema created successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du schéma RAW: {str(e)}")
        raise

def extract_and_load_table(table_name, **context):
    """Extrait les données d'une table MySQL et les charge dans PostgreSQL RAW"""
    try:
        # Connexions
        mysql_hook = MySqlHook(mysql_conn_id='mysql_oltp_conn')
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Mapping des tables et leurs colonnes
        table_mappings = {
            'categories': {
                'source_table': 'categories',
                'target_table': 'categories_raw',
                'columns': ['category_id', 'name']
            },
            'products': {
                'source_table': 'products',
                'target_table': 'products_raw',
                'columns': ['product_id', 'name', 'category_id', 'price']
            },
            'clients': {
                'source_table': 'clients',
                'target_table': 'clients_raw',
                'columns': ['client_id', 'first_name', 'last_name', 'email', 'created_at']
            },
            'sales': {
                'source_table': 'sales',
                'target_table': 'sales_raw',
                'columns': ['sale_id', 'client_id', 'product_id', 'sale_date_time', 'quantity', 'total_amount', 'region_id']
            },
            'inventory': {
                'source_table': 'inventory',
                'target_table': 'inventory_raw',
                'columns': ['product_id', 'stock_quantity', 'reorder_threshold', 'updated_at']
            },
            'payment_history': {
                'source_table': 'payment_history',
                'target_table': 'payment_history_raw',
                'columns': ['payment_id', 'sale_id', 'client_id', 'payment_date', 'amount', 'method', 'status']
            },
            'regions': {
                'source_table': 'regions',
                'target_table': 'regions_raw',
                'columns': ['region_id', 'region_name', 'region_code', 'created_at']
            }
        }
        
        if table_name not in table_mappings:
            raise ValueError(f"Table {table_name} non supportée")
        
        mapping = table_mappings[table_name]
        source_table = mapping['source_table']
        target_table = mapping['target_table']
        columns = mapping['columns']
        
        # Extraction des données depuis MySQL
        select_sql = f"SELECT {', '.join(columns)} FROM {source_table}"
        logging.info(f"🔍 Extraction depuis MySQL: {select_sql}")
        
        # Récupération des données
        mysql_conn = mysql_hook.get_conn()
        df = pd.read_sql(select_sql, mysql_conn)
        mysql_conn.close()
        
        if df.empty:
            logging.warning(f"⚠️ Aucune donnée trouvée dans la table {source_table}")
            return f"No data found in {source_table}"
        
        logging.info(f"📊 {len(df)} enregistrements extraits de {source_table}")
        
        # Conversion de toutes les colonnes en TEXT (string)
        for col in df.columns:
            df[col] = df[col].astype(str)
            # Remplacer les valeurs NaN par des chaînes vides
            df[col] = df[col].replace('nan', '')
            df[col] = df[col].replace('None', '')
        
        # Nettoyage de la table cible
        delete_sql = f"DELETE FROM raw.{target_table}"
        postgres_hook.run(delete_sql)
        logging.info(f"🧹 Table {target_table} vidée")
        
        # Insertion des données dans PostgreSQL RAW
        postgres_conn = postgres_hook.get_conn()
        cursor = postgres_conn.cursor()
        
        try:
            # Préparation de la requête d'insertion
            placeholders = ', '.join(['%s'] * len(columns))
            insert_sql = f"INSERT INTO raw.{target_table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Insertion par batch pour de meilleures performances
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                values = [tuple(row) for row in batch.values]
                cursor.executemany(insert_sql, values)
                total_inserted += len(values)
                
                if i % (batch_size * 5) == 0:  # Log tous les 5000 enregistrements
                    logging.info(f"📥 {total_inserted} enregistrements insérés...")
            
            postgres_conn.commit()
            logging.info(f"✅ {total_inserted} enregistrements insérés dans {target_table}")
            
        except Exception as e:
            postgres_conn.rollback()
            raise e
        finally:
            cursor.close()
            postgres_conn.close()
        
        return f"Successfully loaded {total_inserted} records into {target_table}"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du chargement de {table_name}: {str(e)}")
        raise

def validate_raw_data(**context):
    """Valide les données chargées dans les tables RAW"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        tables = [
            'categories_raw',
            'products_raw', 
            'clients_raw',
            'sales_raw',
            'inventory_raw',
            'payment_history_raw',
            'regions_raw'
        ]
        
        validation_results = {}
        total_records = 0
        
        for table in tables:
            count_sql = f"SELECT COUNT(*) FROM raw.{table}"
            result = postgres_hook.get_first(count_sql)
            count = result[0] if result else 0
            validation_results[table] = count
            total_records += count
            
            logging.info(f"📊 {table}: {count} enregistrements")
        
        # Vérifications de cohérence
        issues = []
        
        # Vérifier que nous avons des données
        if total_records == 0:
            issues.append("Aucune donnée chargée dans les tables RAW")
        
        # Vérifier la cohérence des relations (même en TEXT)
        coherence_checks = [
            {
                'name': 'Products-Categories',
                'sql': """
                SELECT COUNT(*) FROM raw.products_raw p 
                LEFT JOIN raw.categories_raw c ON p.category_id = c.category_id 
                WHERE c.category_id IS NULL AND p.category_id != ''
                """
            },
            {
                'name': 'Sales-Clients',
                'sql': """
                SELECT COUNT(*) FROM raw.sales_raw s 
                LEFT JOIN raw.clients_raw c ON s.client_id = c.client_id 
                WHERE c.client_id IS NULL AND s.client_id != ''
                """
            },
            {
                'name': 'Sales-Products',
                'sql': """
                SELECT COUNT(*) FROM raw.sales_raw s 
                LEFT JOIN raw.products_raw p ON s.product_id = p.product_id 
                WHERE p.product_id IS NULL AND s.product_id != ''
                """
            }
        ]
        
        for check in coherence_checks:
            result = postgres_hook.get_first(check['sql'])
            orphan_count = result[0] if result else 0
            if orphan_count > 0:
                issues.append(f"{check['name']}: {orphan_count} enregistrements orphelins")
        
        # Génération du rapport
        report = f"""
=== RAPPORT DE VALIDATION DES DONNÉES RAW ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 STATISTIQUES PAR TABLE:
"""
        for table, count in validation_results.items():
            report += f"  • {table}: {count:,} enregistrements\n"
        
        report += f"\n📈 TOTAL: {total_records:,} enregistrements chargés\n"
        
        if issues:
            report += f"\n⚠️ PROBLÈMES DÉTECTÉS:\n"
            for issue in issues:
                report += f"  • {issue}\n"
        else:
            report += f"\n✅ VALIDATION RÉUSSIE: Aucun problème détecté\n"
        
        logging.info(report)
        
        # Sauvegarde du rapport
        report_path = f"/opt/airflow/resource/raw_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
        
        if issues:
            raise ValueError(f"Validation échouée: {len(issues)} problème(s) détecté(s)")
        
        return validation_results
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la validation: {str(e)}")
        raise

def cleanup_old_reports(**context):
    """Nettoie les anciens rapports de validation"""
    try:
        import os
        import glob
        
        reports_pattern = "/opt/airflow/resource/raw_validation_report_*.txt"
        reports = glob.glob(reports_pattern)
        
        # Garder seulement les 10 derniers rapports
        if len(reports) > 10:
            reports.sort()
            old_reports = reports[:-10]
            
            for report in old_reports:
                try:
                    os.remove(report)
                    logging.info(f"🗑️ Rapport supprimé: {report}")
                except Exception as e:
                    logging.warning(f"⚠️ Impossible de supprimer {report}: {str(e)}")
        
        logging.info(f"🧹 Nettoyage terminé. {len(reports)} rapports conservés")
        return f"Cleaned up old reports, kept {min(len(reports), 10)} reports"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du nettoyage: {str(e)}")
        # Ne pas faire échouer le DAG pour un problème de nettoyage
        return f"Cleanup failed: {str(e)}"

# Définition du DAG
with DAG(
    dag_id='load_raw_data',
    default_args=default_args,
    description='Chargement des données OLTP vers les tables RAW PostgreSQL',
    schedule='0 1 * * *',  # Quotidien à 1h du matin
    catchup=False,
    tags=['ecommerce', 'etl', 'raw', 'postgres'],
) as dag:

    # Création du schéma et des tables RAW
    create_schema_task = PythonOperator(
        task_id='create_raw_schema',
        python_callable=create_raw_schema,
    )

    # Chargement des données par table
    load_categories_task = PythonOperator(
        task_id='load_categories_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'categories'},
    )

    load_products_task = PythonOperator(
        task_id='load_products_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'products'},
    )

    load_clients_task = PythonOperator(
        task_id='load_clients_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'clients'},
    )

    load_sales_task = PythonOperator(
        task_id='load_sales_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'sales'},
    )

    load_inventory_task = PythonOperator(
        task_id='load_inventory_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'inventory'},
    )

    load_payment_history_task = PythonOperator(
        task_id='load_payment_history_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'payment_history'},
    )

    load_regions_task = PythonOperator(
        task_id='load_regions_raw',
        python_callable=extract_and_load_table,
        op_kwargs={'table_name': 'regions'},
    )

    # Validation des données chargées
    validate_data_task = PythonOperator(
        task_id='validate_raw_data',
        python_callable=validate_raw_data,
    )

    # Nettoyage des anciens rapports
    cleanup_task = PythonOperator(
        task_id='cleanup_old_reports',
        python_callable=cleanup_old_reports,
    )

    # Définition des dépendances
    create_schema_task >> [
        load_categories_task,
        load_products_task,
        load_clients_task,
        load_sales_task,
        load_inventory_task,
        load_payment_history_task,
        load_regions_task
    ] >> validate_data_task >> cleanup_task
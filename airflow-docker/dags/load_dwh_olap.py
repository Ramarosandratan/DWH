from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging

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

def create_dwh_olap_schema_and_tables(**context):
    """Crée le schéma DWH OLAP et toutes les tables"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # DDL pour créer le schéma et les tables OLAP
        ddl_sql = """
        -- 1. Schéma cible
        CREATE SCHEMA IF NOT EXISTS ecommerce_dwh;
        SET search_path = ecommerce_dwh;

        -- Supprimer les tables existantes dans l'ordre correct (contraintes FK)
        DROP TABLE IF EXISTS fact_sales CASCADE;
        DROP TABLE IF EXISTS dim_payment_method CASCADE;
        DROP TABLE IF EXISTS dim_customer CASCADE;
        DROP TABLE IF EXISTS dim_product CASCADE;
        DROP TABLE IF EXISTS dim_time CASCADE;
        DROP TABLE IF EXISTS dim_date CASCADE;

        -- 2. Dimension Date
        CREATE TABLE dim_date (
            date_key    DATE        PRIMARY KEY,
            day         SMALLINT    NOT NULL,
            month       SMALLINT    NOT NULL,
            quarter     SMALLINT    NOT NULL,
            year        SMALLINT    NOT NULL,
            day_of_week VARCHAR(10) NOT NULL
        );

        -- 3. Dimension Time
        CREATE TABLE dim_time (
            time_key TIME        PRIMARY KEY,
            hour     SMALLINT    NOT NULL,
            minute   SMALLINT    NOT NULL,
            second   SMALLINT    NOT NULL,
            am_pm    VARCHAR(2)  NOT NULL
        );

        -- 4. Dimension Product
        CREATE TABLE dim_product (
            product_key   SERIAL    PRIMARY KEY,
            product_id    INT        NOT NULL UNIQUE,
            product_name  TEXT       NOT NULL,
            category_id   INT        NOT NULL,
            category_name TEXT       NOT NULL,
            price         NUMERIC(10,2) NOT NULL
        );

        -- 5. Dimension Customer
        CREATE TABLE dim_customer (
            customer_key SERIAL    PRIMARY KEY,
            client_id    INT       NOT NULL UNIQUE,
            full_name    TEXT      NOT NULL,
            email        TEXT      NOT NULL,
            signup_date  DATE      NOT NULL
        );

        -- 6. Dimension Payment Method
        CREATE TABLE dim_payment_method (
            payment_method_key SERIAL     PRIMARY KEY,
            method             VARCHAR(50) UNIQUE NOT NULL
        );

        -- 7. Table de faits
        CREATE TABLE fact_sales (
            sale_key           SERIAL     PRIMARY KEY,
            sale_id            INT        NOT NULL UNIQUE,
            date_key           DATE       NOT NULL REFERENCES dim_date(date_key),
            time_key           TIME       NOT NULL REFERENCES dim_time(time_key),
            product_key        INT        NOT NULL REFERENCES dim_product(product_key),
            customer_key       INT        NOT NULL REFERENCES dim_customer(customer_key),
            quantity           INT        NOT NULL,
            total_amount       NUMERIC(10,2) NOT NULL,
            payment_method_key INT        NOT NULL REFERENCES dim_payment_method(payment_method_key)
        );

        -- Index sur les clés de jointure dans la table de faits
        CREATE INDEX idx_fact_date_key ON fact_sales(date_key);
        CREATE INDEX idx_fact_time_key ON fact_sales(time_key);
        CREATE INDEX idx_fact_product_key ON fact_sales(product_key);
        CREATE INDEX idx_fact_customer_key ON fact_sales(customer_key);
        CREATE INDEX idx_fact_pm_key ON fact_sales(payment_method_key);

        -- Index multi-colonnes pour requêtes analytiques fréquentes
        CREATE INDEX idx_fact_date_product ON fact_sales(date_key, product_key);
        """
        
        postgres_hook.run(ddl_sql)
        logging.info("✅ Schéma DWH OLAP et tables créés avec succès")
        return "DWH OLAP schema and tables created successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du schéma DWH OLAP: {str(e)}")
        raise

def create_dwh_olap_procedures(**context):
    """Crée les procédures stockées pour le DWH OLAP"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Procédures stockées pour OLAP
        procedures_sql = """
        SET search_path = ecommerce_dwh;

        -- Helper function to parse both dd/mm/yyyy HH:MM:SS and yyyy-mm-dd HH24:MI:SS formats
        CREATE OR REPLACE FUNCTION ecommerce_dwh.parse_datetime(ts_text TEXT)
          RETURNS TIMESTAMP WITHOUT TIME ZONE
          LANGUAGE plpgsql
          IMMUTABLE
        AS $$
        BEGIN
          ts_text := trim(ts_text);
          IF ts_text ~ '^\\d{2}/\\d{2}/\\d{4}' THEN
            RETURN to_timestamp(ts_text, 'DD/MM/YYYY HH24:MI:SS');
          ELSE
            RETURN to_timestamp(ts_text, 'YYYY-MM-DD HH24:MI:SS');
          END IF;
        END;
        $$;

        -- Procédure de TRUNCATE ordonné
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.truncate_all_tables()
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- 1. Faits (référence toutes les dimensions)
            TRUNCATE TABLE ecommerce_dwh.fact_sales RESTART IDENTITY CASCADE;

            -- 2. Dimensions
            TRUNCATE TABLE ecommerce_dwh.dim_time CASCADE;
            TRUNCATE TABLE ecommerce_dwh.dim_date CASCADE;
            TRUNCATE TABLE ecommerce_dwh.dim_product RESTART IDENTITY CASCADE;
            TRUNCATE TABLE ecommerce_dwh.dim_customer RESTART IDENTITY CASCADE;
            TRUNCATE TABLE ecommerce_dwh.dim_payment_method RESTART IDENTITY CASCADE;

            COMMIT;

            RAISE NOTICE 'All tables truncated in ecommerce_dwh';
        END;
        $$;

        -- Procédure pour charger dim_date
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_dim_date()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh.dim_date
              (date_key, day, month, quarter, year, day_of_week)
          SELECT DISTINCT 
                 parse_datetime(sale_date_time)::DATE AS date_key,
                 EXTRACT(DAY FROM parse_datetime(sale_date_time)::DATE)::SMALLINT AS day,
                 EXTRACT(MONTH FROM parse_datetime(sale_date_time)::DATE)::SMALLINT AS month,
                 EXTRACT(QUARTER FROM parse_datetime(sale_date_time)::DATE)::SMALLINT AS quarter,
                 EXTRACT(YEAR FROM parse_datetime(sale_date_time)::DATE)::SMALLINT AS year,
                 TO_CHAR(parse_datetime(sale_date_time)::DATE, 'FMDay') AS day_of_week
          FROM raw.sales_raw
          WHERE sale_date_time IS NOT NULL AND trim(sale_date_time) != ''
          UNION
          SELECT DISTINCT 
                 parse_datetime(created_at)::DATE AS date_key,
                 EXTRACT(DAY FROM parse_datetime(created_at)::DATE)::SMALLINT AS day,
                 EXTRACT(MONTH FROM parse_datetime(created_at)::DATE)::SMALLINT AS month,
                 EXTRACT(QUARTER FROM parse_datetime(created_at)::DATE)::SMALLINT AS quarter,
                 EXTRACT(YEAR FROM parse_datetime(created_at)::DATE)::SMALLINT AS year,
                 TO_CHAR(parse_datetime(created_at)::DATE, 'FMDay') AS day_of_week
          FROM raw.clients_raw
          WHERE created_at IS NOT NULL AND trim(created_at) != ''
          UNION
          SELECT DISTINCT 
                 parse_datetime(payment_date)::DATE AS date_key,
                 EXTRACT(DAY FROM parse_datetime(payment_date)::DATE)::SMALLINT AS day,
                 EXTRACT(MONTH FROM parse_datetime(payment_date)::DATE)::SMALLINT AS month,
                 EXTRACT(QUARTER FROM parse_datetime(payment_date)::DATE)::SMALLINT AS quarter,
                 EXTRACT(YEAR FROM parse_datetime(payment_date)::DATE)::SMALLINT AS year,
                 TO_CHAR(parse_datetime(payment_date)::DATE, 'FMDay') AS day_of_week
          FROM raw.payment_history_raw
          WHERE payment_date IS NOT NULL AND trim(payment_date) != ''
          UNION
          SELECT DISTINCT 
                 parse_datetime(updated_at)::DATE AS date_key,
                 EXTRACT(DAY FROM parse_datetime(updated_at)::DATE)::SMALLINT AS day,
                 EXTRACT(MONTH FROM parse_datetime(updated_at)::DATE)::SMALLINT AS month,
                 EXTRACT(QUARTER FROM parse_datetime(updated_at)::DATE)::SMALLINT AS quarter,
                 EXTRACT(YEAR FROM parse_datetime(updated_at)::DATE)::SMALLINT AS year,
                 TO_CHAR(parse_datetime(updated_at)::DATE, 'FMDay') AS day_of_week
          FROM raw.inventory_raw
          WHERE updated_at IS NOT NULL AND trim(updated_at) != ''
          ON CONFLICT (date_key) DO NOTHING;
        END;
        $$;

        -- Procédure pour charger dim_time
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_dim_time()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh.dim_time
              (time_key, hour, minute, second, am_pm)
          SELECT DISTINCT 
                 parse_datetime(sale_date_time)::TIME AS time_key,
                 EXTRACT(HOUR FROM parse_datetime(sale_date_time)::TIME)::SMALLINT AS hour,
                 EXTRACT(MINUTE FROM parse_datetime(sale_date_time)::TIME)::SMALLINT AS minute,
                 EXTRACT(SECOND FROM parse_datetime(sale_date_time)::TIME)::SMALLINT AS second,
                 CASE WHEN EXTRACT(HOUR FROM parse_datetime(sale_date_time)::TIME) < 12 THEN 'AM' ELSE 'PM' END AS am_pm
          FROM raw.sales_raw
          WHERE sale_date_time IS NOT NULL AND trim(sale_date_time) != ''
          UNION
          SELECT DISTINCT 
                 parse_datetime(payment_date)::TIME AS time_key,
                 EXTRACT(HOUR FROM parse_datetime(payment_date)::TIME)::SMALLINT AS hour,
                 EXTRACT(MINUTE FROM parse_datetime(payment_date)::TIME)::SMALLINT AS minute,
                 EXTRACT(SECOND FROM parse_datetime(payment_date)::TIME)::SMALLINT AS second,
                 CASE WHEN EXTRACT(HOUR FROM parse_datetime(payment_date)::TIME) < 12 THEN 'AM' ELSE 'PM' END AS am_pm
          FROM raw.payment_history_raw
          WHERE payment_date IS NOT NULL AND trim(payment_date) != ''
          UNION
          SELECT DISTINCT 
                 parse_datetime(updated_at)::TIME AS time_key,
                 EXTRACT(HOUR FROM parse_datetime(updated_at)::TIME)::SMALLINT AS hour,
                 EXTRACT(MINUTE FROM parse_datetime(updated_at)::TIME)::SMALLINT AS minute,
                 EXTRACT(SECOND FROM parse_datetime(updated_at)::TIME)::SMALLINT AS second,
                 CASE WHEN EXTRACT(HOUR FROM parse_datetime(updated_at)::TIME) < 12 THEN 'AM' ELSE 'PM' END AS am_pm
          FROM raw.inventory_raw
          WHERE updated_at IS NOT NULL AND trim(updated_at) != ''
          UNION
          SELECT DISTINCT 
                 parse_datetime(created_at)::TIME AS time_key,
                 EXTRACT(HOUR FROM parse_datetime(created_at)::TIME)::SMALLINT AS hour,
                 EXTRACT(MINUTE FROM parse_datetime(created_at)::TIME)::SMALLINT AS minute,
                 EXTRACT(SECOND FROM parse_datetime(created_at)::TIME)::SMALLINT AS second,
                 CASE WHEN EXTRACT(HOUR FROM parse_datetime(created_at)::TIME) < 12 THEN 'AM' ELSE 'PM' END AS am_pm
          FROM raw.clients_raw
          WHERE created_at IS NOT NULL AND trim(created_at) != ''
          ON CONFLICT (time_key) DO NOTHING;
        END;
        $$;

        -- Procédure pour charger dim_customer
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_dim_customer()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh.dim_customer
              (client_id, full_name, email, signup_date)
          SELECT 
               (trim(c.client_id))::INT,
               upper(trim(c.first_name)) || ' ' || upper(trim(c.last_name)),
               upper(trim(c.email)),
               parse_datetime(c.created_at)::DATE
          FROM raw.clients_raw c
          WHERE c.client_id IS NOT NULL AND trim(c.client_id) != ''
          ON CONFLICT (client_id) DO NOTHING;
        END;
        $$;

        -- Procédure pour charger dim_payment_method
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_dim_payment_method()
        LANGUAGE plpgsql
        AS $$
        BEGIN
          INSERT INTO ecommerce_dwh.dim_payment_method(method)
          SELECT DISTINCT upper(trim(method))
          FROM raw.payment_history_raw
          WHERE method IS NOT NULL AND trim(method) != ''
          ON CONFLICT (method) DO NOTHING;
        END;
        $$;

        -- Procédure pour charger dim_product
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_dim_product()
        LANGUAGE plpgsql
        AS $$
        BEGIN
          INSERT INTO ecommerce_dwh.dim_product
              (product_id, product_name, category_id, category_name, price)
          SELECT
            (trim(p.product_id))::INT,
            upper(trim(p.name)),
            (trim(p.category_id))::INT,
            upper(trim(c.name)),
            (replace(replace(trim(p.price), ' ', ''), ',', '.'))::NUMERIC(10,2)
          FROM raw.products_raw p
          LEFT JOIN raw.categories_raw c
            ON trim(p.category_id) = trim(c.category_id)
          WHERE p.product_id IS NOT NULL AND trim(p.product_id) != ''
          ON CONFLICT (product_id) DO NOTHING;
        END;
        $$;

        -- Procédure pour charger fact_sales
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_fact_sales()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh.fact_sales
              (sale_id, date_key, time_key, product_key,
               customer_key, quantity, total_amount, payment_method_key)
          SELECT 
               (trim(s.sale_id))::INT,
               parse_datetime(s.sale_date_time)::DATE AS date_key,
               parse_datetime(s.sale_date_time)::TIME AS time_key,
               dp.product_key,
               dc.customer_key,
               (trim(s.quantity))::INT,
               (replace(replace(trim(s.total_amount), ' ', ''), ',', '.'))::NUMERIC(10, 2),
               pm.payment_method_key
          FROM raw.sales_raw s
          JOIN ecommerce_dwh.dim_product dp
            ON dp.product_id = (trim(s.product_id))::INT
          JOIN ecommerce_dwh.dim_customer dc
            ON dc.client_id = (trim(s.client_id))::INT
          LEFT JOIN raw.payment_history_raw ph
            ON trim(ph.sale_id) = trim(s.sale_id)
          LEFT JOIN ecommerce_dwh.dim_payment_method pm
            ON pm.method = upper(trim(ph.method))
          WHERE s.sale_id IS NOT NULL AND trim(s.sale_id) != ''
            AND s.sale_date_time IS NOT NULL AND trim(s.sale_date_time) != ''
          ON CONFLICT (sale_id) DO NOTHING;
        END;
        $$;

        -- Orchestrateur principal
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.etl_olap_master()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          CALL ecommerce_dwh.load_dim_date();
          CALL ecommerce_dwh.load_dim_time();
          CALL ecommerce_dwh.load_dim_payment_method();
          CALL ecommerce_dwh.load_dim_product();
          CALL ecommerce_dwh.load_dim_customer();
          CALL ecommerce_dwh.load_fact_sales();
        END;
        $$;
        """
        
        postgres_hook.run(procedures_sql)
        logging.info("✅ Procédures stockées DWH OLAP créées avec succès")
        return "DWH OLAP procedures created successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création des procédures DWH OLAP: {str(e)}")
        raise

def truncate_dwh_olap_tables(**context):
    """Vide toutes les tables DWH OLAP dans l'ordre correct"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        logging.info("🗑️ Vidage des tables DWH OLAP...")
        
        # Appel de la procédure de truncate
        truncate_sql = "CALL ecommerce_dwh.truncate_all_tables();"
        postgres_hook.run(truncate_sql)
        
        logging.info("✅ Tables DWH OLAP vidées avec succès")
        return "DWH OLAP tables truncated successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du vidage des tables DWH OLAP: {str(e)}")
        raise

def load_olap_dimension_table(dimension_name, **context):
    """Charge une table de dimension OLAP spécifique"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        procedure_mapping = {
            'date': 'load_dim_date',
            'time': 'load_dim_time',
            'customer': 'load_dim_customer',
            'product': 'load_dim_product',
            'payment_method': 'load_dim_payment_method'
        }
        
        if dimension_name not in procedure_mapping:
            raise ValueError(f"Dimension {dimension_name} non supportée")
        
        procedure_name = procedure_mapping[dimension_name]
        
        logging.info(f"🔄 Chargement de la dimension OLAP {dimension_name}...")
        
        # Exécution de la procédure stockée
        call_sql = f"CALL ecommerce_dwh.{procedure_name}();"
        postgres_hook.run(call_sql)
        
        # Vérification du nombre d'enregistrements chargés
        count_sql = f"SELECT COUNT(*) FROM ecommerce_dwh.dim_{dimension_name}"
        result = postgres_hook.get_first(count_sql)
        count = result[0] if result else 0
        
        logging.info(f"✅ Dimension OLAP {dimension_name} chargée: {count} enregistrements")
        return f"Loaded {count} records into dim_{dimension_name}"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du chargement de dim_{dimension_name}: {str(e)}")
        raise

def load_olap_fact_table(**context):
    """Charge la table de faits OLAP"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        logging.info("🔄 Chargement de la table de faits OLAP...")
        
        # Exécution de la procédure stockée
        call_sql = "CALL ecommerce_dwh.load_fact_sales();"
        postgres_hook.run(call_sql)
        
        # Vérification du nombre d'enregistrements chargés
        count_sql = "SELECT COUNT(*) FROM ecommerce_dwh.fact_sales"
        result = postgres_hook.get_first(count_sql)
        count = result[0] if result else 0
        
        logging.info(f"✅ Table de faits OLAP chargée: {count} enregistrements")
        return f"Loaded {count} records into fact_sales"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du chargement de fact_sales OLAP: {str(e)}")
        raise

def validate_dwh_olap_data(**context):
    """Valide les données chargées dans le DWH OLAP"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requêtes de validation
        validation_queries = {
            'dim_date': "SELECT COUNT(*) FROM ecommerce_dwh.dim_date",
            'dim_time': "SELECT COUNT(*) FROM ecommerce_dwh.dim_time",
            'dim_customer': "SELECT COUNT(*) FROM ecommerce_dwh.dim_customer",
            'dim_product': "SELECT COUNT(*) FROM ecommerce_dwh.dim_product",
            'dim_payment_method': "SELECT COUNT(*) FROM ecommerce_dwh.dim_payment_method",
            'fact_sales': "SELECT COUNT(*) FROM ecommerce_dwh.fact_sales"
        }
        
        validation_results = {}
        total_records = 0
        
        for table, query in validation_queries.items():
            result = postgres_hook.get_first(query)
            count = result[0] if result else 0
            validation_results[table] = count
            total_records += count
            logging.info(f"📊 {table}: {count} enregistrements")
        
        # Vérifications de cohérence
        issues = []
        
        # Vérifier que nous avons des données
        if total_records == 0:
            issues.append("Aucune donnée chargée dans le DWH OLAP")
        
        # Vérifier la cohérence des faits avec les dimensions
        coherence_checks = [
            {
                'name': 'Facts-Date',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh.fact_sales f 
                LEFT JOIN ecommerce_dwh.dim_date d ON f.date_key = d.date_key 
                WHERE d.date_key IS NULL
                """
            },
            {
                'name': 'Facts-Time',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh.fact_sales f 
                LEFT JOIN ecommerce_dwh.dim_time t ON f.time_key = t.time_key 
                WHERE t.time_key IS NULL
                """
            },
            {
                'name': 'Facts-Customer',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh.fact_sales f 
                LEFT JOIN ecommerce_dwh.dim_customer c ON f.customer_key = c.customer_key 
                WHERE c.customer_key IS NULL
                """
            },
            {
                'name': 'Facts-Product',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh.fact_sales f 
                LEFT JOIN ecommerce_dwh.dim_product p ON f.product_key = p.product_key 
                WHERE p.product_key IS NULL
                """
            }
        ]
        
        for check in coherence_checks:
            result = postgres_hook.get_first(check['sql'])
            orphan_count = result[0] if result else 0
            if orphan_count > 0:
                issues.append(f"{check['name']}: {orphan_count} enregistrements orphelins")
        
        # Statistiques avancées
        stats_queries = {
            'total_sales_amount': "SELECT COALESCE(SUM(total_amount), 0) FROM ecommerce_dwh.fact_sales",
            'avg_sale_amount': "SELECT COALESCE(AVG(total_amount), 0) FROM ecommerce_dwh.fact_sales",
            'unique_customers': "SELECT COUNT(DISTINCT customer_key) FROM ecommerce_dwh.fact_sales",
            'unique_products': "SELECT COUNT(DISTINCT product_key) FROM ecommerce_dwh.fact_sales",
            'date_range': """
                SELECT 
                    MIN(date_key)::TEXT || ' - ' || MAX(date_key)::TEXT 
                FROM ecommerce_dwh.fact_sales
            """,
            'time_range': """
                SELECT 
                    MIN(time_key)::TEXT || ' - ' || MAX(time_key)::TEXT 
                FROM ecommerce_dwh.fact_sales
            """
        }
        
        stats_results = {}
        for stat, query in stats_queries.items():
            result = postgres_hook.get_first(query)
            stats_results[stat] = result[0] if result else 0
        
        # Génération du rapport
        report = f"""
=== RAPPORT DE VALIDATION DU DWH OLAP ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 STATISTIQUES PAR TABLE:
"""
        for table, count in validation_results.items():
            report += f"  • {table}: {count:,} enregistrements\n"
        
        report += f"\n📈 TOTAL: {total_records:,} enregistrements chargés\n"
        
        report += f"""
📈 STATISTIQUES BUSINESS:
  • Montant total des ventes: {stats_results['total_sales_amount']:,.2f} €
  • Montant moyen par vente: {stats_results['avg_sale_amount']:,.2f} €
  • Clients uniques: {stats_results['unique_customers']:,}
  • Produits vendus: {stats_results['unique_products']:,}
  • Période des ventes: {stats_results['date_range']}
  • Plage horaire: {stats_results['time_range']}

🔍 MODÈLE OLAP:
  • Schéma: ecommerce_dwh (OLAP optimisé)
  • Clés temporelles: DATE et TIME (types natifs)
  • Contraintes FK: Intégrité référentielle complète
  • Index: Optimisés pour requêtes analytiques
"""
        
        if issues:
            report += f"\n⚠️ PROBLÈMES DÉTECTÉS:\n"
            for issue in issues:
                report += f"  • {issue}\n"
        else:
            report += f"\n✅ VALIDATION RÉUSSIE: Aucun problème détecté\n"
        
        logging.info(report)
        
        # Sauvegarde du rapport
        report_path = f"/opt/airflow/resource/dwh_olap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport OLAP sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport OLAP: {str(e)}")
        
        if issues:
            raise ValueError(f"Validation OLAP échouée: {len(issues)} problème(s) détecté(s)")
        
        return {**validation_results, **stats_results}
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la validation OLAP: {str(e)}")
        raise

def cleanup_old_olap_reports(**context):
    """Nettoie les anciens rapports de validation DWH OLAP"""
    try:
        import os
        import glob
        
        reports_pattern = "/opt/airflow/resource/dwh_olap_validation_report_*.txt"
        reports = glob.glob(reports_pattern)
        
        # Garder seulement les 10 derniers rapports
        if len(reports) > 10:
            reports.sort()
            old_reports = reports[:-10]
            
            for report in old_reports:
                try:
                    os.remove(report)
                    logging.info(f"🗑️ Rapport OLAP supprimé: {report}")
                except Exception as e:
                    logging.warning(f"⚠️ Impossible de supprimer {report}: {str(e)}")
        
        logging.info(f"🧹 Nettoyage OLAP terminé. {len(reports)} rapports conservés")
        return f"Cleaned up old OLAP reports, kept {min(len(reports), 10)} reports"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du nettoyage OLAP: {str(e)}")
        return f"OLAP cleanup failed: {str(e)}"

# Définition du DAG
with DAG(
    dag_id='load_dwh_olap',
    default_args=default_args,
    description='Chargement des données RAW vers le Data Warehouse OLAP optimisé',
    schedule='0 4 * * *',  # Quotidien à 4h du matin (après load_dwh_star à 3h)
    catchup=False,
    tags=['ecommerce', 'dwh', 'olap', 'analytics'],
) as dag:

    # Création du schéma et des tables DWH OLAP
    create_schema_task = PythonOperator(
        task_id='create_dwh_olap_schema_and_tables',
        python_callable=create_dwh_olap_schema_and_tables,
    )

    # Création des procédures stockées
    create_procedures_task = PythonOperator(
        task_id='create_dwh_olap_procedures',
        python_callable=create_dwh_olap_procedures,
    )

    # Vidage des tables existantes
    truncate_tables_task = PythonOperator(
        task_id='truncate_dwh_olap_tables',
        python_callable=truncate_dwh_olap_tables,
    )

    # Chargement des dimensions (peuvent être parallèles)
    load_dim_date_task = PythonOperator(
        task_id='load_olap_dim_date',
        python_callable=load_olap_dimension_table,
        op_kwargs={'dimension_name': 'date'},
    )

    load_dim_time_task = PythonOperator(
        task_id='load_olap_dim_time',
        python_callable=load_olap_dimension_table,
        op_kwargs={'dimension_name': 'time'},
    )

    load_dim_customer_task = PythonOperator(
        task_id='load_olap_dim_customer',
        python_callable=load_olap_dimension_table,
        op_kwargs={'dimension_name': 'customer'},
    )

    load_dim_product_task = PythonOperator(
        task_id='load_olap_dim_product',
        python_callable=load_olap_dimension_table,
        op_kwargs={'dimension_name': 'product'},
    )

    load_dim_payment_method_task = PythonOperator(
        task_id='load_olap_dim_payment_method',
        python_callable=load_olap_dimension_table,
        op_kwargs={'dimension_name': 'payment_method'},
    )

    # Chargement de la table de faits (après les dimensions)
    load_fact_sales_task = PythonOperator(
        task_id='load_olap_fact_sales',
        python_callable=load_olap_fact_table,
    )

    # Validation des données chargées
    validate_dwh_task = PythonOperator(
        task_id='validate_dwh_olap_data',
        python_callable=validate_dwh_olap_data,
    )

    # Nettoyage des anciens rapports
    cleanup_task = PythonOperator(
        task_id='cleanup_old_olap_reports',
        python_callable=cleanup_old_olap_reports,
    )

    # Définition des dépendances
    create_schema_task >> create_procedures_task >> truncate_tables_task >> [
        load_dim_date_task,
        load_dim_time_task,
        load_dim_customer_task,
        load_dim_product_task,
        load_dim_payment_method_task
    ] >> load_fact_sales_task >> validate_dwh_task >> cleanup_task
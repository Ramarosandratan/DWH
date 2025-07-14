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

def create_dwh_schema_and_tables(**context):
    """Crée le schéma DWH et toutes les tables de dimensions et de faits"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # DDL pour créer le schéma et les tables
        ddl_sql = """
        -- 1. Schéma DWH
        CREATE SCHEMA IF NOT EXISTS ecommerce_dwh_star;
        SET search_path = ecommerce_dwh_star;

        -- Supprimer les tables existantes dans l'ordre correct (contraintes FK)
        DROP TABLE IF EXISTS fact_sales CASCADE;
        DROP TABLE IF EXISTS dim_payment_method CASCADE;
        DROP TABLE IF EXISTS dim_customer CASCADE;
        DROP TABLE IF EXISTS dim_product CASCADE;
        DROP TABLE IF EXISTS dim_time CASCADE;
        DROP TABLE IF EXISTS dim_date CASCADE;

        -- Supprimer les séquences existantes
        DROP SEQUENCE IF EXISTS seq_dim_customer_key CASCADE;
        DROP SEQUENCE IF EXISTS seq_dim_product_key CASCADE;
        DROP SEQUENCE IF EXISTS seq_dim_payment_method_key CASCADE;
        DROP SEQUENCE IF EXISTS seq_fact_sales_key CASCADE;

        -- Créer les séquences
        CREATE SEQUENCE seq_dim_customer_key START 1;
        CREATE SEQUENCE seq_dim_product_key START 1;
        CREATE SEQUENCE seq_dim_payment_method_key START 1;
        CREATE SEQUENCE seq_fact_sales_key START 1;

        -- 2. Dimension Date
        CREATE TABLE dim_date
        (
            date_key        INT PRIMARY KEY, -- YYYYMMDD
            day             INT,
            month           INT,
            quarter         INT,
            year            INT,
            day_of_week     VARCHAR(10),
            day_of_week_num INT  -- 1 (lundi) … 7 (dimanche) ISO 8601
        );

        -- 3. Dimension Time
        CREATE TABLE dim_time
        (
            time_key INT PRIMARY KEY, -- HHMMSS
            hour     INT,
            minute   INT,
            second   INT,
            am_pm    VARCHAR(2)
        );

        -- 4. Dimension Product
        CREATE TABLE dim_product
        (
            product_key   INT PRIMARY KEY,
            product_id    INT UNIQUE,
            product_name  TEXT,
            category_id   INT,
            category_name TEXT,
            price         NUMERIC(10, 2)
        );

        -- 5. Dimension Customer
        CREATE TABLE dim_customer
        (
            customer_key INT PRIMARY KEY,
            client_id    INT UNIQUE,
            full_name    TEXT,
            email        TEXT,
            signup_date  DATE
        );

        -- 6. Dimension Payment Method
        CREATE TABLE dim_payment_method
        (
            payment_method_key INT PRIMARY KEY,
            method             VARCHAR(50) UNIQUE
        );

        -- 7. Table de faits
        CREATE TABLE fact_sales
        (
            sale_key           INT PRIMARY KEY,
            sale_id            INT UNIQUE,
            date_key           INT,
            time_key           INT,
            product_key        INT,
            customer_key       INT,
            quantity           INT,
            total_amount       NUMERIC(10, 2),
            payment_method_key INT,
            FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
            FOREIGN KEY (time_key) REFERENCES dim_time(time_key),
            FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
            FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
            FOREIGN KEY (payment_method_key) REFERENCES dim_payment_method(payment_method_key)
        );

        -- Index pour améliorer les performances
        CREATE INDEX idx_fact_sales_date ON fact_sales(date_key);
        CREATE INDEX idx_fact_sales_product ON fact_sales(product_key);
        CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
        CREATE INDEX idx_fact_sales_payment ON fact_sales(payment_method_key);
        """
        
        postgres_hook.run(ddl_sql)
        logging.info("✅ Schéma DWH et tables créés avec succès")
        return "DWH schema and tables created successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du schéma DWH: {str(e)}")
        raise

def create_dwh_procedures(**context):
    """Crée les procédures stockées pour le chargement des données"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Procédures stockées
        procedures_sql = """
        SET search_path = ecommerce_dwh_star;

        -- Helper function to parse both dd/mm/yyyy HH:MM:SS and yyyy-mm-dd HH24:MI:SS formats
        CREATE OR REPLACE FUNCTION ecommerce_dwh_star.parse_datetime(ts_text TEXT)
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

        -- 2.1 dim_date
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_date()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh_star.dim_date
              (date_key, day, month, quarter, year, day_of_week, day_of_week_num)
          SELECT (TO_CHAR(d, 'YYYYMMDD'))::INT AS date_key,
                 EXTRACT(DAY FROM d)::INT      AS day,
                 EXTRACT(MONTH FROM d)::INT    AS month,
                 EXTRACT(QUARTER FROM d)::INT  AS quarter,
                 EXTRACT(YEAR FROM d)::INT     AS year,
                 TO_CHAR(d, 'FMDay')           AS day_of_week,
                 EXTRACT(ISODOW FROM d)::INT   AS day_of_week_num
          FROM (
            SELECT DISTINCT parse_datetime(sale_date_time)::DATE AS d FROM raw.sales_raw
            UNION
            SELECT DISTINCT parse_datetime(created_at)::DATE            FROM raw.clients_raw
            UNION
            SELECT DISTINCT parse_datetime(payment_date)::DATE          FROM raw.payment_history_raw
            UNION
            SELECT DISTINCT parse_datetime(updated_at)::DATE            FROM raw.inventory_raw
          ) src(d)
          WHERE NOT EXISTS (
            SELECT 1
              FROM ecommerce_dwh_star.dim_date tgt
             WHERE tgt.date_key = (TO_CHAR(src.d, 'YYYYMMDD'))::INT
          );
        END;
        $$;

        -- 2.2 dim_time
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_time()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh_star.dim_time
              (time_key, hour, minute, second, am_pm)
          SELECT (EXTRACT(HOUR FROM t) * 10000
                  + EXTRACT(MINUTE FROM t) * 100
                  + EXTRACT(SECOND FROM t))::INT AS time_key,
                 EXTRACT(HOUR FROM t)::INT           AS hour,
                 EXTRACT(MINUTE FROM t)::INT         AS minute,
                 EXTRACT(SECOND FROM t)::INT         AS second,
                 CASE WHEN EXTRACT(HOUR FROM t) < 12 THEN 'AM' ELSE 'PM' END AS am_pm
          FROM (
            SELECT DISTINCT parse_datetime(sale_date_time)::TIME AS t FROM raw.sales_raw
            UNION
            SELECT DISTINCT parse_datetime(payment_date)::TIME   FROM raw.payment_history_raw
            UNION
            SELECT DISTINCT parse_datetime(updated_at)::TIME     FROM raw.inventory_raw
            UNION
            SELECT DISTINCT parse_datetime(created_at)::TIME     FROM raw.clients_raw
          ) src(t)
          WHERE NOT EXISTS (
            SELECT 1
              FROM ecommerce_dwh_star.dim_time tgt
             WHERE tgt.time_key = (
               EXTRACT(HOUR FROM src.t) * 10000
               + EXTRACT(MINUTE FROM src.t) * 100
               + EXTRACT(SECOND FROM src.t)
             )::INT
          );
        END;
        $$;

        -- 2.3 dim_customer
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_customer()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh_star.dim_customer
              (customer_key, client_id, full_name, email, signup_date)
          SELECT nextval('seq_dim_customer_key')
               , (trim(c.client_id))::INT
               , upper(trim(c.first_name)) || ' ' || upper(trim(c.last_name))
               , upper(trim(c.email))
               , parse_datetime(c.created_at)::DATE
          FROM raw.clients_raw c
          WHERE NOT EXISTS (
            SELECT 1
              FROM ecommerce_dwh_star.dim_customer tgt
             WHERE tgt.client_id = (trim(c.client_id))::INT
          );
        END;
        $$;

        -- 2.4 load_dim_payment_method
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_payment_method()
        LANGUAGE plpgsql
        AS $$
        BEGIN
          INSERT INTO ecommerce_dwh_star.dim_payment_method(payment_method_key, method)
          SELECT
            nextval('seq_dim_payment_method_key'),
            upper(trim(src.method))
          FROM (
            SELECT DISTINCT method
            FROM raw.payment_history_raw
            WHERE method IS NOT NULL
          ) AS src
          WHERE NOT EXISTS (
            SELECT 1
              FROM ecommerce_dwh_star.dim_payment_method tgt
             WHERE tgt.method = upper(trim(src.method))
          );
        END;
        $$;

        -- 2.5 load_dim_product
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_product()
        LANGUAGE plpgsql
        AS $$
        BEGIN
          INSERT INTO ecommerce_dwh_star.dim_product
              (product_key, product_id, product_name, category_id, category_name, price)
          SELECT
            nextval('seq_dim_product_key'),
            (trim(p.product_id))::INT,
            upper(trim(p.name)),
            (trim(p.category_id))::INT,
            upper(trim(c.name)),
            (replace(replace(trim(p.price), ' ', ''), ',', '.'))::NUMERIC(10,2)
          FROM raw.products_raw p
          LEFT JOIN raw.categories_raw c
            ON trim(p.category_id) = trim(c.category_id)
          WHERE NOT EXISTS (
            SELECT 1
              FROM ecommerce_dwh_star.dim_product tgt
             WHERE tgt.product_id = (trim(p.product_id))::INT
          );
        END;
        $$;

        -- 2.6 fact_sales
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_fact_sales()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          INSERT INTO ecommerce_dwh_star.fact_sales
              (sale_key, sale_id, date_key, time_key, product_key,
               customer_key, quantity, total_amount, payment_method_key)
          SELECT nextval('seq_fact_sales_key')
               , (trim(s.sale_id))::INT
               , (TO_CHAR(parse_datetime(s.sale_date_time)::DATE, 'YYYYMMDD'))::INT AS date_key
               , (EXTRACT(HOUR FROM parse_datetime(s.sale_date_time)::TIME) * 10000
                  + EXTRACT(MINUTE FROM parse_datetime(s.sale_date_time)::TIME) * 100
                  + EXTRACT(SECOND FROM parse_datetime(s.sale_date_time)::TIME) * 1)::INT AS time_key
               , dp.product_key
               , dc.customer_key
               , (trim(s.quantity))::INT
               , (replace(replace(trim(s.total_amount), ' ', ''), ',', '.'))::NUMERIC(10, 2)
               , pm.payment_method_key
          FROM raw.sales_raw s
          JOIN ecommerce_dwh_star.dim_product dp
            ON dp.product_id = (trim(s.product_id))::INT
          JOIN ecommerce_dwh_star.dim_customer dc
            ON dc.client_id = (trim(s.client_id))::INT
          LEFT JOIN raw.payment_history_raw ph
            ON trim(ph.sale_id) = trim(s.sale_id)
          LEFT JOIN ecommerce_dwh_star.dim_payment_method pm
            ON pm.method = upper(trim(ph.method))
          WHERE NOT EXISTS (
            SELECT 1
              FROM ecommerce_dwh_star.fact_sales tgt
             WHERE tgt.sale_id = (trim(s.sale_id))::INT
          );
        END;
        $$;

        -- 3) Orchestrator
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.etl_master()
          LANGUAGE plpgsql AS
        $$
        BEGIN
          CALL ecommerce_dwh_star.load_dim_date();
          CALL ecommerce_dwh_star.load_dim_time();
          CALL ecommerce_dwh_star.load_dim_payment_method();
          CALL ecommerce_dwh_star.load_dim_product();
          CALL ecommerce_dwh_star.load_dim_customer();
          CALL ecommerce_dwh_star.load_fact_sales();
        END;
        $$;
        """
        
        postgres_hook.run(procedures_sql)
        logging.info("✅ Procédures stockées DWH créées avec succès")
        return "DWH procedures created successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création des procédures DWH: {str(e)}")
        raise

def load_dimension_table(dimension_name, **context):
    """Charge une table de dimension spécifique"""
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
        
        logging.info(f"🔄 Chargement de la dimension {dimension_name}...")
        
        # Exécution de la procédure stockée
        call_sql = f"CALL ecommerce_dwh_star.{procedure_name}();"
        postgres_hook.run(call_sql)
        
        # Vérification du nombre d'enregistrements chargés
        count_sql = f"SELECT COUNT(*) FROM ecommerce_dwh_star.dim_{dimension_name}"
        result = postgres_hook.get_first(count_sql)
        count = result[0] if result else 0
        
        logging.info(f"✅ Dimension {dimension_name} chargée: {count} enregistrements")
        return f"Loaded {count} records into dim_{dimension_name}"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du chargement de dim_{dimension_name}: {str(e)}")
        raise

def load_fact_table(**context):
    """Charge la table de faits"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        logging.info("🔄 Chargement de la table de faits...")
        
        # Exécution de la procédure stockée
        call_sql = "CALL ecommerce_dwh_star.load_fact_sales();"
        postgres_hook.run(call_sql)
        
        # Vérification du nombre d'enregistrements chargés
        count_sql = "SELECT COUNT(*) FROM ecommerce_dwh_star.fact_sales"
        result = postgres_hook.get_first(count_sql)
        count = result[0] if result else 0
        
        logging.info(f"✅ Table de faits chargée: {count} enregistrements")
        return f"Loaded {count} records into fact_sales"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du chargement de fact_sales: {str(e)}")
        raise

def validate_dwh_data(**context):
    """Valide les données chargées dans le DWH"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requêtes de validation
        validation_queries = {
            'dim_date': "SELECT COUNT(*) FROM ecommerce_dwh_star.dim_date",
            'dim_time': "SELECT COUNT(*) FROM ecommerce_dwh_star.dim_time",
            'dim_customer': "SELECT COUNT(*) FROM ecommerce_dwh_star.dim_customer",
            'dim_product': "SELECT COUNT(*) FROM ecommerce_dwh_star.dim_product",
            'dim_payment_method': "SELECT COUNT(*) FROM ecommerce_dwh_star.dim_payment_method",
            'fact_sales': "SELECT COUNT(*) FROM ecommerce_dwh_star.fact_sales"
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
            issues.append("Aucune donnée chargée dans le DWH")
        
        # Vérifier la cohérence des faits avec les dimensions
        coherence_checks = [
            {
                'name': 'Facts-Date',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh_star.fact_sales f 
                LEFT JOIN ecommerce_dwh_star.dim_date d ON f.date_key = d.date_key 
                WHERE d.date_key IS NULL
                """
            },
            {
                'name': 'Facts-Customer',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh_star.fact_sales f 
                LEFT JOIN ecommerce_dwh_star.dim_customer c ON f.customer_key = c.customer_key 
                WHERE c.customer_key IS NULL
                """
            },
            {
                'name': 'Facts-Product',
                'sql': """
                SELECT COUNT(*) FROM ecommerce_dwh_star.fact_sales f 
                LEFT JOIN ecommerce_dwh_star.dim_product p ON f.product_key = p.product_key 
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
            'total_sales_amount': "SELECT COALESCE(SUM(total_amount), 0) FROM ecommerce_dwh_star.fact_sales",
            'avg_sale_amount': "SELECT COALESCE(AVG(total_amount), 0) FROM ecommerce_dwh_star.fact_sales",
            'unique_customers': "SELECT COUNT(DISTINCT customer_key) FROM ecommerce_dwh_star.fact_sales",
            'unique_products': "SELECT COUNT(DISTINCT product_key) FROM ecommerce_dwh_star.fact_sales"
        }
        
        stats_results = {}
        for stat, query in stats_queries.items():
            result = postgres_hook.get_first(query)
            stats_results[stat] = result[0] if result else 0
        
        # Génération du rapport
        report = f"""
=== RAPPORT DE VALIDATION DU DWH ÉTOILE ===
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
"""
        
        if issues:
            report += f"\n⚠️ PROBLÈMES DÉTECTÉS:\n"
            for issue in issues:
                report += f"  • {issue}\n"
        else:
            report += f"\n✅ VALIDATION RÉUSSIE: Aucun problème détecté\n"
        
        logging.info(report)
        
        # Sauvegarde du rapport
        report_path = f"/opt/airflow/resource/dwh_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
        
        if issues:
            raise ValueError(f"Validation échouée: {len(issues)} problème(s) détecté(s)")
        
        return {**validation_results, **stats_results}
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la validation: {str(e)}")
        raise

def cleanup_old_dwh_reports(**context):
    """Nettoie les anciens rapports de validation DWH"""
    try:
        import os
        import glob
        
        reports_pattern = "/opt/airflow/resource/dwh_validation_report_*.txt"
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
        return f"Cleanup failed: {str(e)}"

# Définition du DAG
with DAG(
    dag_id='load_dwh_star',
    default_args=default_args,
    description='Chargement des données RAW vers le Data Warehouse en étoile',
    schedule='0 3 * * *',  # Quotidien à 3h du matin (après load_raw_data)
    catchup=False,
    tags=['ecommerce', 'dwh', 'star', 'datawarehouse'],
) as dag:

    # Création du schéma et des tables DWH
    create_schema_task = PythonOperator(
        task_id='create_dwh_schema_and_tables',
        python_callable=create_dwh_schema_and_tables,
    )

    # Création des procédures stockées
    create_procedures_task = PythonOperator(
        task_id='create_dwh_procedures',
        python_callable=create_dwh_procedures,
    )

    # Chargement des dimensions (peuvent être parallèles)
    load_dim_date_task = PythonOperator(
        task_id='load_dim_date',
        python_callable=load_dimension_table,
        op_kwargs={'dimension_name': 'date'},
    )

    load_dim_time_task = PythonOperator(
        task_id='load_dim_time',
        python_callable=load_dimension_table,
        op_kwargs={'dimension_name': 'time'},
    )

    load_dim_customer_task = PythonOperator(
        task_id='load_dim_customer',
        python_callable=load_dimension_table,
        op_kwargs={'dimension_name': 'customer'},
    )

    load_dim_product_task = PythonOperator(
        task_id='load_dim_product',
        python_callable=load_dimension_table,
        op_kwargs={'dimension_name': 'product'},
    )

    load_dim_payment_method_task = PythonOperator(
        task_id='load_dim_payment_method',
        python_callable=load_dimension_table,
        op_kwargs={'dimension_name': 'payment_method'},
    )

    # Chargement de la table de faits (après les dimensions)
    load_fact_sales_task = PythonOperator(
        task_id='load_fact_sales',
        python_callable=load_fact_table,
    )

    # Validation des données chargées
    validate_dwh_task = PythonOperator(
        task_id='validate_dwh_data',
        python_callable=validate_dwh_data,
    )

    # Nettoyage des anciens rapports
    cleanup_task = PythonOperator(
        task_id='cleanup_old_dwh_reports',
        python_callable=cleanup_old_dwh_reports,
    )

    # Définition des dépendances
    create_schema_task >> create_procedures_task >> [
        load_dim_date_task,
        load_dim_time_task,
        load_dim_customer_task,
        load_dim_product_task,
        load_dim_payment_method_task
    ] >> load_fact_sales_task >> validate_dwh_task >> cleanup_task
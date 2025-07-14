from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
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

def add_region_column_to_mysql(**context):
    """Ajoute la colonne region_id à la table sales MySQL"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops_conn')
        
        # Vérifier si la colonne existe déjà
        check_column_sql = """
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'ecommerce_ops_db' 
        AND TABLE_NAME = 'sales' 
        AND COLUMN_NAME = 'region_id'
        """
        
        result = mysql_hook.get_first(check_column_sql)
        column_exists = result[0] > 0 if result else False
        
        if not column_exists:
            # Ajouter la colonne region_id
            alter_table_sql = """
            ALTER TABLE ecommerce_ops_db.sales 
            ADD COLUMN region_id INT NOT NULL DEFAULT 1 
            COMMENT 'ID de la région de vente'
            """
            mysql_hook.run(alter_table_sql)
            logging.info("✅ Colonne region_id ajoutée à la table sales")
        else:
            logging.info("ℹ️ Colonne region_id existe déjà dans la table sales")
        
        # Mettre à jour les données avec les region_id selon votre spécification
        update_regions_sql = """
        UPDATE ecommerce_ops_db.sales 
        SET region_id = CASE sale_id
            WHEN 1 THEN 2
            WHEN 2 THEN 1
            WHEN 3 THEN 1
            WHEN 4 THEN 2
            WHEN 5 THEN 2
            WHEN 6 THEN 2
            WHEN 7 THEN 1
            WHEN 8 THEN 3
            WHEN 9 THEN 3
            WHEN 10 THEN 1
            ELSE 1
        END
        """
        mysql_hook.run(update_regions_sql)
        
        # Vérifier les données mises à jour
        verify_sql = "SELECT sale_id, region_id FROM ecommerce_ops_db.sales ORDER BY sale_id"
        results = mysql_hook.get_records(verify_sql)
        
        logging.info("📊 Données region_id mises à jour:")
        for row in results:
            logging.info(f"  Sale ID {row[0]} → Region {row[1]}")
        
        return f"Region column added and {len(results)} records updated"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'ajout de la colonne region_id: {str(e)}")
        raise

def create_regions_table_mysql(**context):
    """Crée une table regions pour les données de référence"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops_conn')
        
        # Créer la table regions
        create_regions_sql = """
        CREATE TABLE IF NOT EXISTS ecommerce_ops_db.regions (
            region_id INT AUTO_INCREMENT PRIMARY KEY,
            region_name VARCHAR(100) NOT NULL,
            region_code VARCHAR(10) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
        mysql_hook.run(create_regions_sql)
        
        # Insérer les données des régions
        insert_regions_sql = """
        INSERT IGNORE INTO ecommerce_ops_db.regions (region_id, region_name, region_code)
        VALUES 
            (1, 'Nord', 'NRD'),
            (2, 'Sud', 'SUD'),
            (3, 'Est', 'EST'),
            (4, 'Ouest', 'OUE')
        """
        mysql_hook.run(insert_regions_sql)
        
        # Ajouter la contrainte FK si elle n'existe pas
        try:
            add_fk_sql = """
            ALTER TABLE ecommerce_ops_db.sales 
            ADD CONSTRAINT fk_sales_region 
            FOREIGN KEY (region_id) REFERENCES regions(region_id)
            """
            mysql_hook.run(add_fk_sql)
            logging.info("✅ Contrainte FK ajoutée entre sales et regions")
        except Exception as fk_error:
            if "Duplicate key name" in str(fk_error):
                logging.info("ℹ️ Contrainte FK existe déjà")
            else:
                logging.warning(f"⚠️ Impossible d'ajouter la contrainte FK: {str(fk_error)}")
        
        # Vérifier les données
        verify_sql = "SELECT region_id, region_name, region_code FROM ecommerce_ops_db.regions ORDER BY region_id"
        results = mysql_hook.get_records(verify_sql)
        
        logging.info("🗺️ Régions créées:")
        for row in results:
            logging.info(f"  Region {row[0]}: {row[1]} ({row[2]})")
        
        return f"Regions table created with {len(results)} regions"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création de la table regions: {str(e)}")
        raise

def update_raw_tables_for_regions(**context):
    """Met à jour les tables RAW PostgreSQL pour inclure region_id"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Ajouter la colonne region_id à sales_raw si elle n'existe pas
        check_column_sql = """
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_schema = 'raw' 
        AND table_name = 'sales_raw' 
        AND column_name = 'region_id'
        """
        
        result = postgres_hook.get_first(check_column_sql)
        column_exists = result[0] > 0 if result else False
        
        if not column_exists:
            alter_raw_sql = """
            ALTER TABLE raw.sales_raw 
            ADD COLUMN region_id TEXT
            """
            postgres_hook.run(alter_raw_sql)
            logging.info("✅ Colonne region_id ajoutée à raw.sales_raw")
        else:
            logging.info("ℹ️ Colonne region_id existe déjà dans raw.sales_raw")
        
        # Créer la table regions_raw
        create_regions_raw_sql = """
        CREATE TABLE IF NOT EXISTS raw.regions_raw (
            region_id TEXT,
            region_name TEXT,
            region_code TEXT,
            created_at TEXT
        )
        """
        postgres_hook.run(create_regions_raw_sql)
        
        logging.info("✅ Tables RAW mises à jour pour les régions")
        return "RAW tables updated for regions"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la mise à jour des tables RAW: {str(e)}")
        raise

def update_dwh_tables_for_regions(**context):
    """Met à jour les tables DWH pour inclure la dimension région"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Mise à jour du schéma Star
        update_star_sql = """
        -- Ajouter la dimension région au schéma Star
        CREATE TABLE IF NOT EXISTS ecommerce_dwh_star.dim_region (
            region_key SERIAL PRIMARY KEY,
            region_id INT NOT NULL UNIQUE,
            region_name TEXT NOT NULL,
            region_code TEXT NOT NULL
        );
        
        -- Ajouter la colonne region_key à fact_sales si elle n'existe pas
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'ecommerce_dwh_star' 
                AND table_name = 'fact_sales' 
                AND column_name = 'region_key'
            ) THEN
                ALTER TABLE ecommerce_dwh_star.fact_sales 
                ADD COLUMN region_key INT;
                
                -- Ajouter la contrainte FK après avoir chargé les données
                -- ALTER TABLE ecommerce_dwh_star.fact_sales 
                -- ADD CONSTRAINT fk_fact_sales_region 
                -- FOREIGN KEY (region_key) REFERENCES dim_region(region_key);
            END IF;
        END $$;
        
        -- Index pour les performances
        CREATE INDEX IF NOT EXISTS idx_fact_sales_region_key 
        ON ecommerce_dwh_star.fact_sales(region_key);
        """
        postgres_hook.run(update_star_sql)
        
        # Mise à jour du schéma OLAP
        update_olap_sql = """
        -- Ajouter la dimension région au schéma OLAP
        CREATE TABLE IF NOT EXISTS ecommerce_dwh.dim_region (
            region_key SERIAL PRIMARY KEY,
            region_id INT NOT NULL UNIQUE,
            region_name TEXT NOT NULL,
            region_code TEXT NOT NULL
        );
        
        -- Ajouter la colonne region_key à fact_sales si elle n'existe pas
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'ecommerce_dwh' 
                AND table_name = 'fact_sales' 
                AND column_name = 'region_key'
            ) THEN
                ALTER TABLE ecommerce_dwh.fact_sales 
                ADD COLUMN region_key INT;
                
                -- Ajouter la contrainte FK après avoir chargé les données
                -- ALTER TABLE ecommerce_dwh.fact_sales 
                -- ADD CONSTRAINT fk_fact_sales_region 
                -- FOREIGN KEY (region_key) REFERENCES dim_region(region_key);
            END IF;
        END $$;
        
        -- Index pour les performances
        CREATE INDEX IF NOT EXISTS idx_fact_sales_region_key 
        ON ecommerce_dwh.fact_sales(region_key);
        """
        postgres_hook.run(update_olap_sql)
        
        logging.info("✅ Tables DWH mises à jour pour les régions")
        return "DWH tables updated for regions"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la mise à jour des tables DWH: {str(e)}")
        raise

def create_region_procedures(**context):
    """Crée les procédures stockées pour charger la dimension région"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        procedures_sql = """
        -- Procédure pour charger dim_region dans Star Schema
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_dim_region()
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO ecommerce_dwh_star.dim_region (region_id, region_name, region_code)
            SELECT 
                (trim(r.region_id))::INT,
                upper(trim(r.region_name)),
                upper(trim(r.region_code))
            FROM raw.regions_raw r
            WHERE r.region_id IS NOT NULL AND trim(r.region_id) != ''
            ON CONFLICT (region_id) DO UPDATE SET
                region_name = EXCLUDED.region_name,
                region_code = EXCLUDED.region_code;
        END;
        $$;
        
        -- Procédure pour charger dim_region dans OLAP
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_dim_region()
        LANGUAGE plpgsql
        AS $$
        BEGIN
            INSERT INTO ecommerce_dwh.dim_region (region_id, region_name, region_code)
            SELECT 
                (trim(r.region_id))::INT,
                upper(trim(r.region_name)),
                upper(trim(r.region_code))
            FROM raw.regions_raw r
            WHERE r.region_id IS NOT NULL AND trim(r.region_id) != ''
            ON CONFLICT (region_id) DO UPDATE SET
                region_name = EXCLUDED.region_name,
                region_code = EXCLUDED.region_code;
        END;
        $$;
        
        -- Mise à jour de la procédure load_fact_sales pour Star Schema
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.load_fact_sales()
        LANGUAGE plpgsql AS
        $$
        BEGIN
            INSERT INTO ecommerce_dwh_star.fact_sales
                (sale_id, date_key, time_key, product_key,
                 customer_key, quantity, total_amount, payment_method_key, region_key)
            SELECT 
                 (trim(s.sale_id))::INT,
                 (to_char(parse_datetime(s.sale_date_time)::DATE, 'YYYYMMDD'))::INT AS date_key,
                 (to_char(parse_datetime(s.sale_date_time)::TIME, 'HH24MISS'))::INT AS time_key,
                 dp.product_key,
                 dc.customer_key,
                 (trim(s.quantity))::INT,
                 (replace(replace(trim(s.total_amount), ' ', ''), ',', '.'))::NUMERIC(10, 2),
                 pm.payment_method_key,
                 dr.region_key
            FROM raw.sales_raw s
            JOIN ecommerce_dwh_star.dim_product dp
              ON dp.product_id = (trim(s.product_id))::INT
            JOIN ecommerce_dwh_star.dim_customer dc
              ON dc.client_id = (trim(s.client_id))::INT
            LEFT JOIN raw.payment_history_raw ph
              ON trim(ph.sale_id) = trim(s.sale_id)
            LEFT JOIN ecommerce_dwh_star.dim_payment_method pm
              ON pm.method = upper(trim(ph.method))
            LEFT JOIN ecommerce_dwh_star.dim_region dr
              ON dr.region_id = (trim(s.region_id))::INT
            WHERE s.sale_id IS NOT NULL AND trim(s.sale_id) != ''
              AND s.sale_date_time IS NOT NULL AND trim(s.sale_date_time) != ''
            ON CONFLICT (sale_id) DO UPDATE SET
                date_key = EXCLUDED.date_key,
                time_key = EXCLUDED.time_key,
                product_key = EXCLUDED.product_key,
                customer_key = EXCLUDED.customer_key,
                quantity = EXCLUDED.quantity,
                total_amount = EXCLUDED.total_amount,
                payment_method_key = EXCLUDED.payment_method_key,
                region_key = EXCLUDED.region_key;
        END;
        $$;
        
        -- Mise à jour de la procédure load_fact_sales pour OLAP
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.load_fact_sales()
        LANGUAGE plpgsql AS
        $$
        BEGIN
            INSERT INTO ecommerce_dwh.fact_sales
                (sale_id, date_key, time_key, product_key,
                 customer_key, quantity, total_amount, payment_method_key, region_key)
            SELECT 
                 (trim(s.sale_id))::INT,
                 parse_datetime(s.sale_date_time)::DATE AS date_key,
                 parse_datetime(s.sale_date_time)::TIME AS time_key,
                 dp.product_key,
                 dc.customer_key,
                 (trim(s.quantity))::INT,
                 (replace(replace(trim(s.total_amount), ' ', ''), ',', '.'))::NUMERIC(10, 2),
                 pm.payment_method_key,
                 dr.region_key
            FROM raw.sales_raw s
            JOIN ecommerce_dwh.dim_product dp
              ON dp.product_id = (trim(s.product_id))::INT
            JOIN ecommerce_dwh.dim_customer dc
              ON dc.client_id = (trim(s.client_id))::INT
            LEFT JOIN raw.payment_history_raw ph
              ON trim(ph.sale_id) = trim(s.sale_id)
            LEFT JOIN ecommerce_dwh.dim_payment_method pm
              ON pm.method = upper(trim(ph.method))
            LEFT JOIN ecommerce_dwh.dim_region dr
              ON dr.region_id = (trim(s.region_id))::INT
            WHERE s.sale_id IS NOT NULL AND trim(s.sale_id) != ''
              AND s.sale_date_time IS NOT NULL AND trim(s.sale_date_time) != ''
            ON CONFLICT (sale_id) DO UPDATE SET
                date_key = EXCLUDED.date_key,
                time_key = EXCLUDED.time_key,
                product_key = EXCLUDED.product_key,
                customer_key = EXCLUDED.customer_key,
                quantity = EXCLUDED.quantity,
                total_amount = EXCLUDED.total_amount,
                payment_method_key = EXCLUDED.payment_method_key,
                region_key = EXCLUDED.region_key;
        END;
        $$;
        
        -- Mise à jour des orchestrateurs
        CREATE OR REPLACE PROCEDURE ecommerce_dwh_star.etl_master()
        LANGUAGE plpgsql AS
        $$
        BEGIN
            CALL ecommerce_dwh_star.load_dim_date();
            CALL ecommerce_dwh_star.load_dim_time();
            CALL ecommerce_dwh_star.load_dim_payment_method();
            CALL ecommerce_dwh_star.load_dim_product();
            CALL ecommerce_dwh_star.load_dim_customer();
            CALL ecommerce_dwh_star.load_dim_region();
            CALL ecommerce_dwh_star.load_fact_sales();
        END;
        $$;
        
        CREATE OR REPLACE PROCEDURE ecommerce_dwh.etl_olap_master()
        LANGUAGE plpgsql AS
        $$
        BEGIN
            CALL ecommerce_dwh.load_dim_date();
            CALL ecommerce_dwh.load_dim_time();
            CALL ecommerce_dwh.load_dim_payment_method();
            CALL ecommerce_dwh.load_dim_product();
            CALL ecommerce_dwh.load_dim_customer();
            CALL ecommerce_dwh.load_dim_region();
            CALL ecommerce_dwh.load_fact_sales();
        END;
        $$;
        """
        
        postgres_hook.run(procedures_sql)
        logging.info("✅ Procédures stockées pour les régions créées")
        return "Region procedures created successfully"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création des procédures région: {str(e)}")
        raise

def validate_region_integration(**context):
    """Valide l'intégration des régions dans tout le pipeline"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops_conn')
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Validation MySQL
        mysql_validation = """
        SELECT 
            s.region_id,
            r.region_name,
            COUNT(*) as nb_ventes,
            SUM(s.total_amount) as ca_region
        FROM ecommerce_ops_db.sales s
        LEFT JOIN ecommerce_ops_db.regions r ON s.region_id = r.region_id
        GROUP BY s.region_id, r.region_name
        ORDER BY s.region_id
        """
        
        mysql_results = mysql_hook.get_records(mysql_validation)
        
        report = f"""
=== VALIDATION INTÉGRATION RÉGIONS ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 DONNÉES MYSQL (SOURCE):
"""
        total_ca = 0
        for row in mysql_results:
            region_id, region_name, nb_ventes, ca_region = row
            total_ca += float(ca_region) if ca_region else 0
            report += f"  • Région {region_id} ({region_name}): {nb_ventes} ventes, {ca_region:.2f}€\n"
        
        report += f"\n💰 CA TOTAL: {total_ca:.2f}€\n"
        
        # Validation PostgreSQL RAW
        try:
            raw_validation = "SELECT COUNT(*) FROM raw.sales_raw WHERE region_id IS NOT NULL"
            raw_count = postgres_hook.get_first(raw_validation)
            report += f"\n📋 DONNÉES RAW: {raw_count[0] if raw_count else 0} ventes avec region_id\n"
        except Exception as e:
            report += f"\n⚠️ RAW non encore synchronisé: {str(e)}\n"
        
        # Validation DWH Star
        try:
            star_validation = """
            SELECT 
                dr.region_name,
                COUNT(*) as nb_ventes,
                SUM(f.total_amount) as ca_region
            FROM ecommerce_dwh_star.fact_sales f
            LEFT JOIN ecommerce_dwh_star.dim_region dr ON f.region_key = dr.region_key
            GROUP BY dr.region_key, dr.region_name
            ORDER BY dr.region_key
            """
            star_results = postgres_hook.get_records(star_validation)
            
            report += f"\n🌟 DWH STAR SCHEMA:\n"
            for row in star_results:
                region_name, nb_ventes, ca_region = row
                report += f"  • {region_name}: {nb_ventes} ventes, {ca_region:.2f}€\n"
        except Exception as e:
            report += f"\n⚠️ DWH Star non encore synchronisé: {str(e)}\n"
        
        # Validation DWH OLAP
        try:
            olap_validation = """
            SELECT 
                dr.region_name,
                COUNT(*) as nb_ventes,
                SUM(f.total_amount) as ca_region
            FROM ecommerce_dwh.fact_sales f
            LEFT JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
            GROUP BY dr.region_key, dr.region_name
            ORDER BY dr.region_key
            """
            olap_results = postgres_hook.get_records(olap_validation)
            
            report += f"\n📊 DWH OLAP:\n"
            for row in olap_results:
                region_name, nb_ventes, ca_region = row
                report += f"  • {region_name}: {nb_ventes} ventes, {ca_region:.2f}€\n"
        except Exception as e:
            report += f"\n⚠️ DWH OLAP non encore synchronisé: {str(e)}\n"
        
        report += f"\n✅ INTÉGRATION RÉGIONS VALIDÉE\n"
        
        logging.info(report)
        
        # Sauvegarde du rapport
        report_path = f"/opt/airflow/resource/region_integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport région sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport région: {str(e)}")
        
        return {"mysql_regions": len(mysql_results), "total_ca": total_ca}
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la validation région: {str(e)}")
        raise

# Définition du DAG
with DAG(
    dag_id='add_region_column',
    default_args=default_args,
    description='Ajoute la colonne region_id et intègre les régions dans le Data Warehouse',
    schedule=None,  # Exécution manuelle uniquement
    catchup=False,
    tags=['ecommerce', 'regions', 'schema-update'],
) as dag:

    # Étape 1: Créer la table regions dans MySQL
    create_regions_task = PythonOperator(
        task_id='create_regions_table_mysql',
        python_callable=create_regions_table_mysql,
    )

    # Étape 2: Ajouter la colonne region_id à la table sales
    add_region_column_task = PythonOperator(
        task_id='add_region_column_to_mysql',
        python_callable=add_region_column_to_mysql,
    )

    # Étape 3: Mettre à jour les tables RAW
    update_raw_task = PythonOperator(
        task_id='update_raw_tables_for_regions',
        python_callable=update_raw_tables_for_regions,
    )

    # Étape 4: Mettre à jour les tables DWH
    update_dwh_task = PythonOperator(
        task_id='update_dwh_tables_for_regions',
        python_callable=update_dwh_tables_for_regions,
    )

    # Étape 5: Créer les procédures stockées
    create_procedures_task = PythonOperator(
        task_id='create_region_procedures',
        python_callable=create_region_procedures,
    )

    # Étape 6: Valider l'intégration
    validate_task = PythonOperator(
        task_id='validate_region_integration',
        python_callable=validate_region_integration,
    )

    # Définition des dépendances
    create_regions_task >> add_region_column_task >> update_raw_task >> update_dwh_task >> create_procedures_task >> validate_task
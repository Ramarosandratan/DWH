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

def update_regions_data_mysql(**context):
    """Met à jour les données des régions dans MySQL avec les nouveaux noms"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id='mysql_ops_conn')
        
        # Vérifier si la table regions existe
        check_table_sql = """
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'ecommerce_ops_db' 
        AND TABLE_NAME = 'regions'
        """
        
        result = mysql_hook.get_first(check_table_sql)
        table_exists = result[0] > 0 if result else False
        
        if not table_exists:
            logging.error("❌ Table regions n'existe pas. Exécutez d'abord add_region_column")
            raise Exception("Table regions not found")
        
        # Mettre à jour les noms des régions selon les nouvelles spécifications
        update_regions_sql = """
        UPDATE ecommerce_ops_db.regions 
        SET 
            region_name = CASE region_id
                WHEN 1 THEN 'ANALAMANGA'
                WHEN 2 THEN 'ALAOTRA MANGORO'
                WHEN 3 THEN 'BOENY'
                ELSE region_name
            END,
            region_code = CASE region_id
                WHEN 1 THEN 'ANA'
                WHEN 2 THEN 'ALM'
                WHEN 3 THEN 'BOE'
                ELSE region_code
            END
        WHERE region_id IN (1, 2, 3)
        """
        
        mysql_hook.run(update_regions_sql)
        
        # Vérifier les données mises à jour
        verify_sql = """
        SELECT region_id, region_name, region_code 
        FROM ecommerce_ops_db.regions 
        ORDER BY region_id
        """
        results = mysql_hook.get_records(verify_sql)
        
        logging.info("🗺️ Régions mises à jour dans MySQL:")
        for row in results:
            logging.info(f"  Region {row[0]}: {row[1]} ({row[2]})")
        
        # Vérifier la cohérence avec les ventes
        sales_regions_sql = """
        SELECT 
            s.region_id,
            r.region_name,
            COUNT(*) as nb_ventes,
            SUM(s.total_amount) as ca_total
        FROM ecommerce_ops_db.sales s
        LEFT JOIN ecommerce_ops_db.regions r ON s.region_id = r.region_id
        GROUP BY s.region_id, r.region_name
        ORDER BY s.region_id
        """
        
        sales_results = mysql_hook.get_records(sales_regions_sql)
        
        logging.info("📊 Ventes par région (MySQL):")
        for row in sales_results:
            region_id, region_name, nb_ventes, ca_total = row
            logging.info(f"  {region_name}: {nb_ventes} ventes, {ca_total:.2f}€")
        
        return f"Regions updated: {len(results)} regions, {len(sales_results)} regions with sales"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la mise à jour des régions MySQL: {str(e)}")
        raise

def update_raw_regions_data(**context):
    """Met à jour les données des régions dans les tables RAW PostgreSQL"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Vider et recharger la table regions_raw avec les nouvelles données
        truncate_and_reload_sql = """
        -- Vider la table regions_raw
        TRUNCATE TABLE raw.regions_raw;
        
        -- Insérer les nouvelles données des régions
        INSERT INTO raw.regions_raw (region_id, region_name, region_code, created_at)
        VALUES 
            ('1', 'ANALAMANGA', 'ANA', '2025-01-01 00:00:00'),
            ('2', 'ALAOTRA MANGORO', 'ALM', '2025-01-01 00:00:00'),
            ('3', 'BOENY', 'BOE', '2025-01-01 00:00:00'),
            ('4', 'OUEST', 'OUE', '2025-01-01 00:00:00');
        """
        
        postgres_hook.run(truncate_and_reload_sql)
        
        # Vérifier les données
        verify_sql = "SELECT region_id, region_name, region_code FROM raw.regions_raw ORDER BY region_id::INT"
        results = postgres_hook.get_records(verify_sql)
        
        logging.info("🗺️ Régions dans RAW PostgreSQL:")
        for row in results:
            logging.info(f"  Region {row[0]}: {row[1]} ({row[2]})")
        
        return f"RAW regions updated: {len(results)} regions"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la mise à jour des régions RAW: {str(e)}")
        raise

def update_dwh_regions_data(**context):
    """Met à jour les dimensions régions dans les DWH Star et OLAP"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Mettre à jour Star Schema
        update_star_sql = """
        -- Vider et recharger dim_region Star Schema
        TRUNCATE TABLE ecommerce_dwh_star.dim_region RESTART IDENTITY CASCADE;
        
        INSERT INTO ecommerce_dwh_star.dim_region (region_id, region_name, region_code)
        VALUES 
            (1, 'ANALAMANGA', 'ANA'),
            (2, 'ALAOTRA MANGORO', 'ALM'),
            (3, 'BOENY', 'BOE'),
            (4, 'OUEST', 'OUE');
        """
        
        postgres_hook.run(update_star_sql)
        
        # Mettre à jour OLAP
        update_olap_sql = """
        -- Vider et recharger dim_region OLAP
        TRUNCATE TABLE ecommerce_dwh.dim_region RESTART IDENTITY CASCADE;
        
        INSERT INTO ecommerce_dwh.dim_region (region_id, region_name, region_code)
        VALUES 
            (1, 'ANALAMANGA', 'ANA'),
            (2, 'ALAOTRA MANGORO', 'ALM'),
            (3, 'BOENY', 'BOE'),
            (4, 'OUEST', 'OUE');
        """
        
        postgres_hook.run(update_olap_sql)
        
        # Vérifier Star Schema
        verify_star_sql = """
        SELECT region_key, region_id, region_name, region_code 
        FROM ecommerce_dwh_star.dim_region 
        ORDER BY region_id
        """
        star_results = postgres_hook.get_records(verify_star_sql)
        
        logging.info("🌟 Régions dans DWH Star Schema:")
        for row in star_results:
            logging.info(f"  Key {row[0]}: Region {row[1]} - {row[2]} ({row[3]})")
        
        # Vérifier OLAP
        verify_olap_sql = """
        SELECT region_key, region_id, region_name, region_code 
        FROM ecommerce_dwh.dim_region 
        ORDER BY region_id
        """
        olap_results = postgres_hook.get_records(verify_olap_sql)
        
        logging.info("📊 Régions dans DWH OLAP:")
        for row in olap_results:
            logging.info(f"  Key {row[0]}: Region {row[1]} - {row[2]} ({row[3]})")
        
        return f"DWH regions updated: Star={len(star_results)}, OLAP={len(olap_results)}"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la mise à jour des régions DWH: {str(e)}")
        raise

def reload_fact_sales_with_new_regions(**context):
    """Recharge les tables de faits avec les nouvelles clés de régions"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Recharger fact_sales Star Schema
        reload_star_sql = """
        -- Supprimer les données existantes
        TRUNCATE TABLE ecommerce_dwh_star.fact_sales RESTART IDENTITY;
        
        -- Recharger avec les nouvelles clés de régions
        CALL ecommerce_dwh_star.load_fact_sales();
        """
        
        postgres_hook.run(reload_star_sql)
        
        # Recharger fact_sales OLAP
        reload_olap_sql = """
        -- Supprimer les données existantes
        TRUNCATE TABLE ecommerce_dwh.fact_sales RESTART IDENTITY;
        
        -- Recharger avec les nouvelles clés de régions
        CALL ecommerce_dwh.load_fact_sales();
        """
        
        postgres_hook.run(reload_olap_sql)
        
        # Vérifier les données Star Schema
        verify_star_sql = """
        SELECT 
            f.sale_id,
            dr.region_name,
            f.total_amount
        FROM ecommerce_dwh_star.fact_sales f
        JOIN ecommerce_dwh_star.dim_region dr ON f.region_key = dr.region_key
        ORDER BY f.sale_id
        """
        
        star_results = postgres_hook.get_records(verify_star_sql)
        
        logging.info("🌟 Ventes avec nouvelles régions (Star Schema):")
        for row in star_results:
            logging.info(f"  Vente {row[0]}: {row[1]} - {row[2]}€")
        
        # Vérifier les données OLAP
        verify_olap_sql = """
        SELECT 
            f.sale_id,
            dr.region_name,
            f.total_amount
        FROM ecommerce_dwh.fact_sales f
        JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        ORDER BY f.sale_id
        """
        
        olap_results = postgres_hook.get_records(verify_olap_sql)
        
        logging.info("📊 Ventes avec nouvelles régions (OLAP):")
        for row in olap_results:
            logging.info(f"  Vente {row[0]}: {row[1]} - {row[2]}€")
        
        return f"Fact sales reloaded: Star={len(star_results)}, OLAP={len(olap_results)}"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du rechargement des ventes: {str(e)}")
        raise

def validate_new_regions_integration(**context):
    """Valide l'intégration complète des nouvelles régions"""
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
        
        # Validation OLAP
        olap_validation = """
        SELECT 
            dr.region_name,
            COUNT(*) as nb_ventes,
            SUM(f.total_amount) as ca_region,
            AVG(f.total_amount) as panier_moyen
        FROM ecommerce_dwh.fact_sales f
        JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_name
        ORDER BY ca_region DESC
        """
        
        olap_results = postgres_hook.get_records(olap_validation)
        
        # Créer le rapport de validation
        report = f"""
=== VALIDATION NOUVELLES RÉGIONS ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🗺️ NOUVELLES RÉGIONS INTÉGRÉES:
  1. ANALAMANGA (ANA)
  2. ALAOTRA MANGORO (ALM)  
  3. BOENY (BOE)

📊 DONNÉES MYSQL (SOURCE):
"""
        
        total_ca_mysql = 0
        for row in mysql_results:
            region_id, region_name, nb_ventes, ca_region = row
            total_ca_mysql += float(ca_region) if ca_region else 0
            report += f"  • Région {region_id} ({region_name}): {nb_ventes} ventes, {ca_region:.2f}€\n"
        
        report += f"\n💰 CA TOTAL MYSQL: {total_ca_mysql:.2f}€\n"
        
        report += f"\n📊 DONNÉES DWH OLAP (AVEC NOMS):\n"
        total_ca_olap = 0
        for row in olap_results:
            region_name, nb_ventes, ca_region, panier_moyen = row
            total_ca_olap += float(ca_region) if ca_region else 0
            report += f"  • {region_name}: {nb_ventes} ventes, {ca_region:.2f}€, panier moyen: {panier_moyen:.2f}€\n"
        
        report += f"\n💰 CA TOTAL OLAP: {total_ca_olap:.2f}€\n"
        
        # Vérification de cohérence
        coherence_ok = abs(total_ca_mysql - total_ca_olap) < 0.01
        report += f"\n✅ COHÉRENCE DONNÉES: {'OK' if coherence_ok else 'ERREUR'}\n"
        
        if not coherence_ok:
            report += f"⚠️ Écart détecté: MySQL={total_ca_mysql:.2f}€ vs OLAP={total_ca_olap:.2f}€\n"
        
        report += f"\n🎯 PRÊT POUR GRAPHIQUES AVEC NOMS DE RÉGIONS\n"
        
        logging.info(report)
        
        # Sauvegarder le rapport
        report_path = f"/opt/airflow/resource/new_regions_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport validation sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
        
        return {
            "mysql_regions": len(mysql_results),
            "olap_regions": len(olap_results),
            "total_ca": total_ca_olap,
            "coherence_ok": coherence_ok
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la validation: {str(e)}")
        raise

# Définition du DAG
with DAG(
    dag_id='update_region_names',
    default_args=default_args,
    description='Met à jour les noms des régions avec les nouvelles données Madagascar',
    schedule=None,  # Exécution manuelle uniquement
    catchup=False,
    tags=['ecommerce', 'regions', 'madagascar', 'update'],
) as dag:

    # Étape 1: Mettre à jour les données MySQL
    update_mysql_task = PythonOperator(
        task_id='update_regions_data_mysql',
        python_callable=update_regions_data_mysql,
    )

    # Étape 2: Mettre à jour les tables RAW
    update_raw_task = PythonOperator(
        task_id='update_raw_regions_data',
        python_callable=update_raw_regions_data,
    )

    # Étape 3: Mettre à jour les dimensions DWH
    update_dwh_task = PythonOperator(
        task_id='update_dwh_regions_data',
        python_callable=update_dwh_regions_data,
    )

    # Étape 4: Recharger les tables de faits
    reload_facts_task = PythonOperator(
        task_id='reload_fact_sales_with_new_regions',
        python_callable=reload_fact_sales_with_new_regions,
    )

    # Étape 5: Valider l'intégration
    validate_task = PythonOperator(
        task_id='validate_new_regions_integration',
        python_callable=validate_new_regions_integration,
    )

    # Définition des dépendances
    update_mysql_task >> update_raw_task >> update_dwh_task >> reload_facts_task >> validate_task
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.utils.task_group import TaskGroup
from airflow.sensors.filesystem import FileSensor
from datetime import datetime, timedelta
import logging
import pandas as pd
import os


def check_database_health():
    """Vérifier la santé de la base de données"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Vérifier la connectivité
        result = mysql_hook.get_first("SELECT 1 as test")
        if result[0] != 1:
            raise Exception("Test de connectivité échoué")
        
        # Vérifier l'existence des tables principales
        tables = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        for table in tables:
            count = mysql_hook.get_first(f"SELECT COUNT(*) FROM {table}")[0]
            logging.info(f"Table {table}: {count} enregistrements")
        
        logging.info("Vérification de santé de la base de données réussie")
        
    except Exception as e:
        logging.error(f"Problème de santé de la base de données: {e}")
        raise


def generate_data_quality_report():
    """Générer un rapport de qualité des données"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        report = {}
        
        # Statistiques générales
        report['timestamp'] = datetime.now().isoformat()
        
        # Compter les enregistrements par table
        tables = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        report['table_counts'] = {}
        for table in tables:
            count = mysql_hook.get_first(f"SELECT COUNT(*) FROM {table}")[0]
            report['table_counts'][table] = count
        
        # Vérifications de qualité spécifiques
        
        # 1. Produits sans stock
        products_no_stock = mysql_hook.get_first("""
            SELECT COUNT(*) FROM products p 
            LEFT JOIN inventory i ON p.product_id = i.product_id 
            WHERE i.stock_quantity IS NULL OR i.stock_quantity = 0
        """)[0]
        report['products_no_stock'] = products_no_stock
        
        # 2. Ventes sans paiement
        sales_no_payment = mysql_hook.get_first("""
            SELECT COUNT(*) FROM sales s 
            LEFT JOIN payment_history p ON s.sale_id = p.sale_id 
            WHERE p.payment_id IS NULL
        """)[0]
        report['sales_no_payment'] = sales_no_payment
        
        # 3. Paiements échoués
        failed_payments = mysql_hook.get_first("""
            SELECT COUNT(*) FROM payment_history WHERE status = 'failed'
        """)[0]
        report['failed_payments'] = failed_payments
        
        # 4. Paiements en attente
        pending_payments = mysql_hook.get_first("""
            SELECT COUNT(*) FROM payment_history WHERE status = 'pending'
        """)[0]
        report['pending_payments'] = pending_payments
        
        # 5. Incohérences de montants
        amount_inconsistencies = mysql_hook.get_first("""
            SELECT COUNT(*) FROM sales s 
            JOIN payment_history p ON s.sale_id = p.sale_id 
            WHERE ABS(s.total_amount - p.amount) > 0.01
        """)[0]
        report['amount_inconsistencies'] = amount_inconsistencies
        
        # 6. Produits sous le seuil de réapprovisionnement
        products_below_threshold = mysql_hook.get_first("""
            SELECT COUNT(*) FROM inventory 
            WHERE stock_quantity <= reorder_threshold
        """)[0]
        report['products_below_threshold'] = products_below_threshold
        
        # Sauvegarder le rapport
        report_path = f"/opt/airflow/resource/data_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w') as f:
            f.write("=== RAPPORT DE QUALITÉ DES DONNÉES ===\n\n")
            f.write(f"Généré le: {report['timestamp']}\n\n")
            
            f.write("COMPTEURS PAR TABLE:\n")
            for table, count in report['table_counts'].items():
                f.write(f"  {table}: {count}\n")
            
            f.write(f"\nALERTES QUALITÉ:\n")
            f.write(f"  Produits sans stock: {report['products_no_stock']}\n")
            f.write(f"  Ventes sans paiement: {report['sales_no_payment']}\n")
            f.write(f"  Paiements échoués: {report['failed_payments']}\n")
            f.write(f"  Paiements en attente: {report['pending_payments']}\n")
            f.write(f"  Incohérences de montants: {report['amount_inconsistencies']}\n")
            f.write(f"  Produits sous seuil: {report['products_below_threshold']}\n")
        
        logging.info(f"Rapport de qualité généré: {report_path}")
        logging.info(f"Résumé: {report}")
        
        # Alertes si problèmes critiques
        if report['amount_inconsistencies'] > 0:
            logging.warning(f"ALERTE: {report['amount_inconsistencies']} incohérences de montants détectées")
        
        if report['sales_no_payment'] > 0:
            logging.warning(f"ALERTE: {report['sales_no_payment']} ventes sans paiement détectées")
        
        return report
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération du rapport: {e}")
        raise


def update_inventory_status():
    """Mettre à jour le statut des stocks"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Mettre à jour les timestamps
        mysql_hook.run("""
            UPDATE inventory 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE updated_at < DATE_SUB(NOW(), INTERVAL 1 DAY)
        """)
        
        # Identifier les produits nécessitant un réapprovisionnement
        low_stock_products = mysql_hook.get_records("""
            SELECT p.name, i.stock_quantity, i.reorder_threshold 
            FROM inventory i 
            JOIN products p ON i.product_id = p.product_id 
            WHERE i.stock_quantity <= i.reorder_threshold
        """)
        
        if low_stock_products:
            logging.warning(f"Produits nécessitant un réapprovisionnement:")
            for product in low_stock_products:
                logging.warning(f"  {product[0]}: stock={product[1]}, seuil={product[2]}")
        else:
            logging.info("Tous les produits ont un stock suffisant")
        
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour des stocks: {e}")
        raise


def reconcile_sales_payments():
    """Réconcilier les ventes et les paiements"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Identifier les ventes sans paiement
        sales_without_payment = mysql_hook.get_records("""
            SELECT s.sale_id, s.client_id, s.total_amount, s.sale_date_time 
            FROM sales s 
            LEFT JOIN payment_history p ON s.sale_id = p.sale_id 
            WHERE p.payment_id IS NULL
        """)
        
        if sales_without_payment:
            logging.warning(f"Ventes sans paiement trouvées: {len(sales_without_payment)}")
            for sale in sales_without_payment:
                logging.warning(f"  Vente ID {sale[0]}: Client {sale[1]}, Montant {sale[2]}, Date {sale[3]}")
        
        # Identifier les incohérences de montants
        amount_mismatches = mysql_hook.get_records("""
            SELECT s.sale_id, s.total_amount, p.amount, ABS(s.total_amount - p.amount) as difference
            FROM sales s 
            JOIN payment_history p ON s.sale_id = p.sale_id 
            WHERE ABS(s.total_amount - p.amount) > 0.01
        """)
        
        if amount_mismatches:
            logging.warning(f"Incohérences de montants trouvées: {len(amount_mismatches)}")
            for mismatch in amount_mismatches:
                logging.warning(f"  Vente {mismatch[0]}: Vente={mismatch[1]}, Paiement={mismatch[2]}, Différence={mismatch[3]}")
        
        # Statistiques des paiements par statut
        payment_stats = mysql_hook.get_records("""
            SELECT status, COUNT(*), SUM(amount) 
            FROM payment_history 
            GROUP BY status
        """)
        
        logging.info("Statistiques des paiements par statut:")
        for stat in payment_stats:
            logging.info(f"  {stat[0]}: {stat[1]} paiements, Total: {stat[2]}")
        
    except Exception as e:
        logging.error(f"Erreur lors de la réconciliation: {e}")
        raise


def optimize_database():
    """Optimiser la base de données"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Analyser les tables pour optimiser les index
        tables = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        
        for table in tables:
            mysql_hook.run(f"ANALYZE TABLE {table}")
            logging.info(f"Table {table} analysée")
        
        # Nettoyer les anciennes sauvegardes (garder seulement les 7 dernières)
        backup_tables = mysql_hook.get_records("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'ecommerce_ops_db' 
            AND table_name LIKE 'payment_history_backup_%'
            ORDER BY table_name DESC
        """)
        
        if len(backup_tables) > 7:
            for table_to_drop in backup_tables[7:]:
                mysql_hook.run(f"DROP TABLE {table_to_drop[0]}")
                logging.info(f"Ancienne sauvegarde supprimée: {table_to_drop[0]}")
        
        logging.info("Optimisation de la base de données terminée")
        
    except Exception as e:
        logging.error(f"Erreur lors de l'optimisation: {e}")
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
    dag_id='sync_ecommerce_data',
    default_args=default_args,
    description='Synchronisation et maintenance des données e-commerce',
    schedule='0 2 * * *',  # Tous les jours à 2h du matin
    catchup=False,
    tags=['ecommerce', 'maintenance', 'sync', 'monitoring'],
) as dag:

    # Vérification de santé initiale
    health_check_task = PythonOperator(
        task_id='check_database_health',
        python_callable=check_database_health,
    )

    # Groupe de tâches pour l'analyse des données
    with TaskGroup(group_id='data_analysis') as analysis_group:
        
        quality_report_task = PythonOperator(
            task_id='generate_data_quality_report',
            python_callable=generate_data_quality_report,
        )
        
        reconcile_task = PythonOperator(
            task_id='reconcile_sales_payments',
            python_callable=reconcile_sales_payments,
        )

    # Groupe de tâches pour la maintenance
    with TaskGroup(group_id='maintenance') as maintenance_group:
        
        inventory_update_task = PythonOperator(
            task_id='update_inventory_status',
            python_callable=update_inventory_status,
        )
        
        optimize_task = PythonOperator(
            task_id='optimize_database',
            python_callable=optimize_database,
        )

    # Capteur pour détecter de nouveaux fichiers CSV
    csv_sensor = FileSensor(
        task_id='wait_for_new_csv',
        filepath='/opt/airflow/resource/payment_history.csv',
        fs_conn_id='fs_default',
        poke_interval=300,  # Vérifier toutes les 5 minutes
        timeout=3600,  # Timeout après 1 heure
        mode='reschedule',
    )

    # Tâche de nettoyage des logs anciens
    cleanup_logs_task = BashOperator(
        task_id='cleanup_old_logs',
        bash_command="""
        find /opt/airflow/resource -name "data_quality_report_*.txt" -mtime +30 -delete
        echo "Anciens rapports supprimés"
        """,
    )

    # Définir les dépendances du DAG
    health_check_task >> [analysis_group, maintenance_group]
    analysis_group >> cleanup_logs_task
    maintenance_group >> cleanup_logs_task
    
    # Le capteur CSV peut déclencher le DAG de traitement CSV
    csv_sensor  # Tâche indépendante pour surveiller les nouveaux fichiers
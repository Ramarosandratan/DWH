from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import logging
import time


def wait_for_services():
    """Attendre que tous les services soient prêts"""
    max_retries = 30
    retry_delay = 10  # secondes
    
    services = {
        'mysql_ops': MySqlHook,
        # 'postgres_raw': PostgresHook  # Décommenté si PostgreSQL est configuré
    }
    
    for service_name, hook_class in services.items():
        for attempt in range(max_retries):
            try:
                if service_name == 'mysql_ops':
                    hook = hook_class(mysql_conn_id=service_name)
                    result = hook.get_first("SELECT 1")
                    if result and result[0] == 1:
                        logging.info(f"✅ Service {service_name} est prêt")
                        break
                # elif service_name == 'postgres_raw':
                #     hook = hook_class(postgres_conn_id=service_name)
                #     result = hook.get_first("SELECT 1")
                #     if result and result[0] == 1:
                #         logging.info(f"✅ Service {service_name} est prêt")
                #         break
                        
            except Exception as e:
                logging.warning(f"Tentative {attempt + 1}/{max_retries} pour {service_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logging.error(f"❌ Service {service_name} non disponible après {max_retries} tentatives")
                    raise
    
    logging.info("🎉 Tous les services sont prêts!")


def generate_demo_report():
    """Générer un rapport de démonstration"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        # Statistiques générales
        stats = {}
        
        # Compter les enregistrements
        tables = ['categories', 'products', 'clients', 'sales', 'inventory', 'payment_history']
        for table in tables:
            try:
                count = mysql_hook.get_first(f"SELECT COUNT(*) FROM {table}")[0]
                stats[table] = count
            except:
                stats[table] = 0
        
        # Statistiques business
        try:
            # Chiffre d'affaires total
            total_revenue = mysql_hook.get_first("""
                SELECT COALESCE(SUM(total_amount), 0) FROM sales
            """)[0]
            
            # Nombre de clients actifs
            active_clients = mysql_hook.get_first("""
                SELECT COUNT(DISTINCT client_id) FROM sales
            """)[0]
            
            # Produit le plus vendu
            top_product = mysql_hook.get_first("""
                SELECT p.name, SUM(s.quantity) as total_qty
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
                GROUP BY s.product_id, p.name
                ORDER BY total_qty DESC
                LIMIT 1
            """)
            
            # Méthode de paiement préférée
            top_payment_method = mysql_hook.get_first("""
                SELECT method, COUNT(*) as count
                FROM payment_history
                GROUP BY method
                ORDER BY count DESC
                LIMIT 1
            """)
            
        except Exception as e:
            logging.warning(f"Erreur lors du calcul des statistiques business: {e}")
            total_revenue = 0
            active_clients = 0
            top_product = ("N/A", 0)
            top_payment_method = ("N/A", 0)
        
        # Créer le rapport
        report_content = f"""
=== RAPPORT DE DÉMONSTRATION E-COMMERCE ===
Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 DONNÉES EN BASE:
  • Catégories: {stats.get('categories', 0)}
  • Produits: {stats.get('products', 0)}
  • Clients: {stats.get('clients', 0)}
  • Ventes: {stats.get('sales', 0)}
  • Inventaire: {stats.get('inventory', 0)}
  • Paiements: {stats.get('payment_history', 0)}

💰 STATISTIQUES BUSINESS:
  • Chiffre d'affaires total: {total_revenue:.2f} €
  • Clients actifs: {active_clients}
  • Produit le plus vendu: {top_product[0] if top_product else 'N/A'} ({top_product[1] if top_product else 0} unités)
  • Méthode de paiement préférée: {top_payment_method[0] if top_payment_method else 'N/A'} ({top_payment_method[1] if top_payment_method else 0} fois)

🎯 STATUT DU PIPELINE:
  ✅ Base de données OLTP initialisée
  ✅ Données de démonstration chargées
  ✅ Pipeline de traitement CSV opérationnel
  ✅ Surveillance de qualité active

🔄 PROCHAINES ÉTAPES:
  1. Activer le DAG 'process_payment_csv' pour le traitement quotidien
  2. Activer le DAG 'sync_ecommerce_data' pour la maintenance
  3. Surveiller les rapports de qualité quotidiens
  4. Configurer les alertes selon vos besoins

=== FIN DU RAPPORT ===
        """
        
        # Sauvegarder le rapport
        report_path = f"/opt/airflow/resource/demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logging.info(f"📋 Rapport de démonstration généré: {report_path}")
        logging.info("=== RÉSUMÉ ===")
        logging.info(f"Total des tables: {len([v for v in stats.values() if v > 0])}")
        logging.info(f"Total des enregistrements: {sum(stats.values())}")
        logging.info(f"Chiffre d'affaires: {total_revenue:.2f} €")
        
        return report_path
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération du rapport: {e}")
        raise


def validate_demo_data():
    """Valider que les données de démonstration sont cohérentes"""
    mysql_hook = MySqlHook(mysql_conn_id='mysql_ops')
    
    try:
        mysql_hook.run("USE ecommerce_ops_db;")
        
        validations = []
        
        # 1. Vérifier que chaque produit a une catégorie valide
        invalid_products = mysql_hook.get_first("""
            SELECT COUNT(*) FROM products p
            LEFT JOIN categories c ON p.category_id = c.category_id
            WHERE c.category_id IS NULL
        """)[0]
        validations.append(("Produits avec catégorie invalide", invalid_products, 0))
        
        # 2. Vérifier que chaque vente a un client et un produit valides
        invalid_sales_client = mysql_hook.get_first("""
            SELECT COUNT(*) FROM sales s
            LEFT JOIN clients c ON s.client_id = c.client_id
            WHERE c.client_id IS NULL
        """)[0]
        validations.append(("Ventes avec client invalide", invalid_sales_client, 0))
        
        invalid_sales_product = mysql_hook.get_first("""
            SELECT COUNT(*) FROM sales s
            LEFT JOIN products p ON s.product_id = p.product_id
            WHERE p.product_id IS NULL
        """)[0]
        validations.append(("Ventes avec produit invalide", invalid_sales_product, 0))
        
        # 3. Vérifier que chaque produit a un inventaire
        products_no_inventory = mysql_hook.get_first("""
            SELECT COUNT(*) FROM products p
            LEFT JOIN inventory i ON p.product_id = i.product_id
            WHERE i.product_id IS NULL
        """)[0]
        validations.append(("Produits sans inventaire", products_no_inventory, 0))
        
        # 4. Vérifier la cohérence des montants
        amount_mismatches = mysql_hook.get_first("""
            SELECT COUNT(*) FROM sales s
            JOIN payment_history p ON s.sale_id = p.sale_id
            WHERE ABS(s.total_amount - p.amount) > 0.01
        """)[0]
        validations.append(("Incohérences de montants", amount_mismatches, 0))
        
        # Analyser les résultats
        errors = []
        warnings = []
        
        for description, actual, expected in validations:
            if actual != expected:
                if "invalide" in description.lower() or "incohérence" in description.lower():
                    errors.append(f"❌ {description}: {actual} (attendu: {expected})")
                else:
                    warnings.append(f"⚠️  {description}: {actual} (attendu: {expected})")
            else:
                logging.info(f"✅ {description}: OK")
        
        if errors:
            error_msg = "Erreurs de validation détectées:\n" + "\n".join(errors)
            logging.error(error_msg)
            raise Exception(error_msg)
        
        if warnings:
            warning_msg = "Avertissements de validation:\n" + "\n".join(warnings)
            logging.warning(warning_msg)
        
        logging.info("🎉 Validation des données de démonstration réussie!")
        
    except Exception as e:
        logging.error(f"Erreur lors de la validation: {e}")
        raise


def cleanup_demo_files():
    """Nettoyer les anciens fichiers de démonstration"""
    import os
    import glob
    
    try:
        # Nettoyer les anciens rapports de démonstration (garder les 5 derniers)
        demo_files = glob.glob("/opt/airflow/resource/demo_report_*.txt")
        demo_files.sort(reverse=True)  # Plus récents en premier
        
        if len(demo_files) > 5:
            for old_file in demo_files[5:]:
                os.remove(old_file)
                logging.info(f"🗑️  Ancien rapport supprimé: {old_file}")
        
        logging.info("🧹 Nettoyage des fichiers de démonstration terminé")
        
    except Exception as e:
        logging.warning(f"Erreur lors du nettoyage: {e}")


# Configuration du DAG
default_args = {
    'owner': 'demo_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

with DAG(
    dag_id='demo_full_pipeline',
    default_args=default_args,
    description='Démonstration complète du pipeline e-commerce',
    schedule=None,  # Exécution manuelle
    catchup=False,
    tags=['demo', 'ecommerce', 'pipeline', 'showcase'],
) as dag:

    # Vérification des services
    wait_services_task = PythonOperator(
        task_id='wait_for_services',
        python_callable=wait_for_services,
        execution_timeout=timedelta(minutes=10),
    )

    # Note: Ce DAG de démonstration génère un rapport sans déclencher d'autres DAGs
    # Pour une démonstration complète, exécutez manuellement les DAGs dans l'ordre :
    # 1. setup_connections
    # 2. init_ecommerce_oltp  
    # 3. process_payment_csv

    # Validation des données
    validate_data_task = PythonOperator(
        task_id='validate_demo_data',
        python_callable=validate_demo_data,
    )

    # Génération du rapport final
    generate_report_task = PythonOperator(
        task_id='generate_demo_report',
        python_callable=generate_demo_report,
    )

    # Nettoyage
    cleanup_task = PythonOperator(
        task_id='cleanup_demo_files',
        python_callable=cleanup_demo_files,
    )

    # Définir les dépendances
    wait_services_task >> validate_data_task >> generate_report_task >> cleanup_task
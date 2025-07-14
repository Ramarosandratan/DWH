from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging
import os

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

def create_madagascar_sales_chart(**context):
    """Crée un graphique des ventes par région Madagascar avec noms complets"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête pour obtenir les données des ventes par région Madagascar
        query_madagascar = """
        SELECT 
            dr.region_id,
            dr.region_name,
            dr.region_code,
            COUNT(*) as nb_ventes,
            SUM(f.total_amount) as ca_total,
            AVG(f.total_amount) as panier_moyen,
            SUM(f.quantity) as quantite_totale,
            MIN(f.date_key) as premiere_vente,
            MAX(f.date_key) as derniere_vente
        FROM ecommerce_dwh.fact_sales f
        JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_id, dr.region_name, dr.region_code
        ORDER BY ca_total DESC
        """
        
        # Exécuter la requête
        results = postgres_hook.get_records(query_madagascar)
        
        if not results:
            logging.warning("⚠️ Aucune donnée trouvée dans le DWH OLAP")
            return "No data found in OLAP DWH"
        
        # Traitement des données
        regions_data = []
        for row in results:
            regions_data.append({
                'region_id': row[0],
                'region_name': row[1],
                'region_code': row[2],
                'nb_ventes': row[3],
                'ca_total': float(row[4]),
                'panier_moyen': float(row[5]),
                'quantite_totale': int(row[6]),
                'premiere_vente': row[7],
                'derniere_vente': row[8]
            })
        
        # Créer un rapport détaillé avec noms des régions
        report = f"""
=== ANALYSE VENTES PAR RÉGION MADAGASCAR ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🇲🇬 RÉGIONS MADAGASCAR ANALYSÉES:
"""
        
        total_ca = sum(region['ca_total'] for region in regions_data)
        total_ventes = sum(region['nb_ventes'] for region in regions_data)
        
        # Analyse détaillée par région
        for i, region in enumerate(regions_data, 1):
            pourcentage_ca = (region['ca_total'] / total_ca) * 100 if total_ca > 0 else 0
            pourcentage_ventes = (region['nb_ventes'] / total_ventes) * 100 if total_ventes > 0 else 0
            
            report += f"""
🏛️ {i}. RÉGION {region['region_name']} ({region['region_code']})
   📍 ID Région: {region['region_id']}
   💰 Chiffre d'affaires: {region['ca_total']:.2f}€ ({pourcentage_ca:.1f}% du total)
   📈 Nombre de ventes: {region['nb_ventes']} ({pourcentage_ventes:.1f}% du total)
   🛒 Panier moyen: {region['panier_moyen']:.2f}€
   📦 Quantité totale: {region['quantite_totale']} unités
   📅 Période: {region['premiere_vente']} → {region['derniere_vente']}
"""
        
        # Statistiques globales
        report += f"""
📊 STATISTIQUES GLOBALES MADAGASCAR:
   💰 CA Total: {total_ca:.2f}€
   📈 Ventes Totales: {total_ventes}
   🛒 Panier Moyen Global: {total_ca/total_ventes:.2f}€
   🗺️ Nombre de Régions: {len(regions_data)}

🏆 CLASSEMENT PAR PERFORMANCE:
"""
        
        # Classement par CA
        for i, region in enumerate(regions_data, 1):
            pourcentage = (region['ca_total'] / total_ca) * 100
            report += f"   {i}. {region['region_name']}: {region['ca_total']:.2f}€ ({pourcentage:.1f}%)\n"
        
        # Analyse comparative
        if len(regions_data) >= 2:
            meilleure_region = regions_data[0]
            moins_bonne_region = regions_data[-1]
            
            report += f"""
🔍 ANALYSE COMPARATIVE:
   🥇 Meilleure région: {meilleure_region['region_name']}
      • CA: {meilleure_region['ca_total']:.2f}€
      • Panier moyen: {meilleure_region['panier_moyen']:.2f}€
   
   📉 Région à développer: {moins_bonne_region['region_name']}
      • CA: {moins_bonne_region['ca_total']:.2f}€
      • Panier moyen: {moins_bonne_region['panier_moyen']:.2f}€
   
   📊 Écart de performance: {((meilleure_region['ca_total'] / moins_bonne_region['ca_total']) - 1) * 100:.1f}%
"""
        
        # Recommandations business
        report += f"""
💡 RECOMMANDATIONS BUSINESS:
"""
        
        for region in regions_data:
            if region['ca_total'] > total_ca * 0.4:  # Plus de 40% du CA
                report += f"   🚀 {region['region_name']}: Région leader - Maintenir l'excellence\n"
            elif region['ca_total'] > total_ca * 0.25:  # Plus de 25% du CA
                report += f"   📈 {region['region_name']}: Région performante - Potentiel de croissance\n"
            else:
                report += f"   🎯 {region['region_name']}: Région à développer - Actions marketing ciblées\n"
        
        # Analyse des paniers
        panier_moyen_global = total_ca / total_ventes if total_ventes > 0 else 0
        report += f"""
🛒 ANALYSE DES PANIERS:
   📊 Panier moyen global: {panier_moyen_global:.2f}€
"""
        
        for region in regions_data:
            if region['panier_moyen'] > panier_moyen_global * 1.1:
                report += f"   💎 {region['region_name']}: Panier premium ({region['panier_moyen']:.2f}€)\n"
            elif region['panier_moyen'] < panier_moyen_global * 0.9:
                report += f"   💰 {region['region_name']}: Potentiel d'upselling ({region['panier_moyen']:.2f}€)\n"
            else:
                report += f"   ✅ {region['region_name']}: Panier équilibré ({region['panier_moyen']:.2f}€)\n"
        
        logging.info(report)
        
        # Sauvegarder le rapport
        report_path = f"/opt/airflow/resource/madagascar_regions_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport Madagascar sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
        
        return {
            "report_path": report_path,
            "regions_count": len(regions_data),
            "total_ca": float(total_ca),
            "total_sales": int(total_ventes),
            "best_region": regions_data[0]['region_name'] if regions_data else None
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'analyse Madagascar: {str(e)}")
        raise

def create_detailed_region_breakdown(**context):
    """Crée une analyse détaillée par région avec breakdown par produit"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête pour l'analyse détaillée par région et produit
        query_breakdown = """
        SELECT 
            dr.region_name,
            dp.product_name,
            dc.category_name,
            COUNT(*) as nb_ventes,
            SUM(f.quantity) as quantite_vendue,
            SUM(f.total_amount) as ca_produit_region,
            AVG(f.total_amount) as prix_moyen_vente
        FROM ecommerce_dwh.fact_sales f
        JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        JOIN ecommerce_dwh.dim_product dp ON f.product_key = dp.product_key
        JOIN ecommerce_dwh.dim_customer dc ON f.customer_key = dc.customer_key
        GROUP BY dr.region_key, dr.region_name, dp.product_key, dp.product_name, dc.category_name
        ORDER BY dr.region_name, ca_produit_region DESC
        """
        
        results = postgres_hook.get_records(query_breakdown)
        
        if not results:
            logging.warning("⚠️ Aucune donnée détaillée trouvée")
            return "No detailed data found"
        
        # Organiser les données par région
        regions_breakdown = {}
        for row in results:
            region_name = row[0]
            if region_name not in regions_breakdown:
                regions_breakdown[region_name] = []
            
            regions_breakdown[region_name].append({
                'product_name': row[1],
                'category_name': row[2],
                'nb_ventes': row[3],
                'quantite_vendue': row[4],
                'ca_produit_region': float(row[5]),
                'prix_moyen_vente': float(row[6])
            })
        
        # Créer le rapport détaillé
        detailed_report = f"""
=== ANALYSE DÉTAILLÉE PAR RÉGION MADAGASCAR ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔍 BREAKDOWN PAR RÉGION ET PRODUIT:
"""
        
        for region_name, products in regions_breakdown.items():
            total_ca_region = sum(p['ca_produit_region'] for p in products)
            total_ventes_region = sum(p['nb_ventes'] for p in products)
            
            detailed_report += f"""
🏛️ RÉGION {region_name}:
   💰 CA Total Région: {total_ca_region:.2f}€
   📈 Ventes Total Région: {total_ventes_region}
   
   📊 TOP PRODUITS:
"""
            
            # Top 3 produits par région
            top_products = sorted(products, key=lambda x: x['ca_produit_region'], reverse=True)[:3]
            
            for i, product in enumerate(top_products, 1):
                pourcentage_region = (product['ca_produit_region'] / total_ca_region) * 100
                detailed_report += f"""      {i}. {product['product_name']} ({product['category_name']})
         • CA: {product['ca_produit_region']:.2f}€ ({pourcentage_region:.1f}% de la région)
         • Ventes: {product['nb_ventes']} unités
         • Prix moyen: {product['prix_moyen_vente']:.2f}€
"""
        
        logging.info(detailed_report)
        
        # Sauvegarder le rapport détaillé
        detailed_path = f"/opt/airflow/resource/madagascar_detailed_breakdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(detailed_path, 'w', encoding='utf-8') as f:
                f.write(detailed_report)
            logging.info(f"📄 Rapport détaillé sauvegardé: {detailed_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport détaillé: {str(e)}")
        
        return {
            "detailed_path": detailed_path,
            "regions_analyzed": len(regions_breakdown),
            "total_products": len(results)
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'analyse détaillée: {str(e)}")
        raise

def create_ascii_chart(**context):
    """Crée un graphique ASCII des ventes par région Madagascar"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête pour les données du graphique
        query_chart = """
        SELECT 
            dr.region_name,
            SUM(f.total_amount) as ca_total
        FROM ecommerce_dwh.fact_sales f
        JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_name
        ORDER BY ca_total DESC
        """
        
        results = postgres_hook.get_records(query_chart)
        
        if not results:
            logging.warning("⚠️ Aucune donnée pour le graphique")
            return "No chart data found"
        
        # Préparer les données pour le graphique ASCII
        chart_data = [(row[0], float(row[1])) for row in results]
        max_ca = max(ca for _, ca in chart_data)
        
        # Créer le graphique ASCII
        ascii_chart = f"""
=== GRAPHIQUE VENTES PAR RÉGION MADAGASCAR ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 CHIFFRE D'AFFAIRES PAR RÉGION (en €):

"""
        
        # Échelle du graphique (50 caractères max)
        scale_factor = 50 / max_ca if max_ca > 0 else 1
        
        for region_name, ca_total in chart_data:
            bar_length = int(ca_total * scale_factor)
            bar = "█" * bar_length
            
            # Ajuster la longueur du nom pour l'alignement
            region_display = region_name[:15].ljust(15)
            
            ascii_chart += f"{region_display} │{bar} {ca_total:.2f}€\n"
        
        # Ajouter l'échelle
        ascii_chart += f"""
{'─' * 15}┼{'─' * 52}
{'Échelle:'.ljust(15)} │ Chaque █ ≈ {max_ca/50:.1f}€

💰 TOTAL: {sum(ca for _, ca in chart_data):.2f}€
🗺️ RÉGIONS: {len(chart_data)}
"""
        
        logging.info(ascii_chart)
        
        # Sauvegarder le graphique ASCII
        chart_path = f"/opt/airflow/resource/madagascar_ascii_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(chart_path, 'w', encoding='utf-8') as f:
                f.write(ascii_chart)
            logging.info(f"📊 Graphique ASCII sauvegardé: {chart_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le graphique: {str(e)}")
        
        return {
            "chart_path": chart_path,
            "regions_count": len(chart_data),
            "max_ca": max_ca
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du graphique ASCII: {str(e)}")
        raise

def create_comparison_report(**context):
    """Crée un rapport de comparaison avant/après mise à jour des noms"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête pour les données actuelles
        current_query = """
        SELECT 
            dr.region_id,
            dr.region_name,
            dr.region_code,
            COUNT(*) as nb_ventes,
            SUM(f.total_amount) as ca_total
        FROM ecommerce_dwh.fact_sales f
        JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_id, dr.region_name, dr.region_code
        ORDER BY dr.region_id
        """
        
        current_results = postgres_hook.get_records(current_query)
        
        # Créer le rapport de comparaison
        comparison_report = f"""
=== RAPPORT COMPARAISON RÉGIONS MADAGASCAR ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔄 ÉVOLUTION DES NOMS DE RÉGIONS:

AVANT (Noms génériques):          APRÈS (Noms Madagascar):
1. Nord                    →      1. ANALAMANGA
2. Sud                     →      2. ALAOTRA MANGORO  
3. Est                     →      3. BOENY

📊 DONNÉES ACTUELLES AVEC NOUVEAUX NOMS:
"""
        
        total_ca = 0
        for row in current_results:
            region_id, region_name, region_code, nb_ventes, ca_total = row
            total_ca += float(ca_total)
            
            comparison_report += f"""
🏛️ Région {region_id}: {region_name} ({region_code})
   • Ventes: {nb_ventes}
   • CA: {ca_total:.2f}€
"""
        
        comparison_report += f"""
💰 CA TOTAL: {total_ca:.2f}€

✅ AVANTAGES DE LA MISE À JOUR:
   🗺️ Noms géographiques réels (Madagascar)
   📊 Meilleure lisibilité des rapports
   🎯 Analyse business plus précise
   📈 Graphiques avec noms explicites

🎯 PRÊT POUR ANALYSE GÉOGRAPHIQUE MADAGASCAR !
"""
        
        logging.info(comparison_report)
        
        # Sauvegarder le rapport de comparaison
        comparison_path = f"/opt/airflow/resource/madagascar_comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(comparison_path, 'w', encoding='utf-8') as f:
                f.write(comparison_report)
            logging.info(f"📄 Rapport comparaison sauvegardé: {comparison_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
        
        return {
            "comparison_path": comparison_path,
            "total_ca": total_ca,
            "regions_updated": len(current_results)
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du rapport de comparaison: {str(e)}")
        raise

def cleanup_old_madagascar_reports(**context):
    """Nettoie les anciens rapports Madagascar"""
    try:
        import glob
        
        # Patterns des fichiers à nettoyer
        patterns = [
            "/opt/airflow/resource/madagascar_regions_analysis_*.txt",
            "/opt/airflow/resource/madagascar_detailed_breakdown_*.txt",
            "/opt/airflow/resource/madagascar_ascii_chart_*.txt",
            "/opt/airflow/resource/madagascar_comparison_report_*.txt"
        ]
        
        cleaned_count = 0
        
        for pattern in patterns:
            files = glob.glob(pattern)
            
            # Garder seulement les 3 derniers fichiers de chaque type
            if len(files) > 3:
                files.sort()
                old_files = files[:-3]
                
                for file_path in old_files:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logging.info(f"🗑️ Fichier supprimé: {file_path}")
                    except Exception as e:
                        logging.warning(f"⚠️ Impossible de supprimer {file_path}: {str(e)}")
        
        logging.info(f"🧹 Nettoyage Madagascar terminé. {cleaned_count} fichiers supprimés")
        return f"Cleaned {cleaned_count} old Madagascar report files"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du nettoyage: {str(e)}")
        return f"Cleanup failed: {str(e)}"

# Définition du DAG
with DAG(
    dag_id='create_madagascar_region_chart',
    default_args=default_args,
    description='Crée des analyses et graphiques des régions Madagascar avec noms complets',
    schedule=None,  # Exécution manuelle
    catchup=False,
    tags=['ecommerce', 'madagascar', 'regions', 'analytics'],
) as dag:

    # Analyse principale des régions Madagascar
    create_main_analysis_task = PythonOperator(
        task_id='create_madagascar_sales_chart',
        python_callable=create_madagascar_sales_chart,
    )

    # Analyse détaillée par produit
    create_detailed_analysis_task = PythonOperator(
        task_id='create_detailed_region_breakdown',
        python_callable=create_detailed_region_breakdown,
    )

    # Graphique ASCII
    create_ascii_chart_task = PythonOperator(
        task_id='create_ascii_chart',
        python_callable=create_ascii_chart,
    )

    # Rapport de comparaison
    create_comparison_task = PythonOperator(
        task_id='create_comparison_report',
        python_callable=create_comparison_report,
    )

    # Nettoyage des anciens rapports
    cleanup_task = PythonOperator(
        task_id='cleanup_old_madagascar_reports',
        python_callable=cleanup_old_madagascar_reports,
    )

    # Définition des dépendances (parallèle puis nettoyage)
    [create_main_analysis_task, create_detailed_analysis_task, create_ascii_chart_task, create_comparison_task] >> cleanup_task
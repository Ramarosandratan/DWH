from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging
import os
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns
    CHARTS_AVAILABLE = True
    # Configuration matplotlib pour environnement headless
    plt.switch_backend('Agg')
    plt.ioff()
except ImportError:
    CHARTS_AVAILABLE = False
    logging.warning("⚠️ Matplotlib non disponible. Seuls les rapports textuels seront générés.")

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

def create_sales_by_region_chart(**context):
    """Crée un graphique des ventes par région depuis le DWH OLAP"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête pour obtenir les données des ventes par région avec noms complets
        query_olap = """
        SELECT 
            COALESCE(dr.region_name, 'Non défini') as region_name,
            COALESCE(dr.region_code, 'N/A') as region_code,
            dr.region_id,
            COUNT(*) as nb_ventes,
            SUM(f.total_amount) as ca_total,
            AVG(f.total_amount) as panier_moyen,
            SUM(f.quantity) as quantite_totale
        FROM ecommerce_dwh.fact_sales f
        LEFT JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_id, dr.region_name, dr.region_code
        ORDER BY ca_total DESC
        """
        
        # Exécuter la requête
        results = postgres_hook.get_records(query_olap)
        
        if not results:
            logging.warning("⚠️ Aucune donnée trouvée dans le DWH OLAP")
            return "No data found in OLAP DWH"
        
        # Traitement des données
        data_list = []
        for row in results:
            data_list.append({
                'region_name': row[0],
                'region_code': row[1],
                'region_id': row[2],
                'nb_ventes': row[3],
                'ca_total': float(row[4]),
                'panier_moyen': float(row[5]),
                'quantite_totale': int(row[6])
            })
        
        chart_path = None
        
        # Créer le graphique si matplotlib est disponible
        if CHARTS_AVAILABLE:
            try:
                df = pd.DataFrame(data_list)
                
                # Configuration du style
                plt.style.use('default')
                
                # Créer une figure avec plusieurs sous-graphiques
                fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
                fig.suptitle('📊 Analyse des Ventes par Région', fontsize=16, fontweight='bold')
                
                # Graphique 1: Chiffre d'affaires par région (Bar chart)
                bars1 = ax1.bar(df['region_name'], df['ca_total'], 
                               color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
                ax1.set_title('💰 Chiffre d\'Affaires par Région', fontweight='bold')
                ax1.set_ylabel('Montant (€)')
                ax1.tick_params(axis='x', rotation=45)
                
                # Ajouter les valeurs sur les barres
                for bar, value in zip(bars1, df['ca_total']):
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                            f'{value:.2f}€', ha='center', va='bottom', fontweight='bold')
                
                # Graphique 2: Nombre de ventes par région (Pie chart)
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
                wedges, texts, autotexts = ax2.pie(df['nb_ventes'], 
                                                  labels=df['region_name'],
                                                  autopct='%1.1f%%',
                                                  colors=colors[:len(df)],
                                                  startangle=90)
                ax2.set_title('📈 Répartition des Ventes par Région', fontweight='bold')
                
                # Améliorer la lisibilité du pie chart
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                
                # Graphique 3: Panier moyen par région
                bars3 = ax3.bar(df['region_name'], df['panier_moyen'],
                               color=['#FFA07A', '#98D8C8', '#87CEEB', '#F0E68C'])
                ax3.set_title('🛒 Panier Moyen par Région', fontweight='bold')
                ax3.set_ylabel('Montant Moyen (€)')
                ax3.tick_params(axis='x', rotation=45)
                
                # Ajouter les valeurs sur les barres
                for bar, value in zip(bars3, df['panier_moyen']):
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                            f'{value:.2f}€', ha='center', va='bottom', fontweight='bold')
                
                # Graphique 4: Quantité totale par région
                bars4 = ax4.bar(df['region_name'], df['quantite_totale'],
                               color=['#DDA0DD', '#F0E68C', '#FFB6C1', '#B0E0E6'])
                ax4.set_title('📦 Quantité Totale Vendue par Région', fontweight='bold')
                ax4.set_ylabel('Quantité')
                ax4.tick_params(axis='x', rotation=45)
                
                # Ajouter les valeurs sur les barres
                for bar, value in zip(bars4, df['quantite_totale']):
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                            f'{int(value)}', ha='center', va='bottom', fontweight='bold')
                
                # Ajuster l'espacement
                plt.tight_layout()
                
                # Sauvegarder le graphique
                chart_path = f"/opt/airflow/resource/sales_by_region_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
                plt.close()
                
                logging.info(f"📊 Graphique sauvegardé: {chart_path}")
                
            except Exception as chart_error:
                logging.warning(f"⚠️ Erreur lors de la création du graphique: {str(chart_error)}")
                chart_path = None
        else:
            logging.info("ℹ️ Matplotlib non disponible - génération du rapport textuel uniquement")
        
        # Créer un rapport textuel
        report = f"""
=== RAPPORT VENTES PAR RÉGION ===
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 DONNÉES PAR RÉGION:
"""
        
        total_ca = sum(item['ca_total'] for item in data_list)
        total_ventes = sum(item['nb_ventes'] for item in data_list)
        
        for item in data_list:
            pourcentage_ca = (item['ca_total'] / total_ca) * 100 if total_ca > 0 else 0
            pourcentage_ventes = (item['nb_ventes'] / total_ventes) * 100 if total_ventes > 0 else 0
            
            report += f"""
🗺️ RÉGION {item['region_name']} ({item['region_code']}) - ID: {item['region_id']}:
  • Chiffre d'affaires: {item['ca_total']:.2f}€ ({pourcentage_ca:.1f}% du total)
  • Nombre de ventes: {item['nb_ventes']} ({pourcentage_ventes:.1f}% du total)
  • Panier moyen: {item['panier_moyen']:.2f}€
  • Quantité totale: {item['quantite_totale']} unités
"""
        
        report += f"""
📈 TOTAUX:
  • CA Total: {total_ca:.2f}€
  • Ventes Totales: {total_ventes}
  • Panier Moyen Global: {total_ca/total_ventes:.2f}€

📊 GRAPHIQUE: {'Sauvegardé: ' + chart_path if chart_path else 'Non généré (matplotlib non disponible)'}
"""
        
        logging.info(report)
        
        # Sauvegarder le rapport
        report_path = f"/opt/airflow/resource/sales_by_region_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logging.info(f"📄 Rapport région sauvegardé: {report_path}")
        except Exception as e:
            logging.warning(f"⚠️ Impossible de sauvegarder le rapport: {str(e)}")
        
        return {
            "chart_path": chart_path,
            "report_path": report_path,
            "regions_count": len(df),
            "total_ca": float(total_ca),
            "total_sales": int(total_ventes)
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du graphique région: {str(e)}")
        raise

def create_comparative_chart(**context):
    """Crée un rapport comparatif entre Star Schema et OLAP"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête Star Schema
        query_star = """
        SELECT 
            COALESCE(dr.region_name, 'Non défini') as region_name,
            COUNT(*) as nb_ventes,
            SUM(f.total_amount) as ca_total
        FROM ecommerce_dwh_star.fact_sales f
        LEFT JOIN ecommerce_dwh_star.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_name
        ORDER BY ca_total DESC
        """
        
        # Requête OLAP
        query_olap = """
        SELECT 
            COALESCE(dr.region_name, 'Non défini') as region_name,
            COUNT(*) as nb_ventes,
            SUM(f.total_amount) as ca_total
        FROM ecommerce_dwh.fact_sales f
        LEFT JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY dr.region_key, dr.region_name
        ORDER BY ca_total DESC
        """
        
        star_data = []
        olap_data = []
        
        try:
            star_results = postgres_hook.get_records(query_star)
            for row in star_results:
                star_data.append({
                    'region_name': row[0],
                    'nb_ventes': row[1],
                    'ca_total': float(row[2])
                })
        except Exception as e:
            logging.warning(f"⚠️ Données Star Schema non disponibles: {str(e)}")
        
        try:
            olap_results = postgres_hook.get_records(query_olap)
            for row in olap_results:
                olap_data.append({
                    'region_name': row[0],
                    'nb_ventes': row[1],
                    'ca_total': float(row[2])
                })
        except Exception as e:
            logging.warning(f"⚠️ Données OLAP non disponibles: {str(e)}")
        
        if not star_data and not olap_data:
            logging.warning("⚠️ Aucune donnée disponible pour la comparaison")
            return "No data available for comparison"
        
        # Combiner les DataFrames
        df_combined = pd.concat([df_star, df_olap], ignore_index=True)
        
        # Créer le graphique comparatif
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('🔄 Comparaison Star Schema vs OLAP - Ventes par Région', fontsize=14, fontweight='bold')
        
        # Graphique 1: CA par région et modèle
        if not df_combined.empty:
            pivot_ca = df_combined.pivot(index='region_name', columns='model', values='ca_total').fillna(0)
            pivot_ca.plot(kind='bar', ax=ax1, color=['#FF6B6B', '#4ECDC4'])
            ax1.set_title('💰 Chiffre d\'Affaires par Région', fontweight='bold')
            ax1.set_ylabel('Montant (€)')
            ax1.tick_params(axis='x', rotation=45)
            ax1.legend()
        
        # Graphique 2: Nombre de ventes par région et modèle
        if not df_combined.empty:
            pivot_ventes = df_combined.pivot(index='region_name', columns='model', values='nb_ventes').fillna(0)
            pivot_ventes.plot(kind='bar', ax=ax2, color=['#45B7D1', '#96CEB4'])
            ax2.set_title('📈 Nombre de Ventes par Région', fontweight='bold')
            ax2.set_ylabel('Nombre de ventes')
            ax2.tick_params(axis='x', rotation=45)
            ax2.legend()
        
        plt.tight_layout()
        
        # Sauvegarder le graphique comparatif
        comparison_chart_path = f"/opt/airflow/resource/star_vs_olap_regions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(comparison_chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logging.info(f"📊 Graphique comparatif sauvegardé: {comparison_chart_path}")
        
        return {
            "comparison_chart_path": comparison_chart_path,
            "star_regions": len(df_star),
            "olap_regions": len(df_olap)
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du graphique comparatif: {str(e)}")
        raise

def create_time_series_by_region(**context):
    """Crée un graphique de série temporelle des ventes par région"""
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_raw_conn')
        
        # Requête pour les données temporelles par région
        query_time_series = """
        SELECT 
            f.date_key,
            COALESCE(dr.region_name, 'Non défini') as region_name,
            SUM(f.total_amount) as ca_jour,
            COUNT(*) as ventes_jour
        FROM ecommerce_dwh.fact_sales f
        LEFT JOIN ecommerce_dwh.dim_region dr ON f.region_key = dr.region_key
        GROUP BY f.date_key, dr.region_key, dr.region_name
        ORDER BY f.date_key, dr.region_name
        """
        
        results = postgres_hook.get_records(query_time_series)
        
        if not results:
            logging.warning("⚠️ Aucune donnée temporelle trouvée")
            return "No time series data found"
        
        df_time = pd.DataFrame(results, columns=['date_key', 'region_name', 'ca_jour', 'ventes_jour'])
        df_time['date_key'] = pd.to_datetime(df_time['date_key'])
        
        # Créer le graphique de série temporelle
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle('📅 Évolution Temporelle des Ventes par Région', fontsize=14, fontweight='bold')
        
        # Graphique 1: CA par jour et région
        for region in df_time['region_name'].unique():
            region_data = df_time[df_time['region_name'] == region]
            ax1.plot(region_data['date_key'], region_data['ca_jour'], 
                    marker='o', linewidth=2, label=region)
        
        ax1.set_title('💰 Chiffre d\'Affaires Quotidien par Région', fontweight='bold')
        ax1.set_ylabel('CA (€)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Graphique 2: Nombre de ventes par jour et région
        for region in df_time['region_name'].unique():
            region_data = df_time[df_time['region_name'] == region]
            ax2.plot(region_data['date_key'], region_data['ventes_jour'], 
                    marker='s', linewidth=2, label=region)
        
        ax2.set_title('📈 Nombre de Ventes Quotidiennes par Région', fontweight='bold')
        ax2.set_ylabel('Nombre de ventes')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Sauvegarder le graphique temporel
        time_series_path = f"/opt/airflow/resource/time_series_regions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(time_series_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logging.info(f"📅 Graphique temporel sauvegardé: {time_series_path}")
        
        return {
            "time_series_path": time_series_path,
            "date_range": f"{df_time['date_key'].min()} - {df_time['date_key'].max()}",
            "regions_tracked": len(df_time['region_name'].unique())
        }
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la création du graphique temporel: {str(e)}")
        raise

def cleanup_old_charts(**context):
    """Nettoie les anciens graphiques"""
    try:
        import glob
        
        # Patterns des fichiers à nettoyer
        patterns = [
            "/opt/airflow/resource/sales_by_region_chart_*.png",
            "/opt/airflow/resource/sales_by_region_report_*.txt",
            "/opt/airflow/resource/star_vs_olap_regions_*.png",
            "/opt/airflow/resource/time_series_regions_*.png"
        ]
        
        cleaned_count = 0
        
        for pattern in patterns:
            files = glob.glob(pattern)
            
            # Garder seulement les 5 derniers fichiers de chaque type
            if len(files) > 5:
                files.sort()
                old_files = files[:-5]
                
                for file_path in old_files:
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                        logging.info(f"🗑️ Fichier supprimé: {file_path}")
                    except Exception as e:
                        logging.warning(f"⚠️ Impossible de supprimer {file_path}: {str(e)}")
        
        logging.info(f"🧹 Nettoyage terminé. {cleaned_count} fichiers supprimés")
        return f"Cleaned {cleaned_count} old chart files"
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du nettoyage: {str(e)}")
        return f"Cleanup failed: {str(e)}"

# Définition du DAG
with DAG(
    dag_id='create_region_chart',
    default_args=default_args,
    description='Crée des graphiques d\'analyse des ventes par région',
    schedule=None,  # Exécution manuelle
    catchup=False,
    tags=['ecommerce', 'regions', 'charts', 'analytics'],
) as dag:

    # Graphique principal des ventes par région
    create_main_chart_task = PythonOperator(
        task_id='create_sales_by_region_chart',
        python_callable=create_sales_by_region_chart,
    )

    # Graphique comparatif Star vs OLAP
    create_comparison_task = PythonOperator(
        task_id='create_comparative_chart',
        python_callable=create_comparative_chart,
    )

    # Graphique de série temporelle
    create_time_series_task = PythonOperator(
        task_id='create_time_series_by_region',
        python_callable=create_time_series_by_region,
    )

    # Nettoyage des anciens graphiques
    cleanup_charts_task = PythonOperator(
        task_id='cleanup_old_charts',
        python_callable=cleanup_old_charts,
    )

    # Définition des dépendances (parallèle puis nettoyage)
    [create_main_chart_task, create_comparison_task, create_time_series_task] >> cleanup_charts_task
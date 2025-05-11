from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import pandas as pd
import datetime as dt

default_args = {
    'start_date': datetime(2025, 5, 1),
    'retries': 0,
    'retry_delay': timedelta(minutes=0),
}

def clean_and_load(table_name, sql_select, target_schema, target_table):
    # Helper function to convert numpy types to Python native types
    def to_python(val):
        try:
            return val.item()  # Convert numpy types to Python native types
        except AttributeError:
            return val  # Already a Python native type or other object
    
    hook = PostgresHook(postgres_conn_id='postgres_dwh')
    db_uri = hook.get_uri()
    engine = create_engine(db_uri)
    df = pd.read_sql(sql_select, con=engine)

    df = df.drop_duplicates().dropna()
    
    # Traitement des colonnes de date
    if 'date_key' in df:
        df['date_key'] = pd.to_datetime(df['date_key'], format='%Y%m%d').dt.date
    
    # Obtention des colonnes cibles depuis le schéma
    cols = hook.get_pandas_df(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        parameters=(target_schema, target_table)
    )
    
    # Conversion du DataFrame en dictionnaire pour une recherche plus facile
    column_types = dict(zip(cols['column_name'], cols['data_type']))
    
    # Filtrer les colonnes pour correspondre au schéma cible
    target_columns = cols['column_name'].tolist()
    df = df[[c for c in df.columns if c in target_columns]]
    
    # Stockage des valeurs originales avant conversion
    pk = df.columns[0]
    raw_keys = df[pk].unique().tolist()
    
    # Traitement spécifique pour les colonnes de type TIME
    # Créer une fonction de conversion des entiers HHMMSS en objets time
    def int_to_time(x):
        if x is None:
            return None
        try:
            hours = int(x) // 10000
            minutes = (int(x) // 100) % 100
            seconds = int(x) % 100
            return dt.time(hours, minutes, seconds)
        except (ValueError, TypeError):
            return x
    
    # Traitement spécifique pour dim_time
    if target_table == 'dim_time':
        # Convertir directement time_key en objets time
        df['time_key'] = df['time_key'].apply(int_to_time)
        
    
    # Pour fact_sales, nous devons convertir la colonne time_key en time
    if target_table == 'fact_sales' and 'time_key' in df.columns:
        df['time_key'] = df['time_key'].apply(int_to_time)
    
    # Parcourir toutes les colonnes et appliquer les conversions nécessaires
    for col_name in df.columns:
        if col_name in column_types:
            # Convertir les valeurs selon le type de données de la colonne cible
            if column_types[col_name].startswith('time'):
                df[col_name] = df[col_name].apply(int_to_time)
    
    # Convertir toutes les valeurs en types Python natifs pour l'insertion
    rows = [
        tuple(to_python(v) for v in row)
        for row in df.values.tolist()
    ]
    
    # Insérer les nouvelles lignes
    if rows:  # S'assurer qu'il y a des lignes à insérer
        hook.insert_rows(
            table=f"{target_schema}.{target_table}",
            rows=rows,
            target_fields=list(df.columns),
            commit_every=1000
        )
        print(f"Inserted {len(rows)} rows into {target_schema}.{target_table}")
    else:
        print(f"No rows to insert into {target_schema}.{target_table}")

# Configuration pour l'ordre d'exécution des tâches
def create_dag():
    with DAG(
        dag_id='etl_clean_and_load_dwh',
        default_args=default_args,
        schedule='@daily',
        catchup=False,
        tags={'ecommerce', 'dwh', 'cleaning'},
    ) as dag:

        with TaskGroup('truncate_task') as truncate_task:
            etl_master = SQLExecuteQueryOperator(
                task_id='truncate_task',
                sql='CALL ecommerce_dwh.truncate_all_tables()',
                conn_id='postgres_dwh',
                autocommit=True
            )

        tables = [
            ('dim_date', "SELECT * FROM ecommerce_dwh_star.dim_date"),
            ('dim_time', "SELECT * FROM ecommerce_dwh_star.dim_time"),
            ('dim_product', "SELECT * FROM ecommerce_dwh_star.dim_product"),
            ('dim_customer', "SELECT * FROM ecommerce_dwh_star.dim_customer"),
            ('dim_payment_method', "SELECT * FROM ecommerce_dwh_star.dim_payment_method"),
            ('fact_sales', "SELECT * FROM ecommerce_dwh_star.fact_sales")
        ]
        
        tasks = {}
        for table_name, sql_query in tables:
            tasks[table_name] = PythonOperator(
                task_id=f'clean_load_{table_name}',
                python_callable=clean_and_load,
                op_kwargs={
                    'table_name': table_name,
                    'sql_select': sql_query,
                    'target_schema': 'ecommerce_dwh',
                    'target_table': table_name
                }
            )
        
        # dimension → fact dependencies
        for dim in ['dim_date', 'dim_time', 'dim_product', 'dim_customer', 'dim_payment_method']:
            tasks[dim] >> tasks['fact_sales']

        truncate_task >> list(tasks.values())
        
        return dag

dag = create_dag()
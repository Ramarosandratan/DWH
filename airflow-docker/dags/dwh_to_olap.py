from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import pandas as pd

default_args = {
    'start_date': datetime(2025, 5, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def clean_and_load(table_name, sql_select, target_schema, target_table):
    """
    Extrait avec Pandas, nettoie et charge dans la table cible.
    """
    hook = PostgresHook(postgres_conn_id='postgres_dwh')
    # Extraction en DataFrame
    df = hook.get_pandas_df(sql_select)  # :contentReference[oaicite:11]{index=11}

    # Nettoyages génériques
    df = df.drop_duplicates()            # suppression doublons
    df = df.dropna()                     # suppression NA :contentReference[oaicite:12]{index=12}

    # Exemple: conversion de colonnes date
    if 'date_key' in df:
        df['date_key'] = pd.to_datetime(df['date_key'], format='%Y%m%d').dt.date

    # Chargement: effacer les anciennes lignes pour date(s) en question
    pk = df.columns[0]  # suppose première colonne pk surrogate
    keys = tuple(df[pk].unique())
    hook.run(f"DELETE FROM {target_schema}.{target_table} WHERE {pk} IN %s", parameters=(keys,))

    # Insertion par batch
    hook.insert_rows(table=f"{target_schema}.{target_table}",
                     rows=df.values.tolist(),
                     target_fields=list(df.columns),
                     commit_every=1000)  # :contentReference[oaicite:13]{index=13}

with DAG(
    dag_id='clean_and_load_dwh',
    default_args=default_args,
    schedule='@daily',
    catchup=False,
    tags={'ecommerce','dwh','cleaning'},
) as dag:

    # Tâches dynamiques pour chaque table
    tables = {
        'dim_date':   "SELECT * FROM ecommerce_dwh_star.dim_date",
        'dim_time':   "SELECT * FROM ecommerce_dwh_star.dim_time",
        'dim_product':"SELECT * FROM ecommerce_dwh_star.dim_product",
        'dim_customer':"SELECT * FROM ecommerce_dwh_star.dim_customer",
        'dim_payment_method':"SELECT * FROM ecommerce_dwh_star.dim_payment_method",
        'fact_sales': "SELECT * FROM ecommerce_dwh_star.fact_sales"
    }

    for tbl, query in tables.items():
        PythonOperator(
            task_id=f'clean_load_{tbl}',
            python_callable=clean_and_load,
            op_kwargs={
                'table_name': tbl,
                'sql_select': query,
                'target_schema': 'ecommerce_dwh',
                'target_table': tbl
            }
        )

from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta

default_args = {
    'start_date': datetime(2025, 4, 30),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='etl_raw_to_dwh',
    default_args=default_args,
    schedule='@daily',
    catchup=False,
    tags={'ecommerce', 'dwh'},
) as dag:

    with TaskGroup('load_dwh') as load_dwh_group:
        sql_command = 'call ecommerce_dwh_db.ecommerce_dwh_star.load_dim_date()'
        sp_ctrl_calendar = SQLExecuteQueryOperator(
            task_id='load_dim_date',
            sql=sql_command,
            postgres_conn_id='postgres_dwh',
            autocommit=True)

    # Vous pouvez chaîner d’autres tâches ici
    load_dwh_group

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='dag_catchup_backfill_v1',
    default_args=default_args,
    schedule=timedelta(days=1),
    start_date=datetime(2024, 6, 16, 2),
    catchup=True,
) as dag:

    task1 = BashOperator(
        task_id='task1',
        bash_command='echo "This is the first task in the DAG."',
    )

    task1
dag_instance = dag
# This line is necessary to instantiate the DAG and make it available to Airflow.
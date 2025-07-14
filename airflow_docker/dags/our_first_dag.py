from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='our_first_dag_V3',
    default_args=default_args,
    description='A simple first DAG',
    start_date=datetime(2025, 6, 16, 2),
    schedule=timedelta(days=1),
) as dag:
    task1 = BashOperator(
        task_id='first_task',
        bash_command='echo "Hello, World! This is my first task in Airflow!"',
    )

    task2 = BashOperator(
        task_id='second_task',
        bash_command='echo "This is my second task in Airflow!"',
    )

    task3 = BashOperator(
        task_id='third_task',
        bash_command='echo "This is my third task in Airflow!"',
    )

    task1 >> task2
    task1 >> task3

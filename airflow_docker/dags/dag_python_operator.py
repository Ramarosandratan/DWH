from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
# This DAG demonstrates the use of PythonOperator in Apache Airflow.

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

def greet(ti):
    """Prints a greeting message to demonstrate PythonOperator usage in Airflow."""
    first_name = ti.xcom_pull(task_ids='get_name_task', key='first_name')
    last_name = ti.xcom_pull(task_ids='get_name_task', key='last_name')
    age = ti.xcom_pull(task_ids='get_age_task')
    print(f"Hello, {first_name} {last_name}! You are {age} years old.")

def get_name(ti):
    ti.xcom_push(
        key='first_name',
        value='John'
    )
    ti.xcom_push(
        key='last_name',
        value='Doe'
    )

def get_age():
    """Returns an age to be used in the PythonOperator."""
    return 30

with DAG(
    dag_id='dag_with_python_operator_v05',
    description='A simple DAG with PythonOperator',
    tags=['example', 'python_operator'],
    schedule=timedelta(days=1),
    start_date=datetime(2024, 6, 16, 2),
    default_args=default_args,
) as dag:
    task1 = PythonOperator(
        task_id='greet_task',
        python_callable=greet,
        dag=dag,
    )

    task2 = PythonOperator(
        task_id='get_name_task',
        python_callable=get_name,
        dag=dag,
    )

    task3 = PythonOperator(
        task_id='get_age_task',
        python_callable=get_age,
        dag=dag,
    )

    (task2, task3) >> task1
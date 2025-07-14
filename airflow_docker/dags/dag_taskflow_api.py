from datetime import datetime, timedelta
from airflow.decorators import dag, task
# This DAG demonstrates the use of TaskFlow API in Apache Airflow.

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

@dag(
    dag_id='dag_with_taskflow_api_v2',
    default_args=default_args,
    schedule=timedelta(days=1),
    start_date=datetime(2024, 6, 16, 2),
)
def hello_world_etl():
    """A simple DAG using TaskFlow API to demonstrate its usage in Airflow."""
    
    @task
    def greet(first_name: str, last_name: str, age: int):
        """Prints a greeting message."""
        print(f"Hello, {first_name} {last_name}! You are {age} years old.")

    @task(multiple_outputs=True)
    def get_name() -> str:
        """Returns a first name."""
        return {
            'first_name': 'John',
            'last_name': 'Doe'
        }

    @task
    def get_age() -> int:
        """Returns an age."""
        return 30

    names = get_name()
    age = get_age()
    greet(names['first_name'], names['last_name'], age)

dag_instance = hello_world_etl()
# This line is necessary to instantiate the DAG and make it available to Airflow.
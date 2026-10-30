from datetime import datetime, timedelta
from airflow.decorators import dag, task
from include.scripts.reconstruct import reconstruct

@dag(
    start_date = datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(seconds=30)
    },
    tags=["upwork"]
)
def upworkETL_dag():
    @task
    def reconstruct_csv():
        reconstruct()
        pass

    @task
    def build_bronze():
        pass

    @task
    def build_silver():
        pass

    @task
    def build_gold():
        pass

    data = reconstruct_csv()
    bronze = build_bronze()
    silver = build_silver()
    gold = build_gold()
    data >> bronze >> silver >> gold

upworkETL_dag()
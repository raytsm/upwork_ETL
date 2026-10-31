from datetime import datetime, timedelta
from airflow.decorators import dag, task
from include.scripts.reconstruct import reconstruct
from airflow.providers.postgres.hooks.postgres import PostgresHook
from include.utils.helpers import file_hash
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

POSTGRES_CONN_ID = os.getenv("CONNECTION_ID", "upwork_postgres")

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
    # @task
    # def reconstruct_csv(file_name):
    #     reconstruct(file_name)
    #     return

    @task
    def initialise():
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        cursor.execute("CREATE SCHEMA IF NOT EXISTS bronze")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS silver")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS gold")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze.ingestion_batches (
                source_hash VARCHAR PRIMARY KEY,
                source_file VARCHAR NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bronze.upwork_raw_jobs (
                id VARCHAR,
                url VARCHAR,
                title VARCHAR,
                description VARCHAR,
                budget VARCHAR,
                budget_type VARCHAR,
                hourly_rate_min VARCHAR,
                hourly_rate_max VARCHAR,
                work_type VARCHAR,
                experience_level VARCHAR,
                duration VARCHAR,
                location VARCHAR,
                category VARCHAR,
                skills VARCHAR,
                proposals VARCHAR,
                client_info VARCHAR,
                posted_date VARCHAR,
                crawled_date VARCHAR,
                raw_data VARCHAR,
                created_at VARCHAR,
                updated_at VARCHAR,
                source_file VARCHAR NOT NULL,
                source_hash VARCHAR NOT NULL,
                ingested_at TIMESTAMPTZ NOT NULL
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    @task
    def ingest_bronze(source: Path):
        source = Path(source).resolve()

        if not source.is_file():
            raise FileNotFoundError(f"CSV not found: {source}")
        
        digest = file_hash(source)

        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO bronze.ingestion_batches
                    (source_hash, source_file)
                VALUES (%s, %s)
                ON CONFLICT (source_hash) DO NOTHING
                RETURNING source_hash
                """,
                (digest, source.name),
            )

            if cursor.fetchone() is None:
                print(f"Skipping{source.name}: already loaded")
                conn.rollback()
                return False

            cursor.execute(
                """
                CREATE TEMP TABLE upwork_stage
                ON COMMIT DROP AS
                SELECT
                    id, url, title, description,
                    budget, budget_type,
                    hourly_rate_min, hourly_rate_max,
                    work_type, experience_level,
                    duration, location, category,
                    skills, proposals, client_info,
                    posted_date, crawled_date,
                    raw_data, created_at, updated_at
                FROM bronze.upwork_raw_jobs
                WITH NO DATA
                """
            )
            copy_sql = """
                COPY upwork_stage
                FROM STDIN
                WITH (FORMAT CSV, HEADER TRUE)
            """

            with source.open("rb") as file:
                if hasattr(cursor, "copy"):
                    with cursor.copy(copy_sql) as copy:
                        while chunk := file.read(1024 * 1024):
                            copy.write(chunk)
                else:
                    cursor.copy_expert(copy_sql, file)

            cursor.execute(
                """
                INSERT INTO bronze.upwork_raw_jobs
                SELECT *, %s, %s, CURRENT_TIMESTAMP
                FROM upwork_stage
                """,
                (source.name, digest),
            )

            conn.commit()
            print(f"Loaded {source.name} into bronze")
        
        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()

    @task
    def build_silver():
        pass

    @task
    def build_gold():
        pass

    # data = reconstruct_csv("upwork_combined_data.csv")
    setup = initialise()
    bronze = ingest_bronze(Path("include/data/reconstructed_data/upwork_reconstructed.csv"))
    silver = build_silver()
    gold = build_gold()
    # data >> 
    setup >> bronze >> silver >> gold

upworkETL_dag()
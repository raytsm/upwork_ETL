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

    @task
    def reconstruct_csv(file_name):
        reconstruct(file_name)
        return

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
                print(f"Skipping {source.name}: already loaded")
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
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN;")

            # ==========================================
            # STEP 1: Safe Casting & JSON Parsing Helpers
            # ==========================================

            cursor.execute("""
                CREATE OR REPLACE FUNCTION parse_upwork_json(raw_text TEXT)
                RETURNS JSONB LANGUAGE plpgsql IMMUTABLE AS $$
                DECLARE
                    normalized_text TEXT;
                BEGIN
                    IF raw_text IS NULL OR btrim(raw_text) = '' OR btrim(raw_text) = '{}' THEN
                        RETURN NULL;
                    END IF;
                    
                    normalized_text := replace(
                        replace(raw_text, $q$'"$q$, '"'),
                        $q$"'$q$,
                        '"'
                    );

                    BEGIN
                        RETURN normalized_text::jsonb;
                    EXCEPTION WHEN OTHERS THEN
                        RETURN NULL;
                    END;
                END;
                $$;
            """)

            cursor.execute("""
                CREATE OR REPLACE FUNCTION safe_numeric(val TEXT) RETURNS NUMERIC LANGUAGE sql IMMUTABLE AS $$
                    SELECT CASE WHEN val IS NULL OR btrim(val) = '' THEN NULL ELSE val::numeric END;
                $$;
            """)

            cursor.execute("""
                CREATE OR REPLACE FUNCTION safe_int(val TEXT) RETURNS INT LANGUAGE sql IMMUTABLE AS $$
                    SELECT CASE WHEN val IS NULL OR btrim(val) = '' THEN NULL ELSE val::numeric::int END;
                $$;
            """)

            cursor.execute("""
                CREATE OR REPLACE FUNCTION safe_bigint(val TEXT) RETURNS BIGINT LANGUAGE sql IMMUTABLE AS $$
                    SELECT CASE WHEN val IS NULL OR btrim(val) = '' THEN NULL ELSE val::numeric::bigint END;
                $$;
            """)

            cursor.execute("""
                CREATE OR REPLACE FUNCTION safe_bool(val TEXT) RETURNS BOOLEAN LANGUAGE sql IMMUTABLE AS $$
                    SELECT CASE 
                        WHEN val IS NULL OR btrim(val) = '' THEN NULL 
                        WHEN lower(btrim(val)) IN ('true', 't', '1', 'yes') THEN TRUE
                        WHEN lower(btrim(val)) IN ('false', 'f', '0', 'no') THEN FALSE
                        ELSE NULL 
                    END;
                $$;
            """)

            cursor.execute("""
                CREATE OR REPLACE FUNCTION safe_timestamptz(val TEXT) RETURNS TIMESTAMPTZ LANGUAGE plpgsql IMMUTABLE AS $$
                BEGIN
                    IF val IS NULL OR btrim(val) = '' OR lower(btrim(val)) IN ('n/a', 'null', 'none') THEN
                        RETURN NULL;
                    END IF;
                    
                    IF val ~* 'ago|yesterday|just now|hours?|mins?|minutes?|days?|weeks?|months?|years?' THEN
                        RETURN NULL;
                    END IF;

                    RETURN val::timestamptz;
                EXCEPTION WHEN OTHERS THEN
                    RETURN NULL;
                END;
                $$;
            """)

            # ==========================================
            # STEP 2: Materialize Staging for Bucket B
            # ==========================================

            cursor.execute("DROP TABLE IF EXISTS stg_bucket_b_parsed;")
            cursor.execute("""
                CREATE UNLOGGED TABLE stg_bucket_b_parsed AS
                SELECT
                    id::bigint AS id,
                    url,
                    safe_timestamptz(crawled_date::text) AS crawled_date,
                    safe_timestamptz(created_at::text) AS created_at,
                    safe_timestamptz(updated_at::text) AS updated_at,
                    source_file,
                    source_hash,
                    safe_timestamptz(ingested_at::text) AS ingested_at,
                    parse_upwork_json(raw_data::text) AS j
                FROM bronze.upwork_raw_jobs
                WHERE raw_data IS NOT NULL AND btrim(raw_data::text) != '';
            """)

            # ==========================================
            # STEP 3: Build `silver_upwork_jobs` (Bucket B)
            # ==========================================

            cursor.execute("DROP TABLE IF EXISTS silver.silver_upwork_jobs;")
            cursor.execute("""
                CREATE TABLE silver.silver_upwork_jobs AS
                SELECT
                    id,
                    j->'opening'->'info'->>'id' AS upwork_job_id,
                    COALESCE(NULLIF(btrim(url), ''), 'https://www.upwork.com/jobs/' || (j->'opening'->'info'->>'ciphertext')) AS url,
                    'jobs_json'::text AS record_source_type,
                    crawled_date,
                    created_at,
                    updated_at,
                    source_file,
                    source_hash,
                    ingested_at,
                    j->'opening'->'info'->>'title' AS title,
                    j->'opening'->>'description' AS description,
                    safe_numeric(j->'opening'->'budget'->>'amount') AS budget,
                    LOWER(j->'opening'->'info'->>'type') AS budget_type,
                    safe_numeric(j->'opening'->'extendedBudgetInfo'->>'hourlyBudgetMin') AS hourly_rate_min,
                    safe_numeric(j->'opening'->'extendedBudgetInfo'->>'hourlyBudgetMax') AS hourly_rate_max,
                    j->'opening'->>'workload' AS work_type,
                    j->'opening'->>'contractorTier' AS experience_level,
                    j->'opening'->'engagementDuration'->>'label' AS duration,
                    j->'buyer'->'location'->>'country' AS location,
                    j->'opening'->'category'->>'name' AS category,
                    safe_int(j->'opening'->'clientActivity'->>'totalApplicants') AS proposals,
                    safe_timestamptz(j->'opening'->>'postedOn') AS posted_date,
                    ARRAY(
                        SELECT COALESCE(elem->>'prefLabel', elem->>'freeText')
                        FROM jsonb_array_elements(
                            CASE WHEN jsonb_typeof(j->'opening'->'sandsData'->'ontologySkills') = 'array' 
                                 THEN j->'opening'->'sandsData'->'ontologySkills' ELSE '[]'::jsonb END
                            ||
                            CASE WHEN jsonb_typeof(j->'opening'->'sandsData'->'additionalSkills') = 'array' 
                                 THEN j->'opening'->'sandsData'->'additionalSkills' ELSE '[]'::jsonb END
                        ) AS elem
                        WHERE COALESCE(elem->>'prefLabel', elem->>'freeText') IS NOT NULL
                    ) AS skills,
                    j->'opening'->'sandsData'->'ontologySkills' AS opening_sands_ontology_skills,
                    j->'opening'->'sandsData'->'additionalSkills' AS opening_sands_additional_skills,
                    j->'opening'->'info'->>'access' AS opening_info_access,
                    safe_bool(j->'opening'->'info'->>'premium') AS opening_info_premium,
                    safe_timestamptz(j->'opening'->'info'->>'createdOn') AS opening_info_created_on,
                    j->'opening'->'info'->>'ciphertext' AS opening_info_ciphertext,
                    safe_bool(j->'opening'->'info'->>'hideBudget') AS opening_info_hide_budget,
                    safe_bool(j->'opening'->'info'->>'notSureExperienceLevel') AS opening_info_not_sure_exp_level,
                    safe_bool(j->'opening'->'info'->>'notSureProjectDuration') AS opening_info_not_sure_duration,
                    safe_bool(j->'opening'->'info'->>'notSureFreelancersToHire') AS opening_info_not_sure_freelancers,
                    safe_bool(j->'opening'->'info'->>'notSureLocationPreference') AS opening_info_not_sure_location,
                    j->'opening'->'tools' AS opening_tools,
                    j->'opening'->'budget'->>'currencyCode' AS opening_budget_currency_code,
                    j->'opening'->>'status' AS opening_status,
                    j->'opening'->'category'->>'urlSlug' AS opening_category_url_slug,
                    j->'opening'->'categoryGroup'->>'name' AS opening_category_group_name,
                    j->'opening'->'categoryGroup'->>'urlSlug' AS opening_category_group_url_slug,
                    j->'opening'->>'deadline' AS opening_deadline,
                    j->'opening'->>'startDate' AS opening_start_date,
                    safe_timestamptz(j->'opening'->>'publishTime') AS opening_publish_time,
                    j->'opening'->'deliverables' AS opening_deliverables,
                    j->'opening'->>'deliveryDate' AS opening_delivery_date,
                    j->'opening'->>'sourcingTime' AS opening_sourcing_time,
                    safe_int(j->'opening'->'engagementDuration'->>'weeks') AS opening_engagement_duration_weeks,
                    j->'opening'->'extendedBudgetInfo'->>'hourlyBudgetType' AS opening_hourly_budget_type,
                    j->'opening'->'sandsData'->'occupation'->>'id' AS opening_occupation_id,
                    j->'opening'->'sandsData'->'occupation'->>'uid' AS opening_occupation_uid,
                    j->'opening'->'sandsData'->'occupation'->>'freeText' AS opening_occupation_free_text,
                    j->'opening'->'sandsData'->'occupation'->>'prefLabel' AS opening_occupation_pref_label,
                    j->'opening'->'sandsData'->'occupation'->>'ontologyId' AS opening_occupation_ontology_id,
                    j->'opening'->'annotations'->'tags' AS opening_annotations_tags,
                    j->'opening'->'annotations'->'customFields'->>'type' AS opening_custom_type,
                    j->'opening'->'annotations'->'customFields'->>'device' AS opening_custom_device,
                    j->'opening'->'annotations'->'customFields'->>'browser' AS opening_custom_browser,
                    j->'opening'->'annotations'->'customFields'->>'flowType' AS opening_custom_flow_type,
                    j->'opening'->'annotations'->'customFields'->>'siteSource' AS opening_custom_site_source,
                    safe_timestamptz(j->'opening'->'annotations'->'customFields'->>'publishTime') AS opening_custom_publish_time,
                    safe_int(j->'opening'->'annotations'->'customFields'->>'sourcingUpdateCount') AS opening_custom_sourcing_update_count,
                    j->'opening'->'annotations'->'customFields'->>'optInDescriptionAIv2' AS opening_custom_opt_in_ai_v2,
                    safe_bool(j->'opening'->'annotations'->'customFields'->>'sourcingUpdateForbidden') AS opening_custom_sourcing_forbidden,
                    CASE 
                        WHEN jsonb_typeof(j->'opening'->'annotations'->'customFields') = 'object'
                        THEN (j->'opening'->'annotations'->'customFields') - ARRAY[
                            'type', 'device', 'browser', 'flowType', 'siteSource', 
                            'publishTime', 'sourcingUpdateCount', 'optInDescriptionAIv2', 'sourcingUpdateForbidden'
                        ]
                        ELSE NULL
                    END AS opening_custom_fields_extra,
                    safe_int(j->'opening'->'clientActivity'->>'totalHired') AS opening_activity_total_hired,
                    safe_int(j->'opening'->'clientActivity'->>'invitationsSent') AS opening_activity_invitations_sent,
                    safe_timestamptz(j->'opening'->'clientActivity'->>'lastBuyerActivity') AS opening_activity_last_buyer_activity,
                    safe_int(j->'opening'->'clientActivity'->>'unansweredInvites') AS opening_activity_unanswered_invites,
                    safe_int(j->'opening'->'clientActivity'->>'numberOfPositionsToHire') AS opening_activity_positions_to_hire,
                    safe_int(j->'opening'->'clientActivity'->>'totalInvitedToInterview') AS opening_activity_total_invited,
                    j->'opening'->'segmentationData'->0->>'name' AS opening_segmentation_name,
                    j->'opening'->'segmentationData'->0->>'type' AS opening_segmentation_type,
                    j->'opening'->'segmentationData'->0->>'label' AS opening_segmentation_label,
                    j->'opening'->'segmentationData'->0->>'skill' AS opening_segmentation_skill,
                    j->'opening'->'segmentationData'->0->>'value' AS opening_segmentation_value,
                    safe_int(j->'opening'->'segmentationData'->0->>'sortOrder') AS opening_segmentation_sort_order,
                    j->'opening'->'segmentationData'->0->>'customValue' AS opening_segmentation_custom_value,
                    j->'opening'->'segmentationData' AS opening_segmentation_raw_array,
                    safe_int(j->'buyer'->'jobs'->>'openCount') AS buyer_jobs_open_count,
                    j->'buyer'->'jobs'->'openJobs' AS buyer_jobs_open_jobs,
                    safe_numeric(j->'buyer'->'stats'->>'score') AS buyer_stats_score,
                    safe_numeric(j->'buyer'->'stats'->>'hoursCount') AS buyer_stats_hours_count,
                    safe_numeric(j->'buyer'->'stats'->'totalCharges'->>'amount') AS buyer_stats_total_charges_amount,
                    safe_int(j->'buyer'->'stats'->>'feedbackCount') AS buyer_stats_feedback_count,
                    safe_int(j->'buyer'->'stats'->>'totalAssignments') AS buyer_stats_total_assignments,
                    safe_int(j->'buyer'->'stats'->>'totalJobsWithHires') AS buyer_stats_total_jobs_with_hires,
                    safe_int(j->'buyer'->'stats'->>'activeAssignmentsCount') AS buyer_stats_active_assignments_count,
                    j->'buyer'->'company'->'profile'->>'size' AS buyer_company_size,
                    j->'buyer'->'company'->'profile'->>'industry' AS buyer_company_industry,
                    safe_timestamptz(j->'buyer'->'company'->>'contractDate') AS buyer_company_contract_date,
                    safe_bool(j->'buyer'->'company'->>'isEDCReplicated') AS buyer_company_is_edc_replicated,
                    j->'buyer'->'location'->>'city' AS buyer_location_city,
                    j->'buyer'->'location'->>'countryTimezone' AS buyer_location_timezone,
                    safe_bigint(j->'buyer'->'location'->>'offsetFromUtcMillis') AS buyer_location_offset_utc_millis,
                    safe_bool(j->'buyerExtra'->>'isPaymentMethodVerified') AS buyer_extra_payment_verified,
                    j->'qualifications'->>'type' AS qual_type,
                    j->'qualifications'->>'group' AS qual_group,
                    j->'qualifications'->'tests' AS qual_tests,
                    j->'qualifications'->>'states' AS qual_states,
                    j->'qualifications'->>'regions' AS qual_regions,
                    j->'qualifications'->>'earnings' AS qual_earnings,
                    j->'qualifications'->'location' AS qual_location,
                    j->'qualifications'->'countries' AS qual_countries,
                    j->'qualifications'->>'languages' AS qual_languages,
                    j->'qualifications'->>'locations' AS qual_locations,
                    j->'qualifications'->>'timezones' AS qual_timezones,
                    j->'qualifications'->>'groupRecno' AS qual_group_recno,
                    j->'qualifications'->>'onSiteType' AS qual_on_site_type,
                    safe_bool(j->'qualifications'->>'localMarket') AS qual_local_market,
                    safe_int(j->'qualifications'->>'minHoursWeek') AS qual_min_hours_week,
                    safe_bool(j->'qualifications'->>'risingTalent') AS qual_rising_talent,
                    safe_int(j->'qualifications'->>'minOdeskHours') AS qual_min_odesk_hours,
                    j->'qualifications'->>'localDescription' AS qual_local_description,
                    j->'qualifications'->>'prefEnglishSkill' AS qual_pref_english_skill,
                    safe_int(j->'qualifications'->>'minJobSuccessScore') AS qual_min_job_success_score,
                    safe_bool(j->'qualifications'->>'shouldHavePortfolio') AS qual_should_have_portfolio,
                    safe_bool(j->'qualifications'->>'locationCheckRequired') AS qual_location_check_required,
                    j->'qualifications'->>'localFlexibilityDescription' AS qual_local_flexibility_description
                FROM stg_bucket_b_parsed;
            """)

            # ==========================================
            # STEP 4: Build `silver_freelance_jobs` (Bucket A)
            # ==========================================

            cursor.execute("DROP TABLE IF EXISTS silver.silver_freelance_jobs;")
            cursor.execute("""
                CREATE TABLE silver.silver_freelance_jobs AS
                SELECT
                    id::bigint AS id,
                    substring(url FROM '~02([0-9]+)') AS upwork_job_id,
                    url,
                    'freelance_jobs_flat'::text AS record_source_type,
                    safe_timestamptz(crawled_date::text) AS crawled_date,
                    safe_timestamptz(created_at::text) AS created_at,
                    safe_timestamptz(updated_at::text) AS updated_at,
                    source_file,
                    source_hash,
                    safe_timestamptz(ingested_at::text) AS ingested_at,
                    title,
                    description,
                    safe_numeric(budget::text) AS budget,
                    LOWER(budget_type) AS budget_type,
                    safe_numeric(hourly_rate_min::text) AS hourly_rate_min,
                    safe_numeric(hourly_rate_max::text) AS hourly_rate_max,
                    work_type,
                    experience_level,
                    duration,
                    location,
                    category,
                    safe_int(proposals::text) AS proposals,
                    safe_timestamptz(posted_date::text) AS posted_date,
                    CASE 
                        WHEN skills IS NULL OR btrim(skills::text) IN ('', '[]') THEN ARRAY[]::text[]
                        WHEN jsonb_typeof(raw_data::jsonb) = 'array' 
                             THEN ARRAY(SELECT jsonb_array_elements_text(raw_data::jsonb))
                        ELSE ARRAY[]::text[]
                    END AS skills,
                    substring(url FROM '(~02[0-9]+)') AS opening_info_ciphertext
                FROM bronze.upwork_raw_jobs
                WHERE raw_data IS NULL OR btrim(raw_data::text) = '';
            """)

            # ==========================================
            # STEP 5: Clean Up Staging
            # ==========================================

            cursor.execute("DROP TABLE IF EXISTS stg_bucket_b_parsed;")

            cursor.execute("COMMIT;")
        except Exception:
            cursor.execute("ROLLBACK;")
            raise
        finally:
            cursor.close()
            conn.close()

    @task
    def build_gold():
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN;")
            cursor.execute("CREATE SCHEMA IF NOT EXISTS gold;")
            cursor.execute("DROP TABLE IF EXISTS gold.gold_skill_rankings;")
            cursor.execute("""
                CREATE TABLE gold.gold_skill_rankings AS
                WITH job_skills AS (
                    SELECT DISTINCT
                        jobs.id AS job_id,
                        lower(btrim(skill_name)) AS skill
                    FROM silver.silver_upwork_jobs AS jobs
                    CROSS JOIN LATERAL unnest(jobs.skills) AS skill_name
                    WHERE nullif(btrim(skill_name), '') IS NOT NULL
                ),
                skill_counts AS (
                    SELECT skill, count(*) AS job_count
                    FROM job_skills
                    GROUP BY skill
                ),
                total AS (
                    SELECT count(DISTINCT job_id) AS jobs_with_skills
                    FROM job_skills
                )
                SELECT
                    rank() OVER (ORDER BY skill_counts.job_count DESC) AS skill_rank,
                    skill_counts.skill,
                    skill_counts.job_count,
                    total.jobs_with_skills,
                    round(
                        100.0 * skill_counts.job_count
                        / nullif(total.jobs_with_skills, 0),
                        2
                    ) AS percent_of_jobs
                FROM skill_counts
                CROSS JOIN total;
            """)
            cursor.execute("DROP TABLE IF EXISTS gold.gold_location_patterns;")
            cursor.execute("""
                CREATE TABLE gold.gold_location_patterns AS
                WITH location_rows AS (
                    SELECT
                        'country'::text AS location_level,
                        nullif(btrim(location), '') AS location,
                        proposals
                    FROM silver.silver_upwork_jobs

                    UNION ALL

                    SELECT
                        'city'::text AS location_level,
                        nullif(btrim(buyer_location_city), '') AS location,
                        proposals
                    FROM silver.silver_upwork_jobs

                    UNION ALL

                    SELECT
                        'location'::text AS location_level,
                        nullif(btrim(location), '') AS location,
                        proposals
                    FROM silver.silver_freelance_jobs
                ),
                location_counts AS (
                    SELECT
                        location_level,
                        location,
                        count(*) AS job_count,
                        count(proposals) AS jobs_with_proposals,
                        round(avg(proposals)::numeric, 2) AS avg_proposals
                    FROM location_rows
                    WHERE location IS NOT NULL
                    GROUP BY location_level, location
                )
                SELECT
                    rank() OVER (
                        PARTITION BY location_level
                        ORDER BY job_count DESC
                    ) AS location_rank,
                    location_level,
                    location,
                    job_count,
                    round(
                        100.0 * job_count
                        / nullif(sum(job_count) OVER (PARTITION BY location_level), 0),
                        2
                    ) AS percent_of_level_jobs,
                    jobs_with_proposals,
                    avg_proposals
                FROM location_counts;
            """)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    recon_task = reconstruct_csv("upwork_combined_data.csv")
    init_task = initialise()
    bronze_task = ingest_bronze(Path("include/data/reconstructed_data/upwork_reconstructed.csv"))
    silver_task = build_silver()
    gold_task = build_gold()
    
    recon_task >> init_task >> bronze_task >> silver_task >> gold_task

upworkETL_dag()
# Silver table columns

Silver has two cleaned job tables:

- `silver.silver_upwork_jobs` contains rows parsed from the full JSON payload (`record_source_type = jobs_json`).
- `silver.silver_freelance_jobs` contains rows parsed from the flatter source (`record_source_type = freelance_jobs_flat`).

## What one record (row) represents

Each row represents one collected **job-posting record**, not one client. The row contains the posting details, such as its title, description, budget, skills, category, and proposal count. In the JSON table it can also include a snapshot of buyer profile/activity details captured with that posting.

- A row in `silver_upwork_jobs` comes from a record with a JSON payload, so it has more opening and buyer detail.
- A row in `silver_freelance_jobs` comes from a flat freelance-jobs record, so it has fewer details.
- `id` identifies the source row; `upwork_job_id` identifies the job when available. Neither is a buyer ID.
- A buyer may have posted multiple jobs, but without a buyer ID these rows cannot reliably be grouped by client.
- `buyer_jobs_open_jobs`, when present, lists other open jobs reported in the buyer snapshot. Those nested jobs are not additional Silver rows unless they were separately collected as records.

Examples are illustrative, not necessarily values present in every row. Missing or invalid source values can appear as `NULL`. Nested source values are retained as JSON where noted.

## Columns in both tables

| Column | What it means; example or variation |
|---|---|
| `id` | Internal source-row ID, numeric; e.g. `12345`. Not a client ID. |
| `upwork_job_id` | Upwork job ID from the JSON or URL; e.g. `123456789`. |
| `url` | Job posting URL; e.g. `https://www.upwork.com/jobs/example`. |
| `record_source_type` | Source format; e.g. `jobs_json` or `freelance_jobs_flat`. |
| `crawled_date` | When the record was collected; e.g. `2026-10-31 12:00:00+00`, or `NULL`. |
| `created_at` | Source record creation timestamp; e.g. `2026-10-30 09:15:00+00`, or `NULL`. |
| `updated_at` | Source record update timestamp; e.g. `2026-10-31 10:00:00+00`, or `NULL`. |
| `source_file` | Input file name; e.g. `upwork_reconstructed.csv`. |
| `source_hash` | Identifier/hash for the input file batch; e.g. `a1b2c3...`. |
| `ingested_at` | When the source record was loaded; e.g. `2026-10-31 12:05:00+00`, or `NULL`. |
| `title` | Job title; e.g. `Build a Shopify store`. |
| `description` | Job description text; e.g. `Need a responsive website`, or a longer description/`NULL`. |
| `budget` | Fixed budget amount as a number; e.g. `500`. Currency is separate in the JSON table. |
| `budget_type` | Lowercase budget type where available; e.g. `fixed` or `hourly`. |
| `hourly_rate_min` | Minimum hourly rate; e.g. `20`, or `NULL` if unavailable. |
| `hourly_rate_max` | Maximum hourly rate; e.g. `40`, or `NULL` if unavailable. |
| `work_type` | Workload label; e.g. `More than 30 hrs/week`. Source wording varies. |
| `experience_level` | Requested experience tier; e.g. `INTERMEDIATE`, `Expert`. |
| `duration` | Project duration label; e.g. `1 to 3 months`. |
| `location` | JSON table: buyer country, e.g. `United States`. Flat table: source text, e.g. `Remote - United States`. |
| `category` | Job category name; e.g. `Web Development`. |
| `proposals` | Applicant/proposal count as an integer; e.g. `15`, or `NULL`. |
| `posted_date` | Job posting timestamp; e.g. `2026-10-30 08:30:00+00`, or `NULL`. |
| `skills` | Text array of extracted skill names; e.g. `{"Python","SQL"}`. Empty array if none were extracted. |

## Extra columns in `silver.silver_upwork_jobs`

### Skills, opening information, budget, and category

| Column | What it means; example or variation |
|---|---|
| `opening_sands_ontology_skills` | Original structured skill objects, including source labels/IDs; e.g. `[{"prefLabel":"Python","uid":"skill-id"}]`. |
| `opening_sands_additional_skills` | Original additional skill objects; e.g. `[{"freeText":"Shopify"}]`, `[]`, or `NULL`. |
| `opening_info_access` | Source visibility/access label; e.g. `PUBLIC_INDEX`. |
| `opening_info_premium` | Whether the opening is marked premium; e.g. `true`, `false`, or `NULL`. |
| `opening_info_created_on` | Opening creation timestamp; e.g. `2026-10-30 08:30:00+00`, or `NULL`. |
| `opening_info_ciphertext` | Opaque Upwork job code; e.g. `~02abc123`, used to construct the URL if needed. |
| `opening_info_hide_budget` | Whether the budget is hidden; e.g. `true`, `false`, or `NULL`. |
| `opening_info_not_sure_exp_level` | Client unsure about experience level; e.g. `true` or `false`. |
| `opening_info_not_sure_duration` | Client unsure about duration; e.g. `true` or `false`. |
| `opening_info_not_sure_freelancers` | Client unsure how many people to hire; e.g. `true` or `false`. |
| `opening_info_not_sure_location` | Client unsure about location preference; e.g. `true` or `false`. |
| `opening_tools` | Tools associated with the opening; e.g. `["Figma","WordPress"]` or another JSON shape. |
| `opening_budget_currency_code` | Budget currency; e.g. `USD`, `EUR`. |
| `opening_status` | Source opening status; e.g. `ACTIVE`, or `NULL`. |
| `opening_category_url_slug` | URL-friendly category name; e.g. `web-development`. |
| `opening_category_group_name` | Parent category group name; e.g. `Design & Creative`. |
| `opening_category_group_url_slug` | URL-friendly parent category group name; e.g. `design-creative`. |
| `opening_deadline` | Deadline value from the source; e.g. `2026-12-01`, format may vary. |
| `opening_start_date` | Requested start-date value; e.g. `2026-11-15`, format may vary. |
| `opening_publish_time` | Publish timestamp; e.g. `2026-10-30 08:30:00+00`, or `NULL`. |
| `opening_deliverables` | Deliverables from the source; e.g. `["Website","Documentation"]` or another JSON shape. |
| `opening_delivery_date` | Requested delivery-date value; e.g. `2026-12-15`, format may vary. |
| `opening_sourcing_time` | Source-provided sourcing-time value; e.g. `24h`, or another source value. |
| `opening_engagement_duration_weeks` | Engagement length in weeks; e.g. `8`. |
| `opening_hourly_budget_type` | Source hourly-budget label; e.g. `MANUAL`. |

### Occupation, annotations, activity, and segmentation

| Column | What it means; example or variation |
|---|---|
| `opening_occupation_id` | Source occupation ID; e.g. `1234`. |
| `opening_occupation_uid` | Source occupation UID; e.g. `occupation-abc123`. |
| `opening_occupation_free_text` | Client-entered occupation label; e.g. `AI app developer`, or `NULL`. |
| `opening_occupation_pref_label` | Standard occupation label; e.g. `Software Developer`, or `NULL`. |
| `opening_occupation_ontology_id` | Occupation taxonomy ID; e.g. `occupation-taxonomy-123`. |
| `opening_annotations_tags` | Source annotation tags; e.g. `["featured"]` or another JSON shape. |
| `opening_custom_type` | Custom-field type label; e.g. `web`. |
| `opening_custom_device` | Device label; e.g. `desktop`. |
| `opening_custom_browser` | Browser label; e.g. `Chrome`. |
| `opening_custom_flow_type` | Workflow label; e.g. `standard`. |
| `opening_custom_site_source` | Site/source label; e.g. `www`. |
| `opening_custom_publish_time` | Publish timestamp from custom fields; e.g. `2026-10-30 08:30:00+00`, or `NULL`. |
| `opening_custom_sourcing_update_count` | Sourcing update count; integer, e.g. `1`. |
| `opening_custom_opt_in_ai_v2` | AI opt-in value as source text; e.g. `true`, `false`, or another source string. |
| `opening_custom_sourcing_forbidden` | Whether sourcing updates are forbidden; e.g. `true` or `false`. |
| `opening_custom_fields_extra` | Other custom fields not extracted separately; e.g. `{"experiment":"variant-b"}` or `NULL`. |
| `opening_activity_total_hired` | Number hired on the opening; e.g. `2`. |
| `opening_activity_invitations_sent` | Invitations sent; e.g. `5`. |
| `opening_activity_last_buyer_activity` | Timestamp of the buyer's last activity; e.g. `2026-10-31 11:00:00+00`. |
| `opening_activity_unanswered_invites` | Unanswered invitations; e.g. `1`. |
| `opening_activity_positions_to_hire` | Number of positions the buyer wants to fill; e.g. `2`. |
| `opening_activity_total_invited` | People invited to interview; e.g. `4`. |
| `opening_segmentation_name` | Name from the first segmentation entry; e.g. `Experience level`. |
| `opening_segmentation_type` | Type from the first segmentation entry; e.g. `experience`. |
| `opening_segmentation_label` | Display label from the first segmentation entry; e.g. `Intermediate`. |
| `opening_segmentation_skill` | Skill value from the first segmentation entry; e.g. `Python`, or `NULL`. |
| `opening_segmentation_value` | Value from the first segmentation entry; e.g. `intermediate`, format varies. |
| `opening_segmentation_sort_order` | Sort position; integer, e.g. `1`. |
| `opening_segmentation_custom_value` | Custom value from the first segmentation entry; e.g. `Other`, or `NULL`. |
| `opening_segmentation_raw_array` | Complete segmentation data; e.g. `[{"name":"Experience level","value":"intermediate"}]`. |

### Buyer, company, and location

| Column | What it means; example or variation |
|---|---|
| `buyer_jobs_open_count` | Number of jobs the buyer reports as currently open; e.g. `3`. Not a lifetime job count. |
| `buyer_jobs_open_jobs` | JSON details for those open jobs; e.g. `[{"id":"job-123","uid":"uid-abc"}]`. These are job IDs/UIDs, not a buyer ID. |
| `buyer_stats_score` | Buyer's reported score/rating; numeric, e.g. `4.8`. |
| `buyer_stats_hours_count` | Buyer's reported accumulated hours; e.g. `1200`. |
| `buyer_stats_total_charges_amount` | Buyer's reported total charges; e.g. `25000.00`, without currency in this column. |
| `buyer_stats_feedback_count` | Number of feedback records; e.g. `18`. |
| `buyer_stats_total_assignments` | Total assignments reported for the buyer; e.g. `25`. |
| `buyer_stats_total_jobs_with_hires` | Jobs with hires reported for the buyer; e.g. `12`. |
| `buyer_stats_active_assignments_count` | Buyer's active assignments; e.g. `2`. |
| `buyer_company_size` | Company-size label; e.g. `Small company`. |
| `buyer_company_industry` | Company industry label; e.g. `Information Technology`. |
| `buyer_company_contract_date` | Company contract date; e.g. `2020-04-15 00:00:00+00`, or `NULL`. |
| `buyer_company_is_edc_replicated` | Source company replication flag; e.g. `true` or `false`. |
| `buyer_location_city` | Buyer's city; e.g. `Toronto`, or `NULL`. |
| `buyer_location_timezone` | Buyer's timezone label; e.g. `America/Toronto`. |
| `buyer_location_offset_utc_millis` | Buyer's UTC offset in milliseconds; e.g. `-18000000`. |
| `buyer_extra_payment_verified` | Whether the buyer's payment method is verified; e.g. `true`, `false`, or `NULL`. |

### Freelancer qualifications

These are requirements for applicants, not necessarily the buyer's location.

| Column | What it means; example or variation |
|---|---|
| `qual_type` | Qualification type; e.g. `location`. |
| `qual_group` | Qualification group; e.g. `location`. |
| `qual_tests` | Test requirements; e.g. `[{"name":"English test"}]` or another JSON shape. |
| `qual_states` | State requirement(s); e.g. `California`, or a source string with multiple values. |
| `qual_regions` | Region requirement(s); e.g. `North America`, or a source string with multiple values. |
| `qual_earnings` | Earnings requirement/value as source text; e.g. `1000`. |
| `qual_location` | Location requirement; e.g. `{"country":"United States"}` or another JSON shape. |
| `qual_countries` | Country requirement(s); e.g. `US`, or source text with multiple values. |
| `qual_languages` | Language requirement(s); e.g. `English`, or source text with multiple values. |
| `qual_locations` | Location requirement(s); e.g. `United States`, or source text with multiple values. |
| `qual_timezones` | Timezone requirement(s); e.g. `UTC-5`, or source text with multiple values. |
| `qual_group_recno` | Qualification group record number; e.g. `12345`. |
| `qual_on_site_type` | On-site/remote requirement label; e.g. `REMOTE`. |
| `qual_local_market` | Whether a local-market requirement applies; e.g. `true` or `false`. |
| `qual_min_hours_week` | Minimum hours per week; integer, e.g. `10`. |
| `qual_rising_talent` | Whether Rising Talent status is required; e.g. `true` or `false`. |
| `qual_min_odesk_hours` | Minimum prior platform hours; e.g. `100`. |
| `qual_local_description` | Description of a local requirement; e.g. `Must be located in the US`. |
| `qual_pref_english_skill` | Preferred English skill level; e.g. `Fluent` or another source value. |
| `qual_min_job_success_score` | Minimum Job Success Score; integer, e.g. `90`. |
| `qual_should_have_portfolio` | Whether a portfolio is required; e.g. `true` or `false`. |
| `qual_location_check_required` | Whether a location check is required; e.g. `true` or `false`. |
| `qual_local_flexibility_description` | Explanation of location flexibility; e.g. `Nearby regions may apply`. |

## Extra column in `silver.silver_freelance_jobs`

| Column | What it means; example or variation |
|---|---|
| `opening_info_ciphertext` | Opaque Upwork job code extracted from the URL; e.g. a `~02...` token. |

## Notes about values

- The current DAG selects specific fields from the JSON; it does not preserve every JSON key as its own column.
- Numeric, integer, boolean, and timestamp fields are converted to their respective types. Empty or unparseable values may become `NULL`; invalid numeric casts can also fail the Silver build.
- JSON fields retain nested source data, whose contents and shape can vary.
- The Silver build does not explicitly change zero hourly-budget values to `NULL`.
- `location` differs by source: the JSON table uses the buyer's country, while the flat table retains the source location text. Use `buyer_location_city` for city detail when it exists.

## Original `raw_data` tree

The reconstructed `raw_data` column contains JSON objects. The source has more than one shape: some records have flat, pre-extracted fields at the root, while others (or the same records) have detailed `buyer`, `opening`, `buyerExtra`, and `qualifications` objects. Fields can be absent or `null`. This is the tree observed in the current data, not a guarantee of every field Upwork may ever provide.

```text
raw_data
├── flat job/client fields (listed below)
├── buyer
│   ├── company
│   ├── jobs
│   ├── location
│   └── stats
├── buyerExtra
├── opening
│   ├── annotations
│   ├── budget
│   ├── category / categoryGroup
│   ├── clientActivity
│   ├── engagementDuration / extendedBudgetInfo
│   ├── info
│   ├── sandsData
│   ├── segmentationData
│   └── other posting fields
└── qualifications
```

### Flat root fields

These are already-flattened job and buyer values. Some overlap with the nested fields below.

| Field | What it means |
|---|---|
| `category` | Job category name. |
| `category_group` | Parent category group name. |
| `ciphertext` | Opaque Upwork job code. |
| `client_active_hires` | Client's number of active hires/assignments. |
| `client_city` | Client's city. |
| `client_company_size` | Client company's size label or value. |
| `client_company_summary` | Short company description. |
| `client_country` | Client's country. |
| `client_feedback_count` | Number of client feedback records. |
| `client_hours` | Client's accumulated work hours. |
| `client_industry` | Client company's industry. |
| `client_member_since` | When the client joined, if provided. |
| `client_open_jobs` | Number of jobs the client currently has open. |
| `client_open_jobs_list` | Array of open-job summaries; fields are described below. |
| `client_payment_verified` | Whether the client's payment method is verified. |
| `client_rating` | Client's reported rating/score. |
| `client_state` | Client's state or region. |
| `client_timezone` | Client's timezone. |
| `client_total_hires` | Client's total hires. |
| `client_total_jobs_with_hires` | Number of client jobs that resulted in hires. |
| `client_total_spent` | Client's reported total spending. |
| `client_utc_offset` | Client's UTC offset, often represented as text. |
| `contractor_tier` | Requested freelancer experience tier. |
| `duration` | Project duration label. |
| `english_level` | Required or preferred English level. |
| `fixed_price_amount` | Fixed-price budget amount, if applicable. |
| `fixed_price_currency` | Currency for the fixed-price amount. |
| `has_details` | Whether additional job details are available. |
| `hiring_now` | Whether the client is currently hiring. |
| `hourly_budget_max` | Maximum hourly budget. |
| `hourly_budget_min` | Minimum hourly budget. |
| `interviewing` | Number of applicants currently being interviewed, if supplied. |
| `invites_sent` | Number of invitations sent. |
| `job_description` | Job description text. |
| `job_id` | Job identifier. It is not a client identifier. |
| `job_title` | Job title. |
| `job_type` | Contract/budget type, such as hourly or fixed-price. |
| `job_url` | URL of the job posting. |
| `last_buyer_activity` | Timestamp/text describing the client's last activity. |
| `min_job_success_score` | Minimum Job Success Score requested. |
| `occupation` | Occupation or role label. |
| `portfolio_required` | Whether a portfolio is required. |
| `positions_to_hire` | Number of people the client plans to hire. |
| `posted_on` | Job posting time. |
| `publish_time` | Time the posting was published. |
| `qualifications` | Applicant qualification requirements; may also be represented by the nested object below. |
| `required_countries` | Countries eligible to apply from. |
| `required_languages` | Required languages. |
| `required_regions` | Eligible regions. |
| `required_timezones` | Eligible time zones. |
| `rising_talent_only` | Whether Rising Talent status is required. |
| `skills` | Requested skill names. |
| `total_applicants` | Number of applicants/proposals. |
| `total_hired` | Number hired for the posting. |
| `unanswered_invites` | Number of unanswered invitations. |
| `workload` | Expected workload, such as hours per week. |

### `client_open_jobs_list[]`

Each item summarizes one of the client's open jobs; it is not a buyer ID.

| Field | What it means |
|---|---|
| `job_id` | Identifier of that open job. |
| `job_url` | URL of that open job. |
| `title` | Open-job title. |
| `type` | Open-job type, such as hourly or fixed-price. |

### `buyer`

#### `buyer.company`

| Field | What it means |
|---|---|
| `contractDate` | Date associated with the company's Upwork contract/profile. |
| `isEDCReplicated` | Source company replication flag. |
| `profile.industry` | Industry listed on the company profile. |
| `profile.size` | Company size listed on the profile. |

#### `buyer.jobs`

| Field | What it means |
|---|---|
| `openCount` | Number of jobs the buyer reports as currently open. |
| `openJobs[]` | Array of open-job records described below. |
| `openJobs[].ciphertext` | Opaque job code for that open job. |
| `openJobs[].id` | ID of that open job, not the buyer. |
| `openJobs[].isPtcPrivate` | Whether that open job is marked private by the source. |
| `openJobs[].title` | Title of that open job. |
| `openJobs[].type` | Type of that open job, such as hourly or fixed-price. |
| `openJobs[].uid` | UID of that open job, not the buyer. |

#### `buyer.location`

| Field | What it means |
|---|---|
| `city` | Buyer's city. |
| `country` | Buyer's country. |
| `countryTimezone` | Timezone associated with the buyer's country/location. |
| `offsetFromUtcMillis` | UTC offset in milliseconds. |

#### `buyer.stats`

| Field | What it means |
|---|---|
| `activeAssignmentsCount` | Number of the buyer's active assignments. |
| `feedbackCount` | Number of feedback records for the buyer. |
| `hoursCount` | Buyer's accumulated hours. |
| `score` | Buyer's reported score/rating. |
| `totalAssignments` | Buyer's total assignments. |
| `totalCharges.amount` | Buyer's reported total charges amount. |
| `totalJobsWithHires` | Number of buyer's jobs that resulted in hires. |

### `buyerExtra`

| Field | What it means |
|---|---|
| `isPaymentMethodVerified` | Whether the buyer's payment method is verified. |

### `opening`

#### `opening.info`

| Field | What it means |
|---|---|
| `access` | Posting access/visibility label. |
| `ciphertext` | Opaque job code, often usable to build the job URL. |
| `createdOn` | Time the opening was created. |
| `hideBudget` | Whether the budget is hidden. |
| `id` | Upwork job ID. |
| `notSureExperienceLevel` | Whether the client is unsure about experience level. |
| `notSureFreelancersToHire` | Whether the client is unsure how many people to hire. |
| `notSureLocationPreference` | Whether the client is unsure about location preference. |
| `notSureProjectDuration` | Whether the client is unsure about project duration. |
| `premium` | Whether the posting is marked premium. |
| `title` | Job title. |
| `type` | Job/budget type. |

#### `opening.budget` and `opening.extendedBudgetInfo`

| Field | What it means |
|---|---|
| `budget.amount` | Fixed budget amount. |
| `budget.currencyCode` | Currency code for the budget. |
| `extendedBudgetInfo.hourlyBudgetMax` | Maximum hourly budget. |
| `extendedBudgetInfo.hourlyBudgetMin` | Minimum hourly budget. |
| `extendedBudgetInfo.hourlyBudgetType` | Source label describing the hourly budget. |

#### `opening.category` and `opening.categoryGroup`

| Field | What it means |
|---|---|
| `category.name` | Job category name. |
| `category.urlSlug` | URL-friendly category name. |
| `categoryGroup.name` | Parent category group name. |
| `categoryGroup.urlSlug` | URL-friendly parent category group name. |

#### Other `opening` fields

| Field | What it means |
|---|---|
| `contractorTier` | Requested freelancer experience tier. |
| `deadline` | Project deadline, if provided. |
| `deliverables` | Deliverables requested; source value may be text or structured data. |
| `deliveryDate` | Requested delivery date. |
| `description` | Full job description. |
| `postedOn` | When the job was posted. |
| `publishTime` | When the job was published. |
| `sourcingTime` | Source-provided sourcing-time value. |
| `startDate` | Requested project start date. |
| `status` | Posting status. |
| `workload` | Expected work schedule/workload. |

#### `opening.engagementDuration`

| Field | What it means |
|---|---|
| `label` | Human-readable project duration, such as `1 to 3 months`. |
| `weeks` | Duration as a number of weeks. |

#### `opening.clientActivity`

| Field | What it means |
|---|---|
| `invitationsSent` | Number of invitations sent for the posting. |
| `lastBuyerActivity` | Time of the buyer's last activity. |
| `numberOfPositionsToHire` | Number of positions the buyer wants to fill. |
| `totalApplicants` | Number of applicants/proposals. |
| `totalHired` | Number hired for this opening. |
| `totalInvitedToInterview` | Number invited to interview. |
| `unansweredInvites` | Number of unanswered invitations. |

#### `opening.sandsData`

| Field | What it means |
|---|---|
| `additionalSkills[]` | Additional skill entries supplied with the posting. Each can have `freeText`, `groupId`, `id`, `prefLabel`, and `relevance`. |
| `additionalSkills[].freeText` | Skill name entered as free text, if any. |
| `additionalSkills[].groupId` | Source skill-group identifier. |
| `additionalSkills[].id` | Source skill identifier. |
| `additionalSkills[].prefLabel` | Preferred/standard skill label. |
| `additionalSkills[].relevance` | Source relevance label/value. |
| `ontologySkills[]` | Skills matched to Upwork's skill taxonomy. |
| `ontologySkills[].freeText` | Optional free-text skill value. |
| `ontologySkills[].groupId` | Identifier for the skill group. |
| `ontologySkills[].groupPrefLabel` | Display name of the skill group. |
| `ontologySkills[].id` | Taxonomy skill identifier. |
| `ontologySkills[].prefLabel` | Standard skill label. |
| `ontologySkills[].relevance` | Source relevance label/value. |
| `occupation` | Occupation/role classification described below. |
| `occupation.freeText` | Free-text occupation label. |
| `occupation.id` | Occupation identifier. |
| `occupation.ontologyId` | Occupation taxonomy identifier. |
| `occupation.prefLabel` | Standard occupation label. |
| `occupation.uid` | Occupation UID. |

#### `opening.annotations`

| Field | What it means |
|---|---|
| `tags` | Source annotation tags; array of labels/values. |
| `customFields.advanced_preferences` | Serialized advanced-preference metadata; source-specific. |
| `customFields.aj_sort` | Serialized job-post sorting metadata; source-specific. |
| `customFields.browser` | Browser reported during the posting flow. |
| `customFields.buildJobAiInput` | Serialized AI input used in a job-building flow. |
| `customFields.buildJobImportedDescription` | Whether/metadata indicating an imported job description; source-specific. |
| `customFields.buildJobImportedTitle` | Whether/metadata indicating an imported job title; source-specific. |
| `customFields.descriptionDifferenceScoreAIv2` | AI-related description difference score/metadata. |
| `customFields.device` | Device reported during the posting flow. |
| `customFields.expertiseAskedAIv2` | Expertise-level input/metadata from the AI-assisted flow. |
| `customFields.finalDescriptionAI` | AI-related final-description metadata/value. |
| `customFields.finalDescriptionAIv2` | Version 2 AI-related final-description metadata/value. |
| `customFields.finalInputsAIv2` | Final inputs to the version 2 AI flow. |
| `customFields.flowType` | Type of job-posting workflow. |
| `customFields.fp_sort` | Serialized fixed-price sorting metadata; source-specific. |
| `customFields.generate_prompt` | Prompt-generation metadata/value. |
| `customFields.generatedDescriptionAI` | AI-generated description metadata/value. |
| `customFields.generatedDescriptionAIv2` | Version 2 AI-generated description metadata/value. |
| `customFields.generatedDescriptionHistoryAIV2` | History/metadata for version 2 AI-generated descriptions. |
| `customFields.generatedInputsAIv2` | Inputs generated for the version 2 AI flow. |
| `customFields.goalFirstEntryGoal` | Goal value from the first-entry posting flow. |
| `customFields.inputsDurationAI` | Duration input/metadata for the AI flow. |
| `customFields.inputsSkillsAI` | Skill inputs/metadata for the AI flow. |
| `customFields.inputsTitleAI` | Title input/metadata for the AI flow. |
| `customFields.jpgV2Prompt` | Prompt metadata for the source's JPG version 2 flow; exact meaning is source-specific. |
| `customFields.optInDescriptionAI` | Whether the description AI feature was opted into; source value is text. |
| `customFields.optInDescriptionAIv2` | Version 2 description AI opt-in value; source value is text. |
| `customFields.publishTime` | Publish-time value stored in custom metadata. |
| `customFields.recommendationId` | ID of a source recommendation. |
| `customFields.recommendationKind` | Type of source recommendation. |
| `customFields.recommendedOccupationUid` | UID of a recommended occupation. |
| `customFields.retriesAIv2` | Retry count/metadata for the version 2 AI flow. |
| `customFields.reuse` | Reuse-flow metadata/value. |
| `customFields.siteSource` | Site/source label for the posting flow. |
| `customFields.sourcingTime` | Sourcing-time metadata. |
| `customFields.sourcingUpdateCount` | Number of sourcing updates. |
| `customFields.sourcingUpdateForbidden` | Whether sourcing updates are forbidden. |
| `customFields.startTimeJobPostFlowAIv2` | Start-time metadata for the version 2 job-posting flow. |
| `customFields.template` | Posting template label/metadata. |
| `customFields.timeSpentToGetAPIDescriptionAI` | Time-spent metadata for obtaining an AI description. |
| `customFields.totalDescriptionEditingTimeAI` | Total editing-time metadata for the AI description flow. |
| `customFields.totalDescriptionEditingTimeAIv2` | Version 2 AI description editing-time metadata. |
| `customFields.totalTimeJobPostFlowAIv2` | Total-time metadata for the version 2 posting flow. |
| `customFields.totalTimeSpentOnDescriptionPageAI` | Time-spent metadata on the AI description page. |
| `customFields.totalTimeSpentOnReviewPageAIv2` | Time-spent metadata on the version 2 review page. |
| `customFields.type` | Custom-field type label. |
| `customFields.urgency` | Source urgency label/value. |

#### `opening.segmentationData[]` and `opening.tools[]`

| Field | What it means |
|---|---|
| `segmentationData[].customValue` | Custom value for a segmentation entry. |
| `segmentationData[].label` | Human-readable segmentation label. |
| `segmentationData[].name` | Segmentation field name. |
| `segmentationData[].skill` | Skill associated with the entry, if any. |
| `segmentationData[].sortOrder` | Display/order position. |
| `segmentationData[].type` | Segmentation entry type. |
| `segmentationData[].value` | Segmentation value. |
| `tools[].name` | Name of a tool associated with the posting. |

### `qualifications`

These fields describe applicant requirements. The separate `location` object below is a qualification/location filter, not necessarily the buyer's location.

| Field | What it means |
|---|---|
| `type` | Qualification rule type. |
| `group` | Qualification group/category. |
| `groupRecno` | Qualification group record number. |
| `tests` | Required test criteria, if provided. |
| `states` | Eligible states. |
| `regions` | Eligible regions. |
| `earnings` | Earnings-related requirement/value. |
| `location` | Structured location requirement. |
| `location.city` | City in the applicant location filter. |
| `location.country` | Country in the applicant location filter. |
| `location.countryTimezone` | Timezone for that qualification location. |
| `location.offsetFromUtcMillis` | UTC offset for that location, in milliseconds. |
| `location.state` | State in that qualification location. |
| `location.worldRegion` | World region in that qualification location. |
| `countries` | Eligible countries. |
| `languages` | Required languages. |
| `locations` | Eligible locations. |
| `timezones` | Eligible time zones. |
| `onSiteType` | On-site/remote requirement. |
| `localMarket` | Whether a local-market requirement applies. |
| `minHoursWeek` | Minimum weekly hours. |
| `risingTalent` | Whether Rising Talent status is required. |
| `minOdeskHours` | Minimum prior platform hours. |
| `localDescription` | Text explaining a local requirement. |
| `prefEnglishSkill` | Preferred English skill level. |
| `minJobSuccessScore` | Minimum Job Success Score. |
| `shouldHavePortfolio` | Whether a portfolio is required. |
| `locationCheckRequired` | Whether a location check is required. |
| `localFlexibilityDescription` | Explanation of any flexibility around local requirements. |

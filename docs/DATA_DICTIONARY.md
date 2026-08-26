# LinkedIn Agent Analytics — Data Dictionary

## Overview

The LinkedIn Agent Analytics pipeline uses SQLite with a star-schema
architecture for analytical reporting.

---

## Dimension Tables

### dim_candidate

| Column | Type | Description |
|---|---|---|
| candidate_key | INTEGER | Surrogate key for candidate |
| source_id | TEXT | Unique source/API identifier |
| candidate_name | TEXT | Candidate/lead name |
| status | TEXT | Current candidate status |
| created_at | TEXT | Candidate creation timestamp |

### dim_company

| Column | Type | Description |
|---|---|---|
| company_key | INTEGER | Surrogate company key |
| company_name | TEXT | Company name |

### dim_job

| Column | Type | Description |
|---|---|---|
| job_key | INTEGER | Surrogate job key |
| job_title | TEXT | Job title |
| company_key | INTEGER | Related company |

### dim_location

| Column | Type | Description |
|---|---|---|
| location_key | INTEGER | Surrogate location key |
| location_name | TEXT | Job/candidate location |

### dim_status

| Column | Type | Description |
|---|---|---|
| status_key | INTEGER | Surrogate status key |
| status_name | TEXT | Lead status |

### dim_date

| Column | Type | Description |
|---|---|---|
| date_key | INTEGER | Date dimension key |
| calendar_date | TEXT | Calendar date |
| year | INTEGER | Year |
| quarter | INTEGER | Calendar quarter |
| month | INTEGER | Month number |
| month_name | TEXT | Month name |
| day | INTEGER | Day of month |

---

## Fact Tables

### fact_lead

Stores the analytical grain of individual lead records.

| Column | Type | Description |
|---|---|---|
| lead_key | INTEGER | Unique fact record |
| candidate_key | INTEGER | Candidate dimension reference |
| job_key | INTEGER | Job dimension reference |
| company_key | INTEGER | Company dimension reference |
| location_key | INTEGER | Location dimension reference |
| date_key | INTEGER | Date dimension reference |
| lead_status | TEXT | Lead status |
| lead_count | INTEGER | Lead count measure |
| created_at | TEXT | Record creation timestamp |
| updated_at | TEXT | Record update timestamp |

---

## Operational Tables

### leads

Stores the normalized operational lead records received from the API.

### pipeline_runs

Tracks each ingestion run, including input/output counts,
status, watermark and error information.

### pipeline_state

Stores incremental pipeline watermarks.

### dead_letter_records

Stores malformed or failed records that could not be processed.

---

## Analytical Grain

The primary analytical grain of `fact_lead` is:

> One record per candidate/lead observation.

This enables analysis by:

- Candidate
- Company
- Job
- Location
- Status
- Date

---

## Relationships

```text
dim_candidate ─────┐
dim_job ───────────┤
dim_company ───────┤
dim_location ──────┼──> fact_lead
dim_date ──────────┤
dim_status ────────┘
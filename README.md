# LinkedIn Agent Analytics

A Python-based data ingestion and analytics pipeline designed to fetch LinkedIn lead data from an API, process and validate the records, store them in SQLite, track incremental updates using a watermark, and handle invalid records through a dead-letter mechanism.

## Features

- API-based lead ingestion
- Incremental data loading using watermark
- Lead validation
- SQLite database storage
- Upsert support for duplicate leads
- Pipeline run tracking
- Dead-letter handling for invalid records
- API retry handling
- Analytics summary
- Automated tests using pytest
- Environment-based API configuration

---

## Tech Stack

- **Python 3**
- **SQLite**
- **Requests**
- **python-dotenv**
- **Pytest**

---

## Project Structure

```text
linkedin-agent-analytics/
│
├── data/
│   └── linkedin_agent_analytics.db
│
├── src/
│   ├── __init__.py
│   ├── api_client.py
│   ├── analytics.py
│   ├── config.py
│   ├── database.py
│   └── pipeline.py
│
├── tests/
│   ├── test_api_client.py
│   └── test_pipeline.py
│
├── .env
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt


## Architecture

The pipeline follows this general flow:

API
 │
 ▼
API Client
 │
 ▼
Extract Records
 │
 ▼
Validate Records
 │
 ├────────────── Invalid ──────────────► Dead Letter
 │
 ▼
Normalize Records
 │
 ▼
SQLite Database
 │
 ▼
Watermark Update
 │
 ▼
Pipeline Analytics

---

## Configuration

Create a `.env` file in the project root:

```env
API_BASE_URL=https://api.example.com
API_TOKEN=your_api_token

---

## Database

The project uses SQLite for data storage.

Database file:

```text
data/linkedin_agent_analytics.db

Database Tables
1. leads

Stores processed LinkedIn lead information.
| Column       | Description               |
| ------------ | ------------------------- |
| `id`         | Primary key               |
| `source_id`  | Unique source identifier  |
| `name`       | Lead name                 |
| `job_title`  | Lead job title            |
| `company`    | Company name              |
| `location`   | Lead location             |
| `status`     | Lead status               |
| `updated_at` | Last update timestamp     |
| `created_at` | Record creation timestamp |


2. pipeline_runs

Stores information about each pipeline execution.

| Column          | Description                              |
| --------------- | ---------------------------------------- |
| `run_id`        | Pipeline run identifier                  |
| `started_at`    | Start timestamp                          |
| `ended_at`      | End timestamp                            |
| `rows_in`       | Number of input records                  |
| `rows_out`      | Number of successfully processed records |
| `status`        | Pipeline execution status                |
| `error_message` | Error details                            |
| `watermark`     | Watermark used for the run               |

3. dead_letter_records

Stores records that could not be processed successfully.

| Column          | Description               |
| --------------- | ------------------------- |
| `id`            | Primary key               |
| `run_id`        | Related pipeline run      |
| `source_id`     | Source identifier         |
| `payload`       | Original record payload   |
| `error_message` | Processing error          |
| `created_at`    | Record creation timestamp |

4. pipeline_state

Stores the watermark used for incremental processing.
| Column          | Description                |
| --------------- | -------------------------- |
| `pipeline_name` | Pipeline name              |
| `watermark`     | Latest processed timestamp |


---

## Incremental Loading

The pipeline uses a watermark-based incremental loading strategy.

Before making an API request, the pipeline retrieves the previously stored watermark.

If a watermark exists, it is sent to the API using:

```text
updated_after=<watermark>


---

## Data Validation

Each incoming lead is validated before being stored.

The minimum required field is:

```text
source_id


---

## Idempotent Processing

The `source_id` field is unique in the `leads` table.

If the same lead is processed multiple times, the pipeline updates the existing record instead of creating a duplicate.

This ensures that repeated pipeline runs do not create duplicate lead records.

The pipeline can therefore safely reprocess the same source data while maintaining data consistency.


---

## API Client

The API client is implemented using the `requests` library.

It provides the following capabilities:

- GET requests
- Bearer token authentication
- JSON response handling
- Request timeout
- Retry handling
- Connection error handling
- HTTP error handling
- HTTP 429 rate-limit handling
- `Retry-After` header support

The API client automatically retries temporary connection and timeout failures before raising an error.

For HTTP 429 responses, the client respects the `Retry-After` header when available.


---

## Error Handling

The pipeline handles errors at both record and pipeline levels.

### Record-Level Errors

If an individual lead fails validation or processing, the record is stored in the:

```text
dead_letter_records


---

## Analytics

The project includes a lightweight analytics module that provides a summary of pipeline execution.

Run the analytics module with:

```powershell
python -m src.analytics



Example output:
========== PIPELINE ANALYTICS ==========
Total Pipeline Runs : 24
Total Rows In       : 36
Total Rows Out      : 30
Processing Success  : 83.33%
=========================================


### Next — `Running the Project`

`README.md` me **Analytics ke just neeche** ye paste karo:

````markdown id="r5k2nd"
---

## Running the Project

### Step 1 — Create Virtual Environment

Windows:

```powershell
python -m venv .venv
````

### Step 2 — Activate Virtual Environment

```powershell
.venv\Scripts\Activate.ps1
```

### Step 3 — Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### Step 4 — Configure Environment Variables

Create a `.env` file in the project root:

```env
API_BASE_URL=https://api.example.com
API_TOKEN=your_api_token
```

Replace the example values with the actual API configuration.

### Step 5 — Initialize Database

```powershell
python -m src.database
```

Expected output:

```text
Database initialized successfully.
```

### Step 6 — Run the Pipeline

```powershell
python -m src.pipeline
```

### Step 7 — Run Analytics

```powershell
python -m src.analytics
```

### Step 8 — Run Tests

```powershell
python -m pytest -v
```

Expected test result:

```text
5 passed
```


### Next — `Testing`

`README.md` me **Running the Project ke just neeche** ye पूरा section paste karo:

````markdown
---

## Testing

The project uses `pytest` for automated testing.

Run all tests with:

```powershell
python -m pytest -v
````

The current test suite covers:

* API client functionality
* Successful pipeline execution
* Idempotent processing
* Invalid record handling
* Watermark persistence

Pipeline tests use mocked API responses so that they do not depend on a live external API.

### Test Result

```text
5 passed
```

A successful test run confirms that the core API client and pipeline functionality is working as expected.

```

---

## Security

API credentials are stored using environment variables.

The `.env` file contains sensitive configuration such as:

- API base URL
- API authentication token

Never commit real API tokens, passwords, or other secrets to GitHub.

The `.env` file should be added to `.gitignore` so that credentials remain local.

For production use, secrets should be managed through a secure secrets-management system.


---

## Future Improvements

The following improvements can be added in future versions of the project:

- Production API integration
- Scheduled pipeline execution
- Advanced data quality checks
- Structured application logging
- Pipeline monitoring and alerting
- Additional database indexes
- Dashboard integration using Power BI
- Cloud database integration
- Automated deployment
- More detailed data quality and pipeline metrics


---

## Project Status

**Status: Functional and Tested**

The current implementation includes:

- API client
- Bearer token authentication
- Retry and rate-limit handling
- Lead validation
- Incremental data loading
- Watermark management
- SQLite database persistence
- Idempotent processing
- Dead-letter record handling
- Pipeline analytics
- Automated testing

### Current Test Result

```text
5 passed



---

## Author

**Abhishek Yadav**

B.Tech – Computer Science & Engineering

### Skills Demonstrated

- Python
- SQL / SQLite
- API Integration
- Data Engineering
- ETL / ELT Concepts
- Data Validation
- Error Handling
- Automated Testing
- Incremental Data Processing


## Data Quality

The pipeline includes automated data quality checks covering:

- Completeness
- Uniqueness
- Validity
- Timeliness
- Referential Integrity

A composite Data Quality score is calculated from these checks.

Run the Data Quality report:

```bash
python src/data_quality.py

Completeness          : 100.00%
Uniqueness            : 100.00%
Validity              : 100.00%
Timeliness            : 100.00%
Referential Integrity : 100.00%
Composite DQ Score    : 100.00%


## Testing

Run the complete test suite:

```bash
python -m pytest -v


Database

The project uses SQLite for local persistence.

The database contains operational tables for:

Leads
Pipeline runs
Pipeline state
Dead-letter records

The analytical layer uses a star-schema design with dimension and fact tables.

The local SQLite database is intentionally excluded from GitHub through .gitignore.

Security

API credentials are stored in environment variables and are not committed to GitHub.


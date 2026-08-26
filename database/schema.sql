-- ============================================================
-- LinkedIn Agent Analytics - Star Schema
-- Database: SQLite
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- Candidate / Lead dimension
CREATE TABLE IF NOT EXISTS dim_candidate (
    candidate_key INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL UNIQUE,
    candidate_name TEXT,
    status TEXT,
    created_at TEXT NOT NULL
);

-- Company dimension
CREATE TABLE IF NOT EXISTS dim_company (
    company_key INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL UNIQUE
);

-- Job dimension
CREATE TABLE IF NOT EXISTS dim_job (
    job_key INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT NOT NULL,
    company_key INTEGER,
    FOREIGN KEY (company_key)
        REFERENCES dim_company(company_key)
);

-- Location dimension
CREATE TABLE IF NOT EXISTS dim_location (
    location_key INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name TEXT NOT NULL UNIQUE
);

-- Date dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL
);

-- ============================================================
-- FACT TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_lead (
    lead_key INTEGER PRIMARY KEY AUTOINCREMENT,

    candidate_key INTEGER NOT NULL,
    job_key INTEGER,
    company_key INTEGER,
    location_key INTEGER,
    date_key INTEGER,

    lead_status TEXT,
    lead_count INTEGER NOT NULL DEFAULT 1,

    created_at TEXT NOT NULL,
    updated_at TEXT,

    FOREIGN KEY (candidate_key)
        REFERENCES dim_candidate(candidate_key),

    FOREIGN KEY (job_key)
        REFERENCES dim_job(job_key),

    FOREIGN KEY (company_key)
        REFERENCES dim_company(company_key),

    FOREIGN KEY (location_key)
        REFERENCES dim_location(location_key),

    FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key)
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fact_lead_candidate
ON fact_lead(candidate_key);

CREATE INDEX IF NOT EXISTS idx_fact_lead_job
ON fact_lead(job_key);

CREATE INDEX IF NOT EXISTS idx_fact_lead_company
ON fact_lead(company_key);

CREATE INDEX IF NOT EXISTS idx_fact_lead_location
ON fact_lead(location_key);

CREATE INDEX IF NOT EXISTS idx_fact_lead_date
ON fact_lead(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_lead_status
ON fact_lead(lead_status);

-- ============================================================
-- END OF STAR SCHEMA
-- ============================================================
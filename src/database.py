import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data") / "linkedin_agent_analytics.db"


def get_db_connection():
    """Get a connection to the SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable named column access
    return conn


def initialize_database():
    """Create the SQLite schema if it does not already exist."""
    conn = get_db_connection()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL UNIQUE,
            name TEXT,
            job_title TEXT,
            company TEXT,
            location TEXT,
            status TEXT,
            updated_at TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            rows_in INTEGER DEFAULT 0,
            rows_out INTEGER DEFAULT 0,
            status TEXT,
            error_message TEXT,
            watermark TEXT
        );

        CREATE TABLE IF NOT EXISTS dead_letter_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            source_id TEXT,
            payload TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pipeline_state (
            pipeline_name TEXT PRIMARY KEY,
            watermark TEXT
        );

                -- =========================
        -- PART 3: ANALYTICAL MODEL
        -- =========================

        CREATE TABLE IF NOT EXISTS dim_lead (
            lead_key INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL UNIQUE,
            name TEXT,
            job_title TEXT,
            location TEXT,
            effective_from TEXT NOT NULL,
            effective_to TEXT,
            is_current INTEGER NOT NULL DEFAULT 1
                CHECK (is_current IN (0, 1))
        );

        CREATE TABLE IF NOT EXISTS dim_company (
            company_key INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS dim_status (
            status_key INTEGER PRIMARY KEY AUTOINCREMENT,
            status_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS dim_date (
            date_key INTEGER PRIMARY KEY,
            calendar_date TEXT NOT NULL UNIQUE,
            year INTEGER NOT NULL,
            quarter INTEGER NOT NULL,
            month INTEGER NOT NULL,
            month_name TEXT NOT NULL,
            day INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fact_lead_activity (
            activity_key INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_key INTEGER NOT NULL,
            company_key INTEGER,
            status_key INTEGER,
            date_key INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            activity_timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL,

            FOREIGN KEY (lead_key)
                REFERENCES dim_lead(lead_key),

            FOREIGN KEY (company_key)
                REFERENCES dim_company(company_key),

            FOREIGN KEY (status_key)
                REFERENCES dim_status(status_key),

            FOREIGN KEY (date_key)
                REFERENCES dim_date(date_key),

            UNIQUE (source_id, activity_timestamp)
        );
        """
    )

    conn.commit()
    conn.close()


def get_watermark(pipeline_name="linkedin_leads"):
    """Get the watermark for a specific pipeline."""
    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT watermark
        FROM pipeline_state
        WHERE pipeline_name = ?
        """,
        (pipeline_name,),
    ).fetchone()

    conn.close()
    return row["watermark"] if row else None


def update_watermark(watermark, pipeline_name="linkedin_leads"):
    """Update the watermark for a specific pipeline."""
    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO pipeline_state (pipeline_name, watermark)
        VALUES (?, ?)
        ON CONFLICT(pipeline_name)
        DO UPDATE SET watermark = excluded.watermark
        """,
        (pipeline_name, watermark),
    )

    conn.commit()
    conn.close()


def upsert_lead(lead):
    """Insert or update a lead record."""
    conn = get_db_connection()

    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO leads (
            source_id,
            name,
            job_title,
            company,
            location,
            status,
            updated_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_id)
        DO UPDATE SET
            name = excluded.name,
            job_title = excluded.job_title,
            company = excluded.company,
            location = excluded.location,
            status = excluded.status,
            updated_at = excluded.updated_at
        """,
        (
            lead["source_id"],
            lead.get("name"),
            lead.get("job_title"),
            lead.get("company"),
            lead.get("location"),
            lead.get("status"),
            lead.get("updated_at", now),
            now,
        ),
    )

    conn.commit()
    conn.close()


def create_pipeline_run():
    """Create a new pipeline run entry."""
    conn = get_db_connection()

    started_at = datetime.now(timezone.utc).isoformat()

    cursor = conn.execute(
        """
        INSERT INTO pipeline_runs (started_at, status)
        VALUES (?, ?)
        """,
        (started_at, "running"),
    )

    run_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return run_id


def finish_pipeline_run(
    run_id,
    rows_in,
    rows_out,
    status,
    watermark=None,
    error_message=None,
):
    """Finish a pipeline run entry."""
    conn = get_db_connection()

    ended_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        UPDATE pipeline_runs
        SET ended_at = ?,
            rows_in = ?,
            rows_out = ?,
            status = ?,
            watermark = ?,
            error_message = ?
        WHERE run_id = ?
        """,
        (ended_at, rows_in, rows_out, status, watermark, error_message, run_id),
    )

    conn.commit()
    conn.close()


def add_dead_letter(run_id, source_id, payload, error_message):
    """Add a dead letter record."""
    conn = get_db_connection()

    created_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO dead_letter_records (
            run_id,
            source_id,
            payload,
            error_message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (run_id, source_id, payload, error_message, created_at),
    )

    conn.commit()
    conn.close()

def load_analytical_model(lead):
    """
    Load a processed lead into the analytical Star Schema.

    Grain:
    One row in fact_lead_activity represents one lead activity
    at a specific activity timestamp.
    """

    conn = get_db_connection()

    now = datetime.now(timezone.utc).isoformat()

    source_id = str(lead["source_id"])
    company_name = lead.get("company")
    status_name = lead.get("status")
    updated_at = lead.get("updated_at") or now

    # ---------------------------------------------------------
    # 1. Date Dimension
    # ---------------------------------------------------------

    dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

    date_key = int(dt.strftime("%Y%m%d"))

    conn.execute(
        """
        INSERT OR IGNORE INTO dim_date (
            date_key,
            calendar_date,
            year,
            quarter,
            month,
            month_name,
            day
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date_key,
            dt.date().isoformat(),
            dt.year,
            ((dt.month - 1) // 3) + 1,
            dt.month,
            dt.strftime("%B"),
            dt.day,
        ),
    )

    # ---------------------------------------------------------
    # 2. Company Dimension
    # ---------------------------------------------------------

    company_key = None

    if company_name:
        conn.execute(
            """
            INSERT OR IGNORE INTO dim_company (company_name)
            VALUES (?)
            """,
            (company_name,),
        )

        row = conn.execute(
            """
            SELECT company_key
            FROM dim_company
            WHERE company_name = ?
            """,
            (company_name,),
        ).fetchone()

        company_key = row["company_key"]

    # ---------------------------------------------------------
    # 3. Status Dimension
    # ---------------------------------------------------------

    status_key = None

    if status_name:
        conn.execute(
            """
            INSERT OR IGNORE INTO dim_status (status_name)
            VALUES (?)
            """,
            (status_name,),
        )

        row = conn.execute(
            """
            SELECT status_key
            FROM dim_status
            WHERE status_name = ?
            """,
            (status_name,),
        ).fetchone()

        status_key = row["status_key"]

    # ---------------------------------------------------------
    # 4. Lead Dimension
    # ---------------------------------------------------------

    lead_row = conn.execute(
        """
        SELECT lead_key
        FROM dim_lead
        WHERE source_id = ?
        """,
        (source_id,),
    ).fetchone()

    if lead_row:
        lead_key = lead_row["lead_key"]

        conn.execute(
            """
            UPDATE dim_lead
            SET name = ?,
                job_title = ?,
                location = ?,
                effective_from = ?,
                is_current = 1
            WHERE lead_key = ?
            """,
            (
                lead.get("name"),
                lead.get("job_title"),
                lead.get("location"),
                updated_at,
                lead_key,
            ),
        )

    else:
        cursor = conn.execute(
            """
            INSERT INTO dim_lead (
                source_id,
                name,
                job_title,
                location,
                effective_from,
                effective_to,
                is_current
            )
            VALUES (?, ?, ?, ?, ?, NULL, 1)
            """,
            (
                source_id,
                lead.get("name"),
                lead.get("job_title"),
                lead.get("location"),
                updated_at,
            ),
        )

        lead_key = cursor.lastrowid

    # ---------------------------------------------------------
    # 5. Fact Table
    # ---------------------------------------------------------

    conn.execute(
        """
        INSERT OR IGNORE INTO fact_lead_activity (
            lead_key,
            company_key,
            status_key,
            date_key,
            source_id,
            activity_timestamp,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lead_key,
            company_key,
            status_key,
            date_key,
            source_id,
            updated_at,
            now,
        ),
    )

    conn.commit()
    conn.close()

def get_pipeline_summary():
    """Return basic pipeline analytics."""
    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_runs,
            COALESCE(SUM(rows_in), 0) AS total_rows_in,
            COALESCE(SUM(rows_out), 0) AS total_rows_out
        FROM pipeline_runs
        """
    ).fetchone()

    conn.close()

    return {
        "total_runs": row["total_runs"],
        "total_rows_in": row["total_rows_in"],
        "total_rows_out": row["total_rows_out"],
    }


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
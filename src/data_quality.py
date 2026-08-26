import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DB_PATH = Path("data") / "linkedin_agent_analytics.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def completeness_check(conn):
    """
    Checks whether required lead fields contain NULL/empty values.
    """
    if not table_exists(conn, "leads"):
        return 0.0

    columns = get_columns(conn, "leads")

    possible_required = [
        "candidate_id",
        "candidate_name",
        "company_id",
        "job_id",
        "status",
    ]

    required = [c for c in possible_required if c in columns]

    if not required:
        return 100.0

    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    if total == 0:
        return 100.0

    valid_rows = 0

    conditions = []
    for column in required:
        conditions.append(
            f"NULLIF(TRIM(CAST({column} AS TEXT)), '') IS NOT NULL"
        )

    query = f"""
        SELECT COUNT(*)
        FROM leads
        WHERE {" AND ".join(conditions)}
    """

    valid_rows = conn.execute(query).fetchone()[0]

    return round((valid_rows / total) * 100, 2)


def uniqueness_check(conn):
    """
    Checks duplicate candidate records.
    """
    if not table_exists(conn, "leads"):
        return 0.0

    columns = get_columns(conn, "leads")

    key_column = None

    for column in ["candidate_id", "lead_id", "id"]:
        if column in columns:
            key_column = column
            break

    if key_column is None:
        return 100.0

    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    if total == 0:
        return 100.0

    unique_count = conn.execute(
        f"""
        SELECT COUNT(DISTINCT {key_column})
        FROM leads
        WHERE {key_column} IS NOT NULL
        """
    ).fetchone()[0]

    return round((unique_count / total) * 100, 2)


def validity_check(conn):
    """
    Checks whether lead status values are valid.
    """
    if not table_exists(conn, "leads"):
        return 0.0

    columns = get_columns(conn, "leads")

    if "status" not in columns:
        return 100.0

    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    if total == 0:
        return 100.0

    allowed_statuses = {
        "new",
        "contacted",
        "qualified",
        "rejected",
        "hired",
        "closed",
        "dead",
    }

    rows = conn.execute(
        "SELECT status FROM leads WHERE status IS NOT NULL"
    ).fetchall()

    if not rows:
        return 100.0

    valid = sum(
        1 for row in rows
        if str(row[0]).strip().lower() in allowed_statuses
    )

    return round((valid / len(rows)) * 100, 2)


def timeliness_check(conn):
    """
    Checks whether lead records have a usable created/updated timestamp.
    """
    if not table_exists(conn, "leads"):
        return 0.0

    columns = get_columns(conn, "leads")

    timestamp_column = None

    for column in [
        "created_at",
        "updated_at",
        "created_date",
        "updated_date",
    ]:
        if column in columns:
            timestamp_column = column
            break

    if timestamp_column is None:
        return 100.0

    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    if total == 0:
        return 100.0

    valid = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM leads
        WHERE {timestamp_column} IS NOT NULL
          AND TRIM(CAST({timestamp_column} AS TEXT)) != ''
        """
    ).fetchone()[0]

    return round((valid / total) * 100, 2)


def referential_integrity_check(conn):
    """
    Checks foreign-key violations reported by SQLite.
    """
    violations = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if violations:
        return 0.0

    return 100.0


def calculate_dq_score(results):
    """
    Calculates the composite Data Quality score.
    """
    if not results:
        return 0.0

    return round(sum(results.values()) / len(results), 2)


def run_data_quality_checks():
    """
    Runs all Data Quality checks and returns a structured result.
    """
    conn = get_connection()

    try:
        results = {
            "completeness": completeness_check(conn),
            "uniqueness": uniqueness_check(conn),
            "validity": validity_check(conn),
            "timeliness": timeliness_check(conn),
            "referential_integrity": referential_integrity_check(conn),
        }

        results["composite_score"] = calculate_dq_score(
            {
                key: value
                for key, value in results.items()
                if key != "composite_score"
            }
        )

        results["checked_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        return results

    finally:
        conn.close()


def print_data_quality_report():
    results = run_data_quality_checks()

    print("\n========== DATA QUALITY REPORT ==========")

    print(f"Completeness          : {results['completeness']:.2f}%")
    print(f"Uniqueness            : {results['uniqueness']:.2f}%")
    print(f"Validity              : {results['validity']:.2f}%")
    print(f"Timeliness            : {results['timeliness']:.2f}%")
    print(
        f"Referential Integrity : "
        f"{results['referential_integrity']:.2f}%"
    )

    print("-----------------------------------------")
    print(
        f"Composite DQ Score    : "
        f"{results['composite_score']:.2f}%"
    )
    print(f"Checked At             : {results['checked_at']}")
    print("=========================================\n")


if __name__ == "__main__":
    print_data_quality_report()
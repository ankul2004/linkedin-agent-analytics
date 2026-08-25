import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import run_pipeline
from src.database import (
    get_db_connection,
    get_watermark,
)


def test_pipeline_success():

    mock_response = {
        "data": [
            {
                "source_id": "LI001",
                "name": "Test User",
                "job_title": "Data Analyst",
                "company": "Test Company",
                "location": "Noida",
                "status": "NEW",
                "updated_at": "2026-08-22T10:00:00+00:00",
            },
            {
                "source_id": "LI002",
                "name": "Another User",
                "job_title": "Business Analyst",
                "company": "Demo Company",
                "location": "Delhi",
                "status": "NEW",
                "updated_at": "2026-08-22T11:00:00+00:00",
            },
        ]
    }

    with patch(
        "src.pipeline.APIClient.get",
        return_value=mock_response
    ):

        result = run_pipeline(
            endpoint="/mock-leads"
        )

    assert result["status"] == "SUCCESS"
    assert result["rows_in"] == 2
    assert result["rows_out"] == 2
    assert result["watermark"] == "2026-08-22T11:00:00+00:00"


def test_idempotent_pipeline():

    mock_response = {
        "data": [
            {
                "source_id": "LI003",
                "name": "Duplicate Test",
                "job_title": "Data Analyst",
                "company": "Test Company",
                "location": "Noida",
                "status": "NEW",
                "updated_at": "2026-08-22T12:00:00+00:00",
            }
        ]
    }

    with patch(
        "src.pipeline.APIClient.get",
        return_value=mock_response
    ):

        run_pipeline(endpoint="/mock-leads")
        run_pipeline(endpoint="/mock-leads")

    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM leads
        WHERE source_id = ?
        """,
        ("LI003",),
    ).fetchone()

    conn.close()

    assert row["count"] == 1


def test_bad_record_goes_to_dead_letter():

    mock_response = {
        "data": [
            {
                "source_id": "LI004",
                "name": "Valid User",
                "job_title": "Data Analyst",
                "company": "Test Company",
                "location": "Noida",
                "status": "NEW",
                "updated_at": "2026-08-22T13:00:00+00:00",
            },
            {
                "name": "Invalid User",
                "job_title": "Data Analyst",
            },
        ]
    }

    with patch(
        "src.pipeline.APIClient.get",
        return_value=mock_response
    ):

        result = run_pipeline(
            endpoint="/mock-leads"
        )

    assert result["rows_in"] == 2
    assert result["rows_out"] == 1

    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM dead_letter_records
        WHERE source_id IS NULL
        """
    ).fetchone()

    conn.close()

    assert row["count"] >= 1


def test_watermark_is_saved():

    watermark = get_watermark("linkedin_leads")

    assert watermark is not None
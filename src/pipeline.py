import json
from datetime import datetime, timezone

from src.api_client import APIClient
from src.database import (
    initialize_database,
    get_watermark,
    update_watermark,
    upsert_lead,
    get_pipeline_summary,
    create_pipeline_run,
    finish_pipeline_run,
    add_dead_letter
)

PIPELINE_NAME = "linkedin_leads"


def validate_lead(lead):
    """ Validate the minimum fields required for a lead."""

    if not isinstance(lead, dict):
        raise ValueError("Lead must be a dictionary.")  

    source_id = lead.get("source_id")

    if not source_id:
        raise ValueError("source_id is required")

    return True


def normalized_lead(lead):
    """ Convert API response into our database format"""

    return {
        "source_id":str(lead["source_id"]),
        "name":lead.get("name"),
        "job_title":lead.get("job_title"),
        "company":lead.get("company"),
        "location":lead.get("location"),
        "status":lead.get("status"),
        "updated_at":lead.get("updated_at"),
    }

def extract_records(response):
    """ 
    Extract records from API response.

      Expected structure:
      {
            "data": [...]
      }
      """

    if isinstance(response, dict):
        records = response.get("data", [])

        if not isinstance(records, list):
            raise ValueError("'data' must be a list")

        return records

    raise ValueError("API response must be a JSON object")

def run_pipeline(endpoint="/leads"):
    """ Run the commplete incremental ingestion pipeline."""

    initialize_database()

    run_id = create_pipeline_run()

    rows_in = 0
    rows_out = 0
    current_watermark = get_watermark(PIPELINE_NAME)

    try:
        client = APIClient()

        # Incremental loading:
        # send the previous watermark to the API
        params = {}

        if current_watermark:
            params["updated_after"] = current_watermark

        response = client.get(
            endpoint, 
            params=params
        )

        client.close()

        records = extract_records(response)

        rows_in = len(records)

        # Start with no new watermark from this response; we'll compute the latest
        # updated_at among the records we fetch. Keep current_watermark so we can
        # fall back when there are no new records.
        new_watermark = None

        for record in records:
            try:
                validate_lead(record)

                lead = normalized_lead(record)

                upsert_lead(lead)

                rows_out += 1

                # Track the latest updated timestamp
                record_watermark = record.get("updated_at")

                if record_watermark:
                    if (
                        new_watermark is None
                        or record_watermark > new_watermark
                    ):
                        new_watermark = record_watermark

            except Exception as record_error:

                add_dead_letter(
                    run_id=run_id,
                    source_id=record.get("source_id"),
                    payload=json.dumps(record),
                    error_message=str(record_error),
                )

        # Determine final watermark: prefer the latest timestamp from the
        # current response (new_watermark) but fall back to the existing
        # current_watermark if there were no records or none had timestamps.
        final_watermark = new_watermark if new_watermark is not None else current_watermark

        # only update watermark after processing the complete API response.
        if final_watermark:
            update_watermark(final_watermark, PIPELINE_NAME)

        finish_pipeline_run(
            run_id=run_id,
            rows_in=rows_in,
            rows_out=rows_out,
            status="SUCCESS",
            watermark=final_watermark,
        )

        return {
            "run_id": run_id,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "status": "SUCCESS",
            "watermark": final_watermark,
        }

    except Exception as pipeline_error:

        finish_pipeline_run(
            run_id=run_id,
            rows_in=rows_in,
            rows_out=rows_out,
            status="FAILED",
            watermark=current_watermark,
            error_message=str(pipeline_error),
        )

        raise


if __name__ == "__main__":
    result = run_pipeline()

    print("Pipeline run completed:")
    print(result)
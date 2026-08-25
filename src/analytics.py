from src.database import get_pipeline_summary


def print_pipeline_summary():
    """Print basic pipeline analytics."""

    summary = get_pipeline_summary()

    print("\n========== PIPELINE ANALYTICS ==========")
    print(f"Total Pipeline Runs : {summary['total_runs']}")
    print(f"Total Rows In       : {summary['total_rows_in']}")
    print(f"Total Rows Out      : {summary['total_rows_out']}")

    if summary["total_rows_in"] > 0:
        success_rate = (
            summary["total_rows_out"] / summary["total_rows_in"]
        ) * 100

        print(f"Processing Success  : {success_rate:.2f}%")

    print("=========================================\n")


if __name__ == "__main__":
    print_pipeline_summary()
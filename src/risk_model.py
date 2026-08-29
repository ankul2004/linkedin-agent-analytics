import sqlite3
from pathlib import Path
from statistics import mean, pstdev
from datetime import datetime, timezone


DB_PATH = Path("data") / "linkedin_agent_analytics.db"

# Observable status proxies from the available source data.
ACCEPTED_STATUSES = {"accepted", "qualified", "interview", "hired"}
REPLIED_STATUSES = {"replied", "contacted", "qualified", "interview", "hired"}
GHOST_STATUSES = {"new", "follow_up"}

# Risk thresholds.
MEDIUM_RISK = 0.50
HIGH_RISK = 0.75

# Tier ceilings from the account-capacity requirement.
TIER_CEILINGS = {
    "STANDARD": 25,
    "CONSERVATIVE": 15,
    "RESTRICTED": 10,
}


def get_connection():
    return sqlite3.connect(DB_PATH)


def normalise_status(value):
    return str(value or "").strip().lower()


def load_daily_observations(conn):
    """
    Creates daily outcome observations from the available lead records.

    The current source schema does not contain direct invite/reply counters,
    so status transitions are used as observable proxies.
    """
    rows = conn.execute(
        """
        SELECT
            date(created_at) AS observation_date,
            COUNT(*) AS total_leads,
            SUM(
                CASE
                    WHEN lower(trim(status)) IN
                    ('accepted', 'qualified', 'interview', 'hired')
                    THEN 1 ELSE 0
                END
            ) AS accepted_count,
            SUM(
                CASE
                    WHEN lower(trim(status)) IN
                    ('replied', 'contacted', 'qualified', 'interview', 'hired')
                    THEN 1 ELSE 0
                END
            ) AS replied_count,
            SUM(
                CASE
                    WHEN lower(trim(status)) IN
                    ('new', 'follow_up')
                    THEN 1 ELSE 0
                END
            ) AS ghost_count
        FROM leads
        GROUP BY date(created_at)
        ORDER BY observation_date
        """
    ).fetchall()

    observations = []

    for row in rows:
        observation_date, total, accepted, replied, ghost = row

        total = total or 0
        accepted = accepted or 0
        replied = replied or 0
        ghost = ghost or 0

        if total == 0:
            continue

        observations.append(
            {
                "date": observation_date,
                "total": total,
                "acceptance_rate": accepted / total,
                "reply_rate": replied / total,
                "ghost_rate": ghost / total,
            }
        )

    return observations


def safe_z_score(value, values):
    """
    Calculates a population z-score.

    If fewer than 3 historical observations exist, the statistical
    baseline is considered insufficient and returns 0.
    """
    if len(values) < 3:
        return 0.0

    standard_deviation = pstdev(values)

    if standard_deviation == 0:
        return 0.0

    return (value - mean(values)) / standard_deviation


def anomaly_from_z(z_score):
    """
    Converts a z-score into a bounded 0-1 anomaly magnitude.

    |z| >= 3 is treated as a severe deviation.
    """
    return round(min(abs(z_score) / 3.0, 1.0), 4)


def decline_risk(current, baseline):
    """
    Measures deterioration relative to historical baseline.

    Positive values mean the current metric is worse than baseline.
    """
    if baseline <= 0:
        return 0.0

    decline = (baseline - current) / baseline

    return round(max(0.0, min(decline, 1.0)), 4)


def increase_risk(current, baseline):
    """
    Measures increase in ghosting relative to historical baseline.
    """
    if baseline <= 0:
        return 0.0

    increase = (current - baseline) / baseline

    return round(max(0.0, min(increase, 1.0)), 4)


def calculate_capacity(risk_score):
    """
    Risk-adjusted daily capacity.

    STANDARD ceiling = 25.
    Higher risk progressively reduces the recommendation.
    """
    if risk_score >= HIGH_RISK:
        return TIER_CEILINGS["RESTRICTED"]

    if risk_score >= MEDIUM_RISK:
        return TIER_CEILINGS["CONSERVATIVE"]

    return TIER_CEILINGS["STANDARD"]


def classify_risk(score):
    if score >= HIGH_RISK:
        return "HIGH"

    if score >= MEDIUM_RISK:
        return "MEDIUM"

    return "LOW"


def calculate_model(observations):
    if not observations:
        return {
            "sample_size": 0,
            "baseline_available": False,
            "acceptance_rate": 0.0,
            "reply_rate": 0.0,
            "ghost_rate": 0.0,
            "risk_score": 0.0,
            "risk_band": "INSUFFICIENT_DATA",
            "recommended_daily_capacity": TIER_CEILINGS["CONSERVATIVE"],
            "confidence": "LOW",
        }

    current = observations[-1]

    acceptance_values = [
        item["acceptance_rate"] for item in observations
    ]

    reply_values = [
        item["reply_rate"] for item in observations
    ]

    ghost_values = [
        item["ghost_rate"] for item in observations
    ]

    # Historical baseline excludes the current observation.
    historical = observations[:-1]

    if historical:
        acceptance_baseline = mean(
            item["acceptance_rate"] for item in historical
        )
        reply_baseline = mean(
            item["reply_rate"] for item in historical
        )
        ghost_baseline = mean(
            item["ghost_rate"] for item in historical
        )
    else:
        acceptance_baseline = current["acceptance_rate"]
        reply_baseline = current["reply_rate"]
        ghost_baseline = current["ghost_rate"]

    acceptance_z = safe_z_score(
        current["acceptance_rate"],
        acceptance_values,
    )

    reply_z = safe_z_score(
        current["reply_rate"],
        reply_values,
    )

    ghost_z = safe_z_score(
        current["ghost_rate"],
        ghost_values,
    )

    acceptance_anomaly = anomaly_from_z(acceptance_z)
    reply_anomaly = anomaly_from_z(reply_z)
    ghost_anomaly = anomaly_from_z(ghost_z)

    acceptance_decline = decline_risk(
        current["acceptance_rate"],
        acceptance_baseline,
    )

    reply_decline = decline_risk(
        current["reply_rate"],
        reply_baseline,
    )

    ghost_increase = increase_risk(
        current["ghost_rate"],
        ghost_baseline,
    )

    # Weighted risk score:
    # 40% acceptance collapse
    # 30% reply decay
    # 30% ghosting increase
    risk_score = round(
        (
            acceptance_decline * 0.40
            + reply_decline * 0.30
            + ghost_increase * 0.30
        ),
        4,
    )

    # Use statistical anomaly evidence when enough observations exist.
    if len(observations) >= 3:
        statistical_component = round(
            (
                acceptance_anomaly
                + reply_anomaly
                + ghost_anomaly
            ) / 3,
            4,
        )

        risk_score = round(
            (risk_score * 0.70) + (statistical_component * 0.30),
            4,
        )

    confidence = "LOW"

    if len(observations) >= 7:
        confidence = "MEDIUM"

    if len(observations) >= 30:
        confidence = "HIGH"

    return {
        "sample_size": len(observations),
        "baseline_available": len(historical) >= 3,
        "acceptance_rate": current["acceptance_rate"],
        "reply_rate": current["reply_rate"],
        "ghost_rate": current["ghost_rate"],
        "acceptance_baseline": acceptance_baseline,
        "reply_baseline": reply_baseline,
        "ghost_baseline": ghost_baseline,
        "acceptance_z": acceptance_z,
        "reply_z": reply_z,
        "ghost_z": ghost_z,
        "acceptance_anomaly": acceptance_anomaly,
        "reply_anomaly": reply_anomaly,
        "ghost_anomaly": ghost_anomaly,
        "acceptance_decline": acceptance_decline,
        "reply_decline": reply_decline,
        "ghost_increase": ghost_increase,
        "risk_score": risk_score,
        "risk_band": classify_risk(risk_score),
        "recommended_daily_capacity": calculate_capacity(risk_score),
        "confidence": confidence,
    }


def create_history_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_model_history (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at TEXT NOT NULL,
            sample_size INTEGER NOT NULL,
            acceptance_rate REAL NOT NULL,
            reply_rate REAL NOT NULL,
            ghost_rate REAL NOT NULL,
            acceptance_baseline REAL NOT NULL,
            reply_baseline REAL NOT NULL,
            ghost_baseline REAL NOT NULL,
            acceptance_anomaly REAL NOT NULL,
            reply_anomaly REAL NOT NULL,
            ghost_anomaly REAL NOT NULL,
            risk_score REAL NOT NULL,
            risk_band TEXT NOT NULL,
            recommended_daily_capacity INTEGER NOT NULL,
            confidence TEXT NOT NULL
        )
        """
    )

    conn.commit()


def save_result(conn, result):
    conn.execute(
        """
        INSERT INTO risk_model_history (
            checked_at,
            sample_size,
            acceptance_rate,
            reply_rate,
            ghost_rate,
            acceptance_baseline,
            reply_baseline,
            ghost_baseline,
            acceptance_anomaly,
            reply_anomaly,
            ghost_anomaly,
            risk_score,
            risk_band,
            recommended_daily_capacity,
            confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            result["sample_size"],
            result["acceptance_rate"],
            result["reply_rate"],
            result["ghost_rate"],
            result.get("acceptance_baseline", 0.0),
            result.get("reply_baseline", 0.0),
            result.get("ghost_baseline", 0.0),
            result.get("acceptance_anomaly", 0.0),
            result.get("reply_anomaly", 0.0),
            result.get("ghost_anomaly", 0.0),
            result["risk_score"],
            result["risk_band"],
            result["recommended_daily_capacity"],
            result["confidence"],
        ),
    )

    conn.commit()


def run_model():
    conn = get_connection()

    try:
        observations = load_daily_observations(conn)

        result = calculate_model(observations)

        create_history_table(conn)
        save_result(conn, result)

        return result

    finally:
        conn.close()


def print_report():
    result = run_model()

    print("\n========== ADVANCED RISK REPORT ==========")

    print(f"Observation Days       : {result['sample_size']}")
    print(f"Confidence              : {result['confidence']}")

    print("------------------------------------------")

    print(
        f"Acceptance Rate         : "
        f"{result['acceptance_rate'] * 100:.2f}%"
    )

    print(
        f"Reply Rate              : "
        f"{result['reply_rate'] * 100:.2f}%"
    )

    print(
        f"Ghost Rate              : "
        f"{result['ghost_rate'] * 100:.2f}%"
    )

    print("------------------------------------------")

    print(
        f"Acceptance Anomaly      : "
        f"{result.get('acceptance_anomaly', 0.0):.4f}"
    )

    print(
        f"Reply Anomaly           : "
        f"{result.get('reply_anomaly', 0.0):.4f}"
    )

    print(
        f"Ghosting Anomaly        : "
        f"{result.get('ghost_anomaly', 0.0):.4f}"
    )

    print("------------------------------------------")

    print(f"Risk Score              : {result['risk_score']:.4f}")
    print(f"Risk Band               : {result['risk_band']}")
    print(
        f"Recommended Daily Cap   : "
        f"{result['recommended_daily_capacity']}"
    )

    print("------------------------------------------")

    print("Statistical Method      : Population z-score")
    print("Risk Weights            : 40% / 30% / 30%")
    print("Severe anomaly          : |z| >= 3")
    print("Tier ceiling baseline   : 25/day")

    print("==========================================\n")


if __name__ == "__main__":
    print_report()
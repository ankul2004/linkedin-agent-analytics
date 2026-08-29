from src.risk_model import (
    anomaly_from_z,
    calculate_capacity,
    calculate_model,
    classify_risk,
    safe_z_score,
)


def test_safe_z_score_with_insufficient_data():
    assert safe_z_score(10, [10, 12]) == 0.0


def test_anomaly_from_z_is_bounded():
    assert anomaly_from_z(0) == 0.0
    assert anomaly_from_z(3) == 1.0
    assert anomaly_from_z(10) == 1.0


def test_risk_classification():
    assert classify_risk(0.20) == "LOW"
    assert classify_risk(0.60) == "MEDIUM"
    assert classify_risk(0.90) == "HIGH"


def test_capacity_reduces_with_risk():
    assert calculate_capacity(0.20) == 25
    assert calculate_capacity(0.60) == 15
    assert calculate_capacity(0.90) == 10


def test_model_handles_empty_data():
    result = calculate_model([])

    assert result["sample_size"] == 0
    assert result["confidence"] == "LOW"
    assert result["risk_band"] == "INSUFFICIENT_DATA"
    assert result["recommended_daily_capacity"] == 15


def test_model_with_multiple_observations():
    observations = [
        {
            "date": "2026-08-20",
            "total": 10,
            "acceptance_rate": 0.50,
            "reply_rate": 0.40,
            "ghost_rate": 0.10,
        },
        {
            "date": "2026-08-21",
            "total": 10,
            "acceptance_rate": 0.45,
            "reply_rate": 0.35,
            "ghost_rate": 0.15,
        },
        {
            "date": "2026-08-22",
            "total": 10,
            "acceptance_rate": 0.20,
            "reply_rate": 0.10,
            "ghost_rate": 0.50,
        },
    ]

    result = calculate_model(observations)

    assert result["sample_size"] == 3
    assert "risk_score" in result
    assert 0.0 <= result["risk_score"] <= 1.0
    assert result["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
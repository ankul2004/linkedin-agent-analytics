# Advanced Analytics & Risk Model

## 1. Objective

The risk model identifies potential account-level performance deterioration
using observable lead outcomes available in the current dataset.

The model focuses on three risk signals:

1. Acceptance-rate collapse
2. Reply-rate decay
3. Ghosting increase

The model also produces a risk-adjusted recommended daily capacity.

---

## 2. Available Data Limitation

The current database does not contain direct historical account-level
counters for invites sent, replies, or accepted invitations.

Therefore, the model uses lead status values as observable outcome proxies.

No synthetic historical outcomes are introduced into the production database.

This prevents artificially inflating the statistical evidence.

---

## 3. Statistical Method

The primary statistical method is the standard z-score.

The z-score measures how far the current observation is from the historical
mean in units of standard deviation.

A large absolute z-score indicates that the current observation is unusual
relative to the historical distribution.

A z-score magnitude of 3 or greater is treated as a severe statistical
deviation.

The model requires at least three observation periods before treating
z-score-based anomaly detection as statistically meaningful.

---

## 4. Risk Signals

### Acceptance-Rate Collapse

A decline in acceptance rate compared with its historical baseline increases
risk.

Acceptance-related risk receives a weight of 40%.

### Reply-Rate Decay

A decline in reply rate compared with the historical baseline indicates
potential campaign or account deterioration.

Reply-related risk receives a weight of 30%.

### Ghosting Increase

An increase in leads remaining in new or follow-up-like states is treated as
a proxy for potential ghosting.

Ghosting risk receives a weight of 30%.

---

## 5. Composite Risk Score

The composite risk score uses the following weighting:

| Signal | Weight |
|---|---:|
| Acceptance-rate deterioration | 40% |
| Reply-rate deterioration | 30% |
| Ghosting increase | 30% |

The score ranges from 0 to 1.

Higher scores represent greater observed risk.

---

## 6. Risk Thresholds

| Risk Score | Risk Band |
|---:|---|
| < 0.50 | LOW |
| 0.50 – 0.74 | MEDIUM |
| >= 0.75 | HIGH |

These thresholds are operational decision thresholds rather than claims
of statistical significance.

---

## 7. Confidence Levels

Confidence depends on the amount of historical observation data available.

| Observation Periods | Confidence |
|---:|---|
| < 7 | LOW |
| 7–29 | MEDIUM |
| >= 30 | HIGH |

The current dataset contains only one observation day, so the current model
output is classified as LOW confidence.

The model therefore does not claim that the current LOW risk result is
statistically conclusive.

---

## 8. Daily Capacity Recommendation

The model uses a conservative risk-adjusted capacity strategy.

The standard baseline ceiling is 25 leads/actions per day.

| Risk Band | Recommended Daily Capacity |
|---|---:|
| LOW | 25 |
| MEDIUM | 15 |
| HIGH | 10 |

Higher observed risk reduces recommended daily capacity.

This prevents aggressive activity when account performance indicators
deteriorate.

The recommendation is intended as an operational guardrail and should be
calibrated against real account-level outcomes.

---

## 9. Current Model Result

The current dataset contains:

- Observation days: 1
- Acceptance rate: 0%
- Reply rate: 0%
- Ghost rate: 100%
- Risk score: 0.0000
- Risk band: LOW
- Confidence: LOW
- Recommended capacity: 25/day

Because only one observation period exists, the statistical anomaly
components are not interpreted as meaningful evidence yet.

Additional historical observations are required before reliable anomaly
detection can be established.

---

## 10. Assumptions

1. Lead status is a reasonable proxy for observable engagement outcomes.
2. Historical observations are representative of normal account behaviour.
3. Risk deterioration should result in a more conservative activity limit.
4. The 25/day standard ceiling is treated as the operational baseline.
5. Status values are consistently populated by the ingestion pipeline.

---

## 11. Limitations

The model has the following limitations:

- Direct invite, acceptance, and reply counters are not available in the
  current source schema.
- Account-level historical observations are currently limited.
- One observation day is insufficient for reliable statistical inference.
- Status-based proxies may not perfectly represent real user behaviour.
- The capacity recommendations are operational guardrails, not causal
  estimates.
- Thresholds should be recalibrated when sufficient production history
  becomes available.

---

## 12. Future Improvements

With additional production data, the model should be extended to include:

- Account-level historical baselines
- Rolling 7-day and 30-day metrics
- Direct invite and acceptance counts
- Reply latency
- Reply decay curves
- Ghosting duration
- Confidence intervals
- Account-specific capacity ceilings
- Backtesting against actual outcomes
- Threshold calibration using historical false-positive rates
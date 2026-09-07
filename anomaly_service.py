import numpy as np
from sklearn.ensemble import IsolationForest

def verify_yield_integrity(sensor_history: list, reported_weight_kg: float) -> dict:
    """
    Cross-checks reported harvest against IoT weight-drop curves and anomaly scoring.
    """
    weights = [entry['weight'] if isinstance(entry, dict) and 'weight' in entry else entry.get('weight_kg', 0) for entry in sensor_history]
    if not weights:
        return {
            "flagged": True,
            "reason": "No sensor history available",
            "audit_recommended": True,
            "discrepancy_kg": 0.0
        }

    # Harvest weight drop calculation: max observed pre-harvest weight minus final post-harvest weight
    expected_yield = max(weights) - weights[-1] if len(weights) > 1 else weights[0]
    discrepancy = abs(reported_weight_kg - expected_yield)

    # Statistical / Isolation Forest check when enough historical points exist
    is_outlier = False
    if len(weights) >= 10:
        try:
            arr = np.array(weights).reshape(-1, 1)
            clf = IsolationForest(contamination=0.05, random_state=42)
            preds = clf.fit_predict(arr)
            # Check if last reading before harvest was anomalous
            if preds[-1] == -1:
                is_outlier = True
        except Exception:
            pass

    if discrepancy > 2.5:  # 2.5kg threshold trigger
        return {
            "flagged": True,
            "reason": f"Discrepancy of {round(discrepancy, 2)}kg detected vs sensor baseline",
            "audit_recommended": True,
            "discrepancy_kg": round(discrepancy, 2),
            "expected_yield_kg": round(expected_yield, 2),
            "sensor_outlier": is_outlier
        }

    return {
        "flagged": False,
        "reason": "Passed cross-check",
        "audit_recommended": False,
        "discrepancy_kg": round(discrepancy, 2),
        "expected_yield_kg": round(expected_yield, 2),
        "sensor_outlier": is_outlier
    }


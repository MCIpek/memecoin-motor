from __future__ import annotations

from collections import defaultdict
from statistics import quantiles

from .storage import Storage


def calibrate_x_bands(storage: Storage, horizon: int = 300,
                      minimum_samples: int = 30) -> int:
    groups: dict[tuple[int, str, int, int], list[object]] = defaultdict(list)
    for row in storage.calibration_source(horizon):
        key = (int(row["decision_age_seconds"]), row["decision"],
               int(row["risk_score"]) // 10 * 10,
               int(row["opportunity_score"]) // 10 * 10)
        groups[key].append(row)
    output: list[tuple[object, ...]] = []
    for (age, decision, risk, opportunity), rows in groups.items():
        if len(rows) < minimum_samples:
            continue
        values = sorted(float(row["max_x"]) for row in rows)
        q = quantiles(values, n=4, method="inclusive")
        p90 = quantiles(values, n=10, method="inclusive")[8]
        n = len(rows)
        output.append((horizon, age, decision, risk, opportunity, n,
                       q[0], q[1], q[2], p90,
                       sum(row["hit_1_5x"] for row in rows) / n,
                       sum(row["hit_2x"] for row in rows) / n,
                       sum(row["hit_3x"] for row in rows) / n,
                       sum(row["hit_5x"] for row in rows) / n,
                       sum(float(row["final_x"]) > 1 for row in rows) / n))
    storage.replace_calibrations(horizon, output)
    return len(output)

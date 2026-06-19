from __future__ import annotations

from typing import Dict, Any, List
import math
import pandas as pd


def score_value(value: float, ideal: float, acceptable: float, direction: str) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return float("nan")
    if direction == "higher":
        if value >= ideal:
            return 100.0
        if value >= acceptable:
            return 80.0 + 20.0 * ((value - acceptable) / max(ideal - acceptable, 1e-6))
        return max(0.0, 80.0 * (value / max(acceptable, 1e-6)))
    else:
        if value <= ideal:
            return 100.0
        if value <= acceptable:
            return 80.0 + 20.0 * ((acceptable - value) / max(acceptable - ideal, 1e-6))
        return max(0.0, 80.0 - 8.0 * (value - acceptable))


def build_metric_table(plan_summary: Dict[str, Any], global_metrics: Dict[str, Any], config: Dict[str, Any], rx_gy: float) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    goals = config.get("generic_goals", {})
    g = global_metrics.get("Global Dose Grid", {}) if global_metrics else {}

    total_mu = float(plan_summary.get("Total MU") or 0)
    mu_per_gy = total_mu / rx_gy if rx_gy else None

    candidates = [
        ("PTV D0.03cc %Rx", (g.get("Dmax Gy", 0) / rx_gy * 100.0) if rx_gy else None, "Target Quality"),
        ("PTV V105%", g.get("Global V105Rx %"), "Target Quality"),
        ("MU per Gy", mu_per_gy, "Delivery Efficiency"),
    ]

    for metric, value, domain in candidates:
        goal = goals.get(metric)
        if not goal:
            continue
        score = score_value(value, goal["ideal"], goal["acceptable"], goal["direction"])
        rows.append({
            "Domain": domain,
            "Metric": metric,
            "Value": None if value is None else round(float(value), 3),
            "Ideal": goal["ideal"],
            "Acceptable": goal["acceptable"],
            "Direction": goal["direction"],
            "Score": None if math.isnan(score) else round(score, 1),
            "Status": "Calculated" if value is not None else "Needs DVH"
        })

    # Placeholder rows for clinically important DVH metrics.
    placeholder_metrics = [
        ("Target Quality", "PTV V100%"),
        ("Critical Serial OAR", "Cord D0.03cc Gy"),
        ("Critical Serial OAR", "Brainstem D0.03cc Gy"),
        ("Critical Serial OAR", "Optic Dmax Gy"),
        ("Functional/QOL OAR", "Parotid Mean Gy"),
        ("Functional/QOL OAR", "Oral Cavity Mean Gy"),
        ("Functional/QOL OAR", "Larynx Mean Gy"),
        ("Functional/QOL OAR", "Esophagus Mean Gy"),
        ("Functional/QOL OAR", "Mandible Dmax Gy"),
    ]
    for domain, metric in placeholder_metrics:
        goal = goals.get(metric, {})
        rows.append({
            "Domain": domain,
            "Metric": metric,
            "Value": None,
            "Ideal": goal.get("ideal"),
            "Acceptable": goal.get("acceptable"),
            "Direction": goal.get("direction"),
            "Score": None,
            "Status": "Requires structure DVH rasterization"
        })
    return pd.DataFrame(rows)


def domain_scores(metric_df: pd.DataFrame, config: Dict[str, Any], completeness_score: float) -> pd.DataFrame:
    domains = config["domain_weights"]
    rows = []
    for domain, weight in domains.items():
        if domain == "Clinical Completeness":
            score = completeness_score
        elif domain == "Dose Falloff":
            # placeholder until CI/GI/body-spill engine is implemented
            score = 75.0
        else:
            subset = metric_df[(metric_df["Domain"] == domain) & (metric_df["Score"].notna())]
            score = float(subset["Score"].mean()) if len(subset) else 50.0
        rows.append({"Domain": domain, "Weight": weight, "Score": round(score, 1), "Weighted Points": round(score * weight, 2)})
    return pd.DataFrame(rows)


def final_grade(domain_df: pd.DataFrame, config: Dict[str, Any]) -> tuple[float, str]:
    score = round(float(domain_df["Weighted Points"].sum()), 1)
    for grade, threshold in config["grade_thresholds"].items():
        if score >= threshold:
            return score, grade
    return score, "Replan Review"

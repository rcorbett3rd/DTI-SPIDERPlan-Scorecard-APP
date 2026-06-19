from __future__ import annotations

import pandas as pd


TARGET_KEYWORDS = [
    "PTV", "CTV", "GTV", "ITV"
]

CRITICAL_OAR_KEYWORDS = [
    "SpinalCord", "Cord", "Cord_PRV",
    "Brainstem", "Brainstem_PRV",
    "OpticChiasm", "Chiasm",
    "OpticNrv", "OpticNerve", "Optic_Nerve"
]

QOL_OAR_KEYWORDS = [
    "Parotid", "OralCavity", "Oral_Cavity",
    "Larynx", "Esophagus", "Mandible",
    "Cochlea"
]

PRV_KEYWORDS = [
    "PRV"
]


def _name_list(structures):
    if not structures:
        return []
    names = []
    for s in structures:
        if isinstance(s, dict):
            name = s.get("Name") or s.get("Structure") or s.get("ROI Name") or ""
        else:
            name = str(s)
        if name:
            names.append(name)
    return names


def _contains_any(names, keywords):
    found = []
    for name in names:
        for kw in keywords:
            if kw.lower() in name.lower():
                found.append(name)
                break
    return sorted(set(found))


def build_readiness_score(grouped, plan_summary, structures):
    """
    Web-safe SPIDER readiness score.
    Does not load RD pixel dose grid or calculate DVH.
    """

    names = _name_list(structures)

    rp_present = bool(grouped.get("RP"))
    rs_present = bool(grouped.get("RS"))
    rd_present = bool(grouped.get("RD"))

    rx_detected = bool(plan_summary.get("Rx Dose Gy"))
    fx_detected = bool(plan_summary.get("Fractions"))
    beams = plan_summary.get("Beams") or []
    beams_detected = len(beams) > 0

    targets = _contains_any(names, TARGET_KEYWORDS)
    critical_oars = _contains_any(names, CRITICAL_OAR_KEYWORDS)
    qol_oars = _contains_any(names, QOL_OAR_KEYWORDS)
    prvs = _contains_any(names, PRV_KEYWORDS)

    # Domain scoring
    dataset_score = 0
    if rp_present:
        dataset_score += 35
    if rs_present:
        dataset_score += 35
    if rd_present:
        dataset_score += 30

    rx_score = 0
    if rx_detected:
        rx_score += 50
    if fx_detected:
        rx_score += 30
    if beams_detected:
        rx_score += 20

    target_score = min(100, len(targets) * 35)

    critical_oar_score = min(100, len(critical_oars) * 12.5)

    qol_score = min(100, len(qol_oars) * 15)

    prv_score = min(100, len(prvs) * 25)

    delivery_score = 100 if beams_detected else 40

    domains = [
        {
            "Domain": "Dataset Completeness",
            "Score": round(dataset_score, 1),
            "Weight": 0.20,
            "Details": f"RP: {rp_present}, RS: {rs_present}, RD: {rd_present}",
        },
        {
            "Domain": "Prescription Integrity",
            "Score": round(rx_score, 1),
            "Weight": 0.20,
            "Details": f"Rx detected: {rx_detected}, Fractions detected: {fx_detected}",
        },
        {
            "Domain": "Target Readiness",
            "Score": round(target_score, 1),
            "Weight": 0.20,
            "Details": ", ".join(targets) if targets else "No target structures detected",
        },
        {
            "Domain": "Critical OAR Readiness",
            "Score": round(critical_oar_score, 1),
            "Weight": 0.20,
            "Details": ", ".join(critical_oars) if critical_oars else "No critical OARs detected",
        },
        {
            "Domain": "QOL OAR / PRV Readiness",
            "Score": round((qol_score * 0.6) + (prv_score * 0.4), 1),
            "Weight": 0.10,
            "Details": f"QOL OARs: {len(qol_oars)}, PRVs: {len(prvs)}",
        },
        {
            "Domain": "Delivery Metadata",
            "Score": round(delivery_score, 1),
            "Weight": 0.10,
            "Details": f"Beams detected: {len(beams)}",
        },
    ]

    domain_df = pd.DataFrame(domains)
    final_score = round((domain_df["Score"] * domain_df["Weight"]).sum(), 1)

    if final_score >= 90:
        grade = "Ready for Full DVH Review"
    elif final_score >= 80:
        grade = "Mostly Ready"
    elif final_score >= 70:
        grade = "Needs Structure / Metadata Review"
    else:
        grade = "Not Ready"

    findings = {
        "Targets Detected": targets,
        "Critical OARs Detected": critical_oars,
        "QOL OARs Detected": qol_oars,
        "PRVs Detected": prvs,
        "Final Readiness Score": final_score,
        "Readiness Grade": grade,
    }

    return domain_df, findings

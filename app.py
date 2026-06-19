from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from dicom_parser import (
    save_uploaded_files,
    load_dicoms,
    classify_rt_files,
    extract_plan_summary,
    extract_structures,
)
from scorecard_engine import build_metric_table, domain_scores, final_grade
from spider_chart import make_spider_chart
from readiness_score import build_readiness_score

st.set_page_config(page_title="DTI SPIDERPlan Scorecard™", layout="wide")


@st.cache_data
def load_config():
    with open(Path(__file__).parent / "scoring_config.json", "r") as f:
        return json.load(f)


config = load_config()

st.title("DTI SPIDERPlan Scorecard™")
st.caption("Web Readiness Mode for Eclipse/ARIA DICOM RT Plan exports")

with st.expander("Clinical / security disclaimer", expanded=False):
    st.warning(
        "Prototype only. Not for clinical decision-making. Do not upload identifiable PHI "
        "to public or non-HIPAA-compliant systems. This Streamlit version uses Web Readiness Mode "
        "and does not perform full RD dose-grid DVH calculation."
    )

processing_mode = st.radio(
    "Processing mode",
    [
        "Web Readiness Mode - no RD dose-grid DVH calculation",
        "Full DVH Mode - disabled on Streamlit Community Cloud",
    ],
    index=0,
)

uploaded = st.file_uploader(
    "Upload Eclipse/ARIA DICOM RT export files: RP + RS preferred, RD optional",
    type=["dcm", "dicom", "DCM"],
    accept_multiple_files=True,
)

manual_rx = st.number_input(
    "Prescription dose for scoring fallback (Gy)",
    min_value=0.0,
    max_value=100.0,
    value=70.0,
    step=0.1,
)

if uploaded:
    try:
        paths = save_uploaded_files(uploaded)
        datasets = load_dicoms(paths)
        grouped = classify_rt_files(datasets)

        rp = grouped["RP"][0] if grouped["RP"] else None
        rs = grouped["RS"][0] if grouped["RS"] else None
        rd = grouped["RD"][0] if grouped["RD"] else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("RT Plan Files", len(grouped["RP"]))
        c2.metric("RT Structure Files", len(grouped["RS"]))
        c3.metric("RT Dose Files", len(grouped["RD"]))
        c4.metric("CT Slices", len(grouped["CT"]))

        plan_summary = extract_plan_summary(rp)
        structures = extract_structures(rs)
        rx_gy = float(plan_summary.get("Rx Dose Gy") or manual_rx or 0)

        st.subheader("Plan Summary")
        summary_display = {k: v for k, v in plan_summary.items() if k != "Beams"}
        st.dataframe(pd.DataFrame([summary_display]), use_container_width=True)

        if plan_summary.get("Beams"):
            st.subheader("Beam / MU Summary")
            st.dataframe(pd.DataFrame(plan_summary["Beams"]), use_container_width=True)

        st.subheader("Structures Detected")
        if structures:
            st.dataframe(pd.DataFrame(structures), use_container_width=True)
        else:
            st.info("No RT Structure Set detected.")

        st.subheader("Pre-DVH SPIDER Readiness Score")

        readiness_df, readiness_findings = build_readiness_score(
            grouped,
            plan_summary,
            structures,
        )

        readiness_score = readiness_findings["Final Readiness Score"]
        readiness_grade = readiness_findings["Readiness Grade"]

        r1, r2 = st.columns(2)
        r1.metric("Pre-DVH SPIDER Readiness Score", readiness_score)
        r2.metric("Readiness Grade", readiness_grade)

        st.dataframe(readiness_df, use_container_width=True)

        st.subheader("Readiness Findings")
        st.json(readiness_findings)

        st.subheader("DTI-SPIDER Readiness Radar")
        st.plotly_chart(make_spider_chart(readiness_df), use_container_width=True)

        st.subheader("DVH / Dose Metrics")

        metrics = {}

        if processing_mode == "Web Readiness Mode - no RD dose-grid DVH calculation":
            st.warning(
                "Web Readiness Mode is active. RD dose-grid DVH calculation is disabled "
                "for Streamlit Community Cloud stability. This score evaluates dataset, "
                "structure, prescription, and delivery readiness before full DVH scoring."
            )
        else:
            st.error(
                "Full DVH Mode is disabled in the Streamlit Community Cloud version because "
                "large RD dose files may exceed free-hosting memory limits. Use the local/full "
                "version for validated DVH calculations."
            )

        st.subheader("ProKnow-Type Metric Scorecard Placeholder")
        metric_df = build_metric_table(plan_summary, metrics, config, rx_gy)
        st.dataframe(metric_df, use_container_width=True)

        st.subheader("Legacy Completeness-Based SPIDER Score")
        completeness = 100.0
        if rp is None:
            completeness -= 30
        if rs is None:
            completeness -= 25
        if rd is None:
            completeness -= 25
        if not structures:
            completeness -= 10
        completeness = max(0.0, completeness)

        domain_df = domain_scores(metric_df, config, completeness)
        score, grade = final_grade(domain_df, config)

        a, b = st.columns([1, 2])
        with a:
            st.metric("Legacy SPIDER Score", score)
            st.metric("Legacy Grade", grade)
            st.dataframe(domain_df, use_container_width=True)
        with b:
            st.plotly_chart(make_spider_chart(domain_df), use_container_width=True)

        st.subheader("Export")

        readiness_csv = readiness_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Readiness Scorecard CSV",
            readiness_csv,
            "dti_spider_readiness_scorecard.csv",
            "text/csv",
        )

        metric_csv = metric_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Metric Scorecard CSV",
            metric_csv,
            "dti_spider_metric_scorecard.csv",
            "text/csv",
        )

        domain_csv = domain_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Legacy SPIDER Domain CSV",
            domain_csv,
            "dti_spider_domain_scorecard.csv",
            "text/csv",
        )

    except Exception as e:
        st.error("The app crashed while processing the uploaded DICOM files.")
        st.exception(e)

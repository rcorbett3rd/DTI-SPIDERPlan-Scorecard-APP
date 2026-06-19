import streamlit as st

st.set_page_config(
    page_title="DTI SPIDERPlan AI",
    page_icon="🕷️",
    layout="wide"
)

st.title("DTI SPIDERPlan AI™")
st.subheader("Radiation Plan Scorecard Prototype")

st.warning(
    "Upload only de-identified/anonymized DICOM RT files. "
    "This prototype is not for clinical treatment decisions."
)

uploaded_files = st.file_uploader(
    "Upload RP, RS, and RD DICOM files",
    type=["dcm"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} file(s) uploaded.")

    for file in uploaded_files:
        st.write(f"Uploaded: {file.name}")

    st.divider()

    st.header("Prototype Scorecard Output")

    st.metric("Overall DTI-SPIDER Score", "Pending DVH Engine")
    st.metric("Plan Grade", "Prototype Mode")

    st.info(
        "The web app is now running successfully. "
        "Next step is reconnecting the DICOM parser and scoring engine."
    )
else:
    st.info("Upload de-identified RP, RS, and RD files to begin.")

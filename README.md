# DTI SPIDERPlan AI™ — Streamlit Web Prototype

This is a Streamlit Community Cloud-ready prototype for uploading de-identified Eclipse/ARIA DICOM RT export files and generating a ProKnow-style metric table plus DTI-SPIDER domain scorecard.

## Files to upload in the app

- RP DICOM file: RT Plan
- RS DICOM file: RT Structure Set
- RD DICOM file: RT Dose
- Optional CT series for future geometry expansion

## Important PHI warning

Streamlit Community Cloud is for demonstration and development only. Do not upload identifiable patient data or PHI. Use only de-identified/anonymized test plans.

## Deploy on Streamlit Community Cloud

1. Create or sign into a GitHub account.
2. Create a new GitHub repository, for example: `dti-spiderplan-ai`.
3. Upload all files in this folder to that repository.
4. Go to Streamlit Community Cloud: `https://share.streamlit.io`.
5. Choose **Create app**.
6. Select your GitHub repo and branch.
7. Set the main file path to: `streamlit_app.py`.
8. Click **Deploy**.

Your app will get a web link such as:

`https://your-app-name.streamlit.app`

## Current MVP limitations

- Prototype only; not for clinical decision-making.
- Structure-specific DVH scoring requires validation/commissioning before clinical use.
- Public/free cloud hosting is not HIPAA-compliant.
- Current scoring framework should be treated as research/demo software until formally validated.


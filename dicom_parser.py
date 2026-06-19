from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import pydicom


def save_uploaded_files(uploaded_files) -> List[Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="dti_spider_"))
    paths = []
    for f in uploaded_files:
        path = temp_dir / f.name
        path.write_bytes(f.getvalue())
        paths.append(path)
    return paths


def load_dicoms(paths: List[Path]) -> List[pydicom.Dataset]:
    datasets = []
    for p in paths:
        try:
            ds = pydicom.dcmread(str(p), force=True)
            ds._source_path = str(p)
            datasets.append(ds)
        except Exception:
            continue
    return datasets


def classify_rt_files(datasets: List[pydicom.Dataset]) -> Dict[str, List[pydicom.Dataset]]:
    out = {"RP": [], "RS": [], "RD": [], "CT": [], "OTHER": []}
    for ds in datasets:
        modality = getattr(ds, "Modality", "")
        sop = getattr(ds, "SOPClassUID", "")
        if modality == "RTPLAN":
            out["RP"].append(ds)
        elif modality == "RTSTRUCT":
            out["RS"].append(ds)
        elif modality == "RTDOSE":
            out["RD"].append(ds)
        elif modality == "CT":
            out["CT"].append(ds)
        else:
            out["OTHER"].append(ds)
    return out


def extract_plan_summary(rp: Optional[pydicom.Dataset]) -> Dict[str, Any]:
    if rp is None:
        return {}
    beams = []
    beam_metersets = {}
    try:
        for fg in getattr(rp, "FractionGroupSequence", []):
            for rb in getattr(fg, "ReferencedBeamSequence", []):
                beam_metersets[int(rb.ReferencedBeamNumber)] = float(getattr(rb, "BeamMeterset", 0))
    except Exception:
        pass

    total_mu = 0.0
    for b in getattr(rp, "BeamSequence", []):
        num = int(getattr(b, "BeamNumber", 0))
        mu = float(beam_metersets.get(num, 0))
        total_mu += mu
        beams.append({
            "Beam Number": num,
            "Beam Name": getattr(b, "BeamName", ""),
            "Machine": getattr(b, "TreatmentMachineName", ""),
            "Radiation Type": getattr(b, "RadiationType", ""),
            "Energy": getattr(getattr(b, "ControlPointSequence", [None])[0], "NominalBeamEnergy", None),
            "MU": mu,
        })

    rx_dose = None
    fractions = None
    try:
        fg = rp.FractionGroupSequence[0]
        fractions = int(getattr(fg, "NumberOfFractionsPlanned", 0)) or None
    except Exception:
        pass
    # Prescription extraction varies by export; fallback to user input in app.
    try:
        rx_dose = float(rp.DoseReferenceSequence[0].TargetPrescriptionDose)
    except Exception:
        rx_dose = None

    return {
        "Patient ID": getattr(rp, "PatientID", ""),
        "Plan Name": getattr(rp, "RTPlanName", ""),
        "Plan Label": getattr(rp, "RTPlanLabel", ""),
        "Plan Date": getattr(rp, "RTPlanDate", ""),
        "Fractions": fractions,
        "Rx Dose Gy": rx_dose,
        "Total MU": round(total_mu, 2),
        "Beam Count": len(beams),
        "Beams": beams,
    }


def extract_structures(rs: Optional[pydicom.Dataset]) -> List[Dict[str, Any]]:
    if rs is None:
        return []
    roi_names = {}
    for roi in getattr(rs, "StructureSetROISequence", []):
        roi_names[int(roi.ROINumber)] = getattr(roi, "ROIName", "")
    structures = []
    for rc in getattr(rs, "ROIContourSequence", []):
        num = int(getattr(rc, "ReferencedROINumber", -1))
        contour_count = len(getattr(rc, "ContourSequence", []))
        structures.append({"ROI Number": num, "Name": roi_names.get(num, ""), "Contours": contour_count})
    return sorted(structures, key=lambda x: x["ROI Number"])

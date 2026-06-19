from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pydicom


def get_dose_grid(rd: pydicom.Dataset) -> Tuple[np.ndarray, Dict[str, float]]:
    arr = rd.pixel_array.astype(float) * float(getattr(rd, "DoseGridScaling", 1.0))
    # convert to Gy when DICOM dose unit is Gy; most RTDOSE is Gy after scaling.
    spacing = getattr(rd, "PixelSpacing", [1.0, 1.0])
    dzs = getattr(rd, "GridFrameOffsetVector", None)
    dz = float(abs(dzs[1] - dzs[0])) if dzs is not None and len(dzs) > 1 else float(getattr(rd, "SliceThickness", 1.0))
    meta = {"dx_mm": float(spacing[1]), "dy_mm": float(spacing[0]), "dz_mm": dz}
    return arr, meta


def _structure_names(rs: pydicom.Dataset) -> Dict[int, str]:
    return {int(roi.ROINumber): str(roi.ROIName) for roi in getattr(rs, "StructureSetROISequence", [])}


def find_structure_by_alias(structures: List[Dict[str, Any]], aliases: List[str]) -> Optional[str]:
    normalized = {s["Name"].lower().replace(" ", "").replace("-", "_"): s["Name"] for s in structures}
    for alias in aliases:
        key = alias.lower().replace(" ", "").replace("-", "_")
        if key in normalized:
            return normalized[key]
    for s in structures:
        n = s["Name"].lower()
        for alias in aliases:
            if alias.lower() in n:
                return s["Name"]
    return None


def approximate_metrics(rd: Optional[pydicom.Dataset], rs: Optional[pydicom.Dataset], structures: List[Dict[str, Any]], config: Dict[str, Any], rx_gy: float) -> Dict[str, Dict[str, float]]:
    """
    MVP placeholder: true contour-to-dose DVH calculation requires rasterizing contours into the dose grid.
    This function returns a safe structure-aware scaffold and, when dose exists, global dose statistics.
    Replace with production-grade DVH rasterization before clinical use.
    """
    metrics: Dict[str, Dict[str, float]] = {}
    if rd is None:
        return metrics
    dose, meta = get_dose_grid(rd)
    max_dose = float(np.nanmax(dose))
    mean_body = float(np.nanmean(dose[dose > 0])) if np.any(dose > 0) else 0.0
    v105_proxy = float(np.mean(dose >= 1.05 * rx_gy) * 100.0) if rx_gy else 0.0
    body_v50 = float(np.mean(dose >= 50.0) * 100.0)
    body_v30 = float(np.mean(dose >= 30.0) * 100.0)

    metrics["Global Dose Grid"] = {
        "Dmax Gy": max_dose,
        "Mean nonzero Gy": mean_body,
        "Global V105Rx %": v105_proxy,
        "Global V50Gy %": body_v50,
        "Global V30Gy %": body_v30,
    }

    aliases = config.get("structure_aliases", {})
    for key, alias_list in aliases.items():
        name = find_structure_by_alias(structures, alias_list)
        if not name:
            continue
        # Placeholder values intentionally not faked. We expose N/A for true structure DVH.
        metrics[name] = {"DVH Status": np.nan}
    return metrics


def dvh_note() -> str:
    return (
        "This MVP detects RT structures and RT dose but does not yet perform production-grade "
        "contour rasterization into the dose grid. Reported global dose-grid metrics are real; "
        "structure-specific DVH values are placeholders until the rasterizer is connected."
    )

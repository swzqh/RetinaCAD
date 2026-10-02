"""Export a local, patient-data-minimized research report."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .model_service import PredictionResult


FIELD_LABELS = {
    "Age": ("Age", "years"),
    "Male": ("Sex", "0=female; 1=male"),
    "HTN": ("Hypertension", "0=no; 1=yes"),
    "DM": ("Diabetes mellitus", "0=no; 1=yes"),
    "Smoke": ("Smoking", "0=no; 1=yes"),
    "LVEF_pct": ("Left ventricular ejection fraction", "%"),
    "LVMI_g_m2": ("Left ventricular mass index", "g/m²"),
    "RWT": ("Relative wall thickness", "unitless"),
    "LVDdI_mm_m2": ("Indexed LV end-diastolic diameter", "mm/m²"),
    "L2ParaFovea": ("Deep parafoveal vessel density", "device output"),
    "L2PeriFovea": ("Deep perifoveal vessel density", "device output"),
    "VD": ("Retinal arterial vessel density", "pipeline output"),
    "Ratio": ("Artery-to-vein median diameter ratio", "unitless"),
}


def export_report(
    directory: str | Path,
    result: PredictionResult,
    case_code: str,
    image_name: str | None,
    image_qc: Mapping[str, Any] | None,
    phenotype_source: str | None = None,
) -> tuple[Path, Path]:
    """Write matching HTML and JSON reports and return their paths."""
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_case = "".join(ch for ch in case_code if ch.isalnum() or ch in "-_")[:40]
    stem = f"RetinaCAD_{safe_case or 'report'}_{timestamp}"
    json_path = output_dir / f"{stem}.json"
    html_path = output_dir / f"{stem}.html"

    payload = {
        "report_version": "1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "case_code": case_code or None,
        "image_filename": image_name,
        "model_id": result.model_id,
        "outcome_definition": result.outcome_definition,
        "probability": result.probability,
        "linear_predictor": result.linear_predictor,
        "inputs": result.values,
        "imputed_fields": list(result.imputed_fields),
        "image_qc": dict(image_qc) if image_qc else None,
        "phenotype_source": phenotype_source,
        "notice": "For research reference only. This tool does not replace coronary angiography, clinical judgment, or future-event risk assessment.",
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    rows = []
    for key, value in result.values.items():
        label, unit = FIELD_LABELS[key]
        display = f"{value:g}"
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{html.escape(display)}</td>"
            f"<td>{html.escape(unit)}</td>"
            "</tr>"
        )
    qc_rows = ""
    if image_qc:
        qc_rows = "".join(
            f"<tr><td>{html.escape(str(key))}</td><td colspan='2'>{html.escape(str(value))}</td></tr>"
            for key, value in image_qc.items()
        )

    report_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RetinaCAD Research Report</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; color: #1d1d1f; background: #f5f5f7; }}
.page {{ max-width: 820px; margin: 32px auto; background: #fff; border: 1px solid #e5e5e8; border-radius: 8px; overflow: hidden; }}
header {{ padding: 26px 32px; background: #fff; color: #1d1d1f; border-bottom: 1px solid #dadadd; }}
header h1 {{ margin: 0 0 6px; font-size: 22px; }}
header p {{ margin: 0; color: #6e6e73; font-size: 13px; }}
main {{ padding: 28px 32px 36px; }}
.result {{ display: flex; justify-content: space-between; align-items: end; padding-bottom: 22px; border-bottom: 1px solid #dadadd; }}
.probability {{ font-size: 42px; font-weight: 700; color: #33915b; }}
.meta {{ color: #6e6e73; font-size: 13px; text-align: right; }}
h2 {{ margin: 26px 0 10px; font-size: 16px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ padding: 9px 10px; border-bottom: 1px solid #ececef; text-align: left; }}
th {{ color: #6e6e73; font-weight: 600; background: #f7f7f8; }}
.notice {{ margin-top: 26px; padding: 14px 16px; background: #fff7e0; color: #8a5a00; border-left: 4px solid #8a5a00; font-size: 13px; }}
footer {{ padding: 14px 32px; border-top: 1px solid #dadadd; color: #6e6e73; font-size: 12px; }}
@media print {{ body {{ background: #fff; }} .page {{ margin: 0; border: 0; }} }}
</style>
</head>
<body><div class="page">
<header><h1>Retinal–Coronary Reference Assessment</h1><p>RetinaCAD · Local research tool</p></header>
<main>
<div class="result"><div><div style="color:#6e6e73;font-size:13px">CAD reference probability</div><div class="probability">{result.probability * 100:.1f}%</div></div>
<div class="meta">Case code: {html.escape(case_code or 'Not provided')}<br>Image: {html.escape(image_name or 'Not loaded')}<br>Phenotypes: {html.escape(phenotype_source or 'Not recorded')}<br>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div></div>
<h2>Model inputs</h2><table><thead><tr><th>Variable</th><th>Value</th><th>Unit / coding</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
{f'<h2>Image technical check</h2><table><tbody>{qc_rows}</tbody></table>' if qc_rows else ''}
<div class="notice">For research reference only. This tool does not replace coronary angiography, clinical judgment, or future-event risk assessment.</div>
</main><footer>Model: {html.escape(result.model_id)} · Results apply only to the study definition and data range</footer>
</div></body></html>"""
    html_path.write_text(report_html, encoding="utf-8")
    return html_path, json_path

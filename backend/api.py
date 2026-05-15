"""
backend/api.py
"""

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from pydantic import BaseModel
import tempfile, os, math, json, re, io
import numpy as np
import pandas as pd

from .parser      import parse_fca_file
from .aligner     import align_tabs, align_rows
from .calculator  import compute_movements
from .ccr         import (check_completeness, check_consistency,
                          check_reasonableness, check_zero_emergence,
                          check_working_file)
from .commentary  import generate_commentary
from .exporter    import build_excel
from .ca1_parser  import extract_hkrbc_data
from .summary     import generate_executive_summary, build_summary_pdf

app = FastAPI(title="Smart Regulatory Reviewer API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

FCA_MANDATORY_TABS = [
    "F.1 EBS","F.1B EBS vs Fin Stat","F.2 EBS by LT Portfolios","F.3 AOM",
    "F.A.1 Property","F.A.2 Equity","F.A.3 Fixed income","F.A.3A Credit Rating",
    "F.A.3B Qualitative Assessment","F.A.4 Derivatives","F.A.5 Cash and Deposits",
    "F.A.6 Port Inv","F.A.6A Port Inv of Port Inv","F.A.7 Related Parties",
    "F.A.7A RP Transaction","F.A.8 Repo","F.A.9 Structured Products",
    "F.L.1 Financial Liabilities","F.LT.1.1 LT CE Summary","F.LT.1.2 LT CE Supp",
    "F.LT.2 LT MOCE","F.LT.3 TVOG","F.LT.4_ClaimLiab_LT_A&H",
    "F.LT.5_PL_LT_A&H","F.LT.5A_PL_Recog_LT_A&H","F.LT.5B_PL_notRecog_LT_A&H",
    "F.LT.6 Par Business","F.LT.MA.X.1 Portfolio Info","F.LT.MA.X.2 MA Asset Data",
    "F.LT.MA.X.3 MA Liability Data","F.LT.MA.X.4 MA Cashflow",
    "F.LT.MA.X.5 MA Result","F.LT.MA.X.6 MA Yield Curve",
    "CA.1 CA Summary","CA.R.1 CB composition","CA.R.2 Features of instruments",
    "CA.P.1.A PCA Summary NetFDB","CA.P.2 PCA Summary GrossFDB","CA.P.3 LAC FDB",
    "CA.P.4 Correlation Matrices","CA.P.M.1 EBS Base","CA.P.M.2 EBS IRUp",
    "CA.P.M.3 EBS IRDown","CA.P.M.4 EBS CS","CA.P.M.5 EBS EQ",
    "CA.P.M.6 EBS PR","CA.P.M.7 CCY","CA.P.LT.1 LOB","CA.P.LT.2 HRG",
    "CA.P.LT.5_P&R_LTB_A&H","CA.P.D Default","CA.P.O Op",
]


class _SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Series):
            return obj.iloc[0] if len(obj) == 1 else obj.tolist()
        if obj is pd.NA or obj is pd.NaT: return None
        if isinstance(obj, np.integer):   return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            return None if (math.isnan(v) or math.isinf(v)) else v
        if isinstance(obj, np.bool_):     return bool(obj)
        if isinstance(obj, np.ndarray):   return obj.tolist()
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return super().default(obj)


def _safe_response(payload: dict) -> Response:
    raw = json.dumps(payload, cls=_SafeEncoder)
    raw = re.sub(r'\bNaN\b', 'null', raw)
    raw = re.sub(r'\bInfinity\b', 'null', raw)
    raw = re.sub(r'\b-Infinity\b', 'null', raw)
    return Response(content=raw.encode("utf-8"), media_type="application/json")


def _run_pipeline(cy_path: str, py_path: str):
    cy_data = parse_fca_file(cy_path)
    py_data = parse_fca_file(py_path)
    tab_alignment = align_tabs(cy_data, py_data)
    all_results, all_ccr = [], []

    for cy_tab, info in tab_alignment.items():
        if info["status"] == "unmatched":
            continue
        py_tab    = info["py_tab"]
        cy_df     = cy_data[cy_tab]
        py_df     = py_data[py_tab]
        aligned   = align_rows(cy_df, py_df)
        movements = compute_movements(aligned)

        all_ccr += check_consistency(movements, cy_tab)
        all_ccr += check_reasonableness(movements, cy_tab)
        all_ccr += check_zero_emergence(movements, cy_tab)   # NEW

        all_results.append({
            "tab":  cy_tab,
            "data": movements.to_dict(orient="records"),
        })

    all_ccr += check_completeness(cy_data, FCA_MANDATORY_TABS)
    return tab_alignment, all_results, all_ccr, cy_data


@app.get("/health")
def health():
    return Response(content='{"status":"ok"}', media_type="application/json")


@app.post("/compare")
async def compare(cy_file: UploadFile = File(...), py_file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await cy_file.read()); cy_path = f.name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await py_file.read()); py_path = f.name
    try:
        tab_alignment, all_results, all_ccr, _ = _run_pipeline(cy_path, py_path)
        high_priority = [
            row for r in all_results for row in r["data"]
            if row.get("priority") == "High" and row.get("pct_change") is not None
        ]
        commented = generate_commentary(high_priority)
        try:
            hkrbc = extract_hkrbc_data(cy_path, py_path)
        except Exception as e:
            hkrbc = {"cy": {}, "py": {}, "ai_commentary": f"[HKRBC unavailable: {e}]"}

        return _safe_response({
            "tab_alignment": tab_alignment,
            "results":       all_results,
            "ccr_findings":  all_ccr,
            "commentary":    commented,
            "hkrbc":         hkrbc,
        })
    finally:
        try: os.unlink(cy_path); os.unlink(py_path)
        except: pass


@app.post("/check_working_file")
async def check_wf(
    cy_file:      UploadFile = File(...),
    working_file: UploadFile = File(...),
):
    """Cross-check FCA return values against uploaded working papers."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await cy_file.read()); cy_path = f.name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await working_file.read()); wf_path = f.name
    try:
        cy_data = parse_fca_file(cy_path)
        findings = check_working_file(cy_data, wf_path)
        return _safe_response({"findings": findings})
    finally:
        try: os.unlink(cy_path); os.unlink(wf_path)
        except: pass


class SummaryRequest(BaseModel):
    hkrbc:        dict
    results:      list
    ccr_findings: list


@app.post("/executive_summary")
async def executive_summary(req: SummaryRequest):
    """Generate AI executive summary memo."""
    memo = generate_executive_summary(req.hkrbc, req.results, req.ccr_findings)
    return _safe_response(memo)


@app.post("/executive_summary_pdf")
async def executive_summary_pdf(req: SummaryRequest):
    """Generate AI executive summary and return as PDF."""
    memo = generate_executive_summary(req.hkrbc, req.results, req.ccr_findings)
    pdf_bytes = build_summary_pdf(memo)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=FCA_Review_Memo.pdf"},
    )


class ExportRequest(BaseModel):
    results:    list
    ai_remarks: bool = True


@app.post("/export_results")
async def export_results(req: ExportRequest):
    xlsx_bytes = build_excel(req.results, use_ai_remarks=req.ai_remarks)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=FCA_Review_Report.xlsx"},
    )
"""
backend/api.py
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from pydantic import BaseModel
import tempfile, os, math, json, re, io, time
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
from .summary     import generate_executive_summary, build_summary_pdf, render_memo_to_pdf

app = FastAPI(title="Smart Regulatory Reviewer API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

FCA_MANDATORY_TABS = [
    "F.1 EBS",
    "F.1B EBS vs Fin Stat",
    "F.2 EBS by LT Portfolios",
    "F.3 AOM",
    "F.A.4 Derivatives",
    "F.A.7 Related Parties",
    "F.L.1 Financial Liabilities",
    "F.LT.1.1 LT CE Summary",
    "F.LT.1.2 LT CE Supp",
    "F.LT.2 LT MOCE",
    "F.LT.3 TVOG",
    "F.LT.6 Par Business",
    "F.LT.MA.X.1 Portfolio Info",
    "F.LT.MA.X.2 MA Asset Data",
    "F.LT.MA.X.3 MA Liability Data",
    "F.LT.MA.X.4 MA Cashflow",
    "F.LT.MA.X.5 MA Result",
    "F.LT.MA.X.6 MA Yield Curve",
    "CA.1 CA Summary",
    "CA.R.1 CB composition",
    "CA.P.1.A PCA Summary NetFDB",
    "CA.P.2 PCA Summary GrossFDB",
    "CA.P.3 LAC FDB",
    "CA.P.4 Correlation Matrices",
    "CA.P.M.1 EBS Base",
    "CA.P.M.2 EBS IRUp",
    "CA.P.M.3 EBS IRDown",
    "CA.P.M.4 EBS CS",
    "CA.P.M.5 EBS EQ",
    "CA.P.M.6 EBS PR",
    "CA.P.M.7 CCY",
    "CA.P.LT.1 LOB",
    "CA.P.LT.2 HRG",
    "CA.P.D Default",
    "CA.P.O Op",
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


def _sse(msg: str, pct: int) -> str:
    """Format a Server-Sent Events message."""
    data = json.dumps({"msg": msg, "pct": pct})
    return f"data: {data}\n\n"


def _is_mandatory(tab_name: str) -> bool:
    """
    Returns True if tab_name fuzzy-matches any tab in FCA_MANDATORY_TABS
    (score >= 85). This lets minor spacing/capitalisation differences through
    while still filtering out DropDownList, cover sheets, etc.
    """
    from rapidfuzz import fuzz, process
    result = process.extractOne(tab_name, FCA_MANDATORY_TABS,
                                scorer=fuzz.token_sort_ratio)
    return result is not None and result[1] >= 85


@app.get("/health")
def health():
    return Response(content='{"status":"ok"}', media_type="application/json")


@app.post("/compare_stream")
async def compare_stream(
    cy_file: UploadFile = File(...),
    py_file: UploadFile = File(...),
):
    """
    Streaming compare endpoint.
    Returns Server-Sent Events progress messages, then the final JSON result
    as the last event with type 'result'.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await cy_file.read()); cy_path = f.name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await py_file.read()); py_path = f.name

    async def generate():
        try:
            # Step 1: Parse
            yield _sse("📂  Parsing CY file…", 5)
            cy_data = parse_fca_file(cy_path)
            yield _sse("📂  Parsing PY file…", 10)
            py_data = parse_fca_file(py_path)

            n_tabs = len(cy_data)
            yield _sse(f"✅  Parsed {n_tabs} tabs from each file", 15)

            # Step 2: Align tabs
            yield _sse("🔗  Matching tabs between CY and PY…", 20)
            tab_alignment = align_tabs(cy_data, py_data)
            matched = sum(1 for v in tab_alignment.values() if v["status"] != "unmatched")
            yield _sse(f"✅  {matched} tabs matched", 25)

            # Step 3: Process each tab
            all_results, all_ccr = [], []
            matched_tabs = [(cy_tab, info) for cy_tab, info in tab_alignment.items()
                            if info["status"] != "unmatched"]
            total = len(matched_tabs)

            for i, (cy_tab, info) in enumerate(matched_tabs):
                pct = 25 + int((i / total) * 30)
                if not _is_mandatory(cy_tab):
                    yield _sse(f"⏭  Skipping {cy_tab}", pct)
                    continue
                yield _sse(f"📊  Analysing {cy_tab}…", pct)
                py_tab    = info["py_tab"]
                aligned   = align_rows(cy_data[cy_tab], py_data[py_tab])
                movements = compute_movements(aligned)
                all_ccr  += check_consistency(movements, cy_tab)
                all_ccr  += check_reasonableness(movements, cy_tab)
                all_ccr  += check_zero_emergence(movements, cy_tab)
                all_results.append({
                    "tab":  cy_tab,
                    "data": movements.to_dict(orient="records"),
                })

            all_ccr += check_completeness(cy_data, FCA_MANDATORY_TABS)
            yield _sse(f"✅  CCR checks complete — {len(all_ccr)} findings", 58)

            # Step 4: HKRBC
            yield _sse("🏛  Extracting HKRBC capital data…", 62)
            try:
                hkrbc = extract_hkrbc_data(cy_path, py_path)
                yield _sse("✅  Capital data extracted", 67)
            except Exception as e:
                hkrbc = {"cy": {}, "py": {}, "ai_commentary": f"[HKRBC unavailable: {e}]"}
                yield _sse("⚠️  HKRBC data unavailable", 67)

            # Step 5: AI Commentary (parallel)
            high_priority = [
                row for r in all_results for row in r["data"]
                if row.get("priority") == "High" and row.get("pct_change") is not None
            ]
            n_hi = len(high_priority[:20])
            if n_hi > 0:
                yield _sse(f"🤖  Generating AI commentary for {n_hi} High-priority items (parallel)…", 70)
                commented = generate_commentary(high_priority)
                yield _sse(f"✅  AI commentary complete", 92)
            else:
                commented = []
                yield _sse("ℹ️  No High-priority items for commentary", 92)

            # Step 6: Capital AI commentary
            yield _sse("🤖  Generating capital adequacy commentary…", 94)
            # Already done inside extract_hkrbc_data above

            # Step 7: Done — emit final result
            yield _sse("✅  Analysis complete!", 98)

            payload = _safe_response({
                "tab_alignment": tab_alignment,
                "results":       all_results,
                "ccr_findings":  all_ccr,
                "commentary":    commented,
                "hkrbc":         hkrbc,
            }).body.decode("utf-8")

            yield f"event: result\ndata: {payload}\n\n"

        finally:
            try: os.unlink(cy_path); os.unlink(py_path)
            except: pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Keep original /compare for backwards compat ───────────────────────────
@app.post("/compare")
async def compare(cy_file: UploadFile = File(...), py_file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await cy_file.read()); cy_path = f.name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as f:
        f.write(await py_file.read()); py_path = f.name
    try:
        cy_data = parse_fca_file(cy_path)
        py_data = parse_fca_file(py_path)
        tab_alignment = align_tabs(cy_data, py_data)
        all_results, all_ccr = [], []
        for cy_tab, info in tab_alignment.items():
            if info["status"] == "unmatched": continue
            if not _is_mandatory(cy_tab): continue
            aligned   = align_rows(cy_data[cy_tab], py_data[info["py_tab"]])
            movements = compute_movements(aligned)
            all_ccr  += check_consistency(movements, cy_tab)
            all_ccr  += check_reasonableness(movements, cy_tab)
            all_ccr  += check_zero_emergence(movements, cy_tab)
            all_results.append({"tab": cy_tab, "data": movements.to_dict(orient="records")})
        all_ccr += check_completeness(cy_data, FCA_MANDATORY_TABS)
        try:
            hkrbc = extract_hkrbc_data(cy_path, py_path)
        except Exception as e:
            hkrbc = {"cy": {}, "py": {}, "ai_commentary": f"[HKRBC unavailable: {e}]"}
        high_priority = [
            row for r in all_results for row in r["data"]
            if row.get("priority") == "High" and row.get("pct_change") is not None
        ]
        commented = generate_commentary(high_priority)
        return _safe_response({
            "tab_alignment": tab_alignment, "results": all_results,
            "ccr_findings": all_ccr, "commentary": commented, "hkrbc": hkrbc,
        })
    finally:
        try: os.unlink(cy_path); os.unlink(py_path)
        except: pass


@app.post("/check_working_file")
async def check_wf(cy_file: UploadFile = File(...), working_file: UploadFile = File(...)):
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
    memo = generate_executive_summary(req.hkrbc, req.results, req.ccr_findings)
    return _safe_response(memo)


@app.post("/executive_summary_pdf")
async def executive_summary_pdf(req: SummaryRequest):
    memo = generate_executive_summary(req.hkrbc, req.results, req.ccr_findings)
    pdf_bytes = build_summary_pdf(memo)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=FCA_Review_Memo.pdf"})


class MemoRequest(BaseModel):
    memo: dict


@app.post("/render_pdf")
async def render_pdf(req: MemoRequest):
    try:
        pdf_bytes = render_memo_to_pdf(req.memo)
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=FCA_Review_Memo.pdf"})
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


class ExportRequest(BaseModel):
    results:    list
    ai_remarks: bool = True


@app.post("/export_results")
async def export_results(req: ExportRequest):
    xlsx_bytes = build_excel(req.results, use_ai_remarks=req.ai_remarks)
    return StreamingResponse(io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=FCA_Review_Report.xlsx"})
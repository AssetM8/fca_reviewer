"""
backend/exporter.py
-------------------
Builds a formatted Excel workbook with one sheet per FCA tab.

Columns:
  A  Description
  B  Code
  C  YE24  (Prior Year value)
  D  YE25  (Current Year value)
  E  Difference    — Excel formula =D{n}-C{n}
  F  % Movement    — Excel formula =IF(C{n}<>0,(D{n}-C{n})/ABS(C{n}),"")
  G  Remarks       — AI-generated for |% movement| >= REMARK_THRESHOLD

Rows are written in the ORIGINAL FCA return order (sorted by row_num),
matching exactly the order seen in the source file.
"""

import io, math, json, httpx, os
from dotenv import load_dotenv

load_dotenv()

try:
    import xlsxwriter
    HAS_XLS = True
except ImportError:
    HAS_XLS = False

BASE_URL = os.getenv("LLM_BASE_URL", "https://nova.deloitte.com.cn/del/v1")
API_KEY  = os.getenv("LLM_API_KEY", "")
MODEL    = os.getenv("LLM_MODEL", "Kimi-K2.5")

REMARK_THRESHOLD = 20.0   # |% change| above this → AI remark


# ── AI remark ─────────────────────────────────────────────────────────────

def _stream_remark(description, code, ye24, ye25, diff, pct, tab) -> str:
    sign = "increase" if diff > 0 else "decrease"
    user_msg = (
        f"Tab: {tab}\nAccount: {description} ({code})\n"
        f"YE24: {ye24:,.0f}   YE25: {ye25:,.0f}\n"
        f"Movement: {diff:,.0f} ({pct:+.1f}%) - {sign}\n\n"
        "Write one plain English sentence explaining the likely business driver. "
        "No LaTeX, no dollar signs, use HKD for currency."
    )
    url = BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content":
             "You are a senior actuary writing review remarks for HKIA FCA regulatory returns. "
             "One sentence. Plain English only. No LaTeX or markdown."},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 80, "stream": True,
    }
    collected = []
    try:
        with httpx.Client(verify=False, timeout=60) as client:
            with client.stream("POST", url, headers=headers, json=payload) as resp:
                for line in resp.iter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"): continue
                    s = line[len("data:"):].strip()
                    if s == "[DONE]": break
                    try:
                        c = json.loads(s)["choices"][0]["delta"].get("content") or ""
                        if c: collected.append(c)
                    except Exception: continue
        return "".join(collected).strip()
    except Exception as e:
        return f"[Unavailable: {e}]"


def _safe_float(val):
    if val is None: return None
    try:
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


# ── Excel builder ──────────────────────────────────────────────────────────

def build_excel(results: list, use_ai_remarks: bool = True) -> bytes:
    if not HAS_XLS:
        raise RuntimeError("xlsxwriter not installed.")

    buf = io.BytesIO()
    wb  = xlsxwriter.Workbook(buf, {"in_memory": True})

    # ── Workbook-level formats ────────────────────────────────────────────
    # Header row
    hdr_fmt = wb.add_format({
        "bold": True, "bg_color": "#1A1A1A", "font_color": "#FFFFFF",
        "border": 1, "align": "center", "valign": "vcenter",
        "text_wrap": True, "font_size": 10,
    })
    # Sub-header (column letter row)
    sub_fmt = wb.add_format({
        "bold": True, "bg_color": "#2D2D2D", "font_color": "#86BC25",
        "border": 1, "align": "center", "valign": "vcenter", "font_size": 9,
    })

    # Description / label cells
    desc_fmt = wb.add_format({
        "border": 1, "valign": "vcenter", "text_wrap": True, "font_size": 9,
        "indent": 1,
    })
    code_fmt = wb.add_format({
        "border": 1, "valign": "vcenter", "font_size": 9,
        "align": "center", "font_color": "#595959",
    })

    # Numeric: plain value
    num_fmt  = wb.add_format({"num_format": "#,##0", "border": 1, "align": "right", "font_size": 9})
    # Numeric: difference — positive green, negative red (set per cell)
    pos_fmt  = wb.add_format({"num_format": "#,##0", "border": 1, "align": "right",
                               "font_color": "#2D4A00", "font_size": 9})
    neg_fmt  = wb.add_format({"num_format": "#,##0", "border": 1, "align": "right",
                               "font_color": "#A8071A", "font_size": 9})
    # Percentage formula cell
    pct_pos  = wb.add_format({"num_format": "0.0%", "border": 1, "align": "right",
                               "font_color": "#2D4A00", "font_size": 9})
    pct_neg  = wb.add_format({"num_format": "0.0%", "border": 1, "align": "right",
                               "font_color": "#A8071A", "font_size": 9})
    pct_na   = wb.add_format({"border": 1, "align": "center", "font_size": 9,
                               "font_color": "#8A8A8A"})
    dash_fmt = wb.add_format({"border": 1, "align": "center", "font_color": "#8A8A8A", "font_size": 9})
    rem_fmt  = wb.add_format({"border": 1, "valign": "vcenter", "text_wrap": True,
                               "font_size": 8, "font_color": "#404040", "italic": True})

    # Priority highlight overlays
    hi_desc  = wb.add_format({"bg_color": "#FFF1F0", "border": 1, "valign": "vcenter",
                               "text_wrap": True, "font_size": 9, "indent": 1})
    hi_num   = wb.add_format({"bg_color": "#FFF1F0", "num_format": "#,##0",
                               "border": 1, "align": "right", "font_size": 9})
    hi_pct_p = wb.add_format({"bg_color": "#FFF1F0", "num_format": "0.0%",
                               "border": 1, "align": "right",
                               "font_color": "#2D4A00", "font_size": 9})
    hi_pct_n = wb.add_format({"bg_color": "#FFF1F0", "num_format": "0.0%",
                               "border": 1, "align": "right",
                               "font_color": "#A8071A", "font_size": 9})
    med_desc = wb.add_format({"bg_color": "#FFFBE6", "border": 1, "valign": "vcenter",
                               "text_wrap": True, "font_size": 9, "indent": 1})
    med_num  = wb.add_format({"bg_color": "#FFFBE6", "num_format": "#,##0",
                               "border": 1, "align": "right", "font_size": 9})
    med_pct_p= wb.add_format({"bg_color": "#FFFBE6", "num_format": "0.0%",
                               "border": 1, "align": "right",
                               "font_color": "#2D4A00", "font_size": 9})
    med_pct_n= wb.add_format({"bg_color": "#FFFBE6", "num_format": "0.0%",
                               "border": 1, "align": "right",
                               "font_color": "#A8071A", "font_size": 9})

    COLS = ["Description", "Code", "YE24", "YE25", "Difference", "% Movement", "Remarks"]
    WIDTHS = [46, 10, 18, 18, 18, 14, 52]

    for tab_result in results:
        tab_name = tab_result["tab"]
        rows     = tab_result["data"]

        # Sheet name: max 31 chars, no special chars
        safe = (tab_name[:31]
                .replace("/","-").replace("\\","-")
                .replace("?","").replace("*","")
                .replace("[","").replace("]",""))
        ws = wb.add_worksheet(safe)

        # Column widths
        for i, w in enumerate(WIDTHS):
            ws.set_column(i, i, w)

        # Row 0: main header with tab name spanning all columns
        ws.merge_range(0, 0, 0, 6,
                       f"FCA Return — {tab_name}   |   YE2025 vs YE2024   |   HKD Thousands",
                       wb.add_format({
                           "bold": True, "bg_color": "#86BC25", "font_color": "#111111",
                           "border": 1, "align": "left", "valign": "vcenter",
                           "font_size": 11, "indent": 1,
                       }))
        ws.set_row(0, 22)

        # Row 1: column headers
        ws.set_row(1, 30)
        for i, col in enumerate(COLS):
            ws.write(1, i, col, hdr_fmt)

        ws.freeze_panes(2, 0)   # freeze both header rows

        # ── Sort rows in original FCA file order ──────────────────────────
        # row_num comes from the parser and reflects the original Excel row.
        # Rows without row_num (e.g. missing_in_cy) go to the bottom.
        def _row_sort_key(r):
            rn = r.get("row_num")
            try: return float(rn) if rn is not None else 99999
            except: return 99999

        sorted_rows = sorted(rows, key=_row_sort_key)

        # ── Write data rows ───────────────────────────────────────────────
        xl_row = 2   # 0-indexed; rows 0 and 1 are headers
        for item in sorted_rows:
            desc     = item.get("description") or ""
            code     = item.get("cy_code") or item.get("py_code") or ""
            ye24     = _safe_float(item.get("py_value"))
            ye25     = _safe_float(item.get("cy_value"))
            pct_raw  = _safe_float(item.get("pct_change"))
            priority = item.get("priority", "Low")

            # Column letter references (1-indexed in xlsxwriter formulas use A1 notation)
            xl_row_1 = xl_row + 1   # Excel row number (1-based)
            C = f"C{xl_row_1}"      # YE24
            D = f"D{xl_row_1}"      # YE25

            # Pick formats by priority
            if priority == "High":
                d_fmt = hi_desc; n_fmt = hi_num
                pp_fmt = hi_pct_p; pn_fmt = hi_pct_n
            elif priority == "Medium":
                d_fmt = med_desc; n_fmt = med_num
                pp_fmt = med_pct_p; pn_fmt = med_pct_n
            else:
                d_fmt = desc_fmt; n_fmt = num_fmt
                pp_fmt = pct_pos; pn_fmt = pct_neg

            ws.set_row(xl_row, 15)

            # A: Description
            ws.write(xl_row, 0, desc, d_fmt)
            # B: Code
            ws.write(xl_row, 1, code, code_fmt)

            # C: YE24 (prior year)
            if ye24 is not None:
                ws.write_number(xl_row, 2, ye24, n_fmt)
            else:
                ws.write(xl_row, 2, "", n_fmt)

            # D: YE25 (current year)
            if ye25 is not None:
                ws.write_number(xl_row, 3, ye25, n_fmt)
            else:
                ws.write(xl_row, 3, "", n_fmt)

            # E: Difference — formula =D-C
            if ye24 is not None and ye25 is not None:
                diff_val = ye25 - ye24
                diff_fmt = (pos_fmt if priority == "Low" else n_fmt) if diff_val >= 0 else (neg_fmt if priority == "Low" else n_fmt)
                ws.write_formula(xl_row, 4, f"={D}-{C}", diff_fmt, ye25 - ye24)
            else:
                ws.write(xl_row, 4, "—", dash_fmt)

            # F: % Movement — formula =IF(C<>0,(D-C)/ABS(C),"")
            if ye24 is not None and ye25 is not None and ye24 != 0:
                pct_val  = (ye25 - ye24) / abs(ye24)
                pf       = pp_fmt if pct_val >= 0 else pn_fmt
                ws.write_formula(xl_row, 5,
                    f'=IF({C}<>0,({D}-{C})/ABS({C}),"")',
                    pf, pct_val)
            else:
                ws.write(xl_row, 5, "—", dash_fmt)

            # G: Remarks — AI for significant movers
            remark = ""
            if use_ai_remarks and pct_raw is not None and ye24 is not None and ye25 is not None:
                if abs(pct_raw) >= REMARK_THRESHOLD or priority == "High":
                    remark = _stream_remark(
                        desc, code, ye24, ye25,
                        ye25 - ye24, pct_raw, tab_name
                    )
            ws.write(xl_row, 6, remark, rem_fmt)

            xl_row += 1

        # Auto-filter on header row
        ws.autofilter(1, 0, xl_row - 1, 6)

    wb.close()
    buf.seek(0)
    return buf.read()
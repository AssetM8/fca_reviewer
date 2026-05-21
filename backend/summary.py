"""
backend/summary.py
------------------
Generates an AI executive summary memo and exports it as PDF.
"""

import json, re, io, math, os, httpx
from datetime import date
from dotenv import load_dotenv
load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL", "https://nova.deloitte.com.cn/del/v1")
API_KEY  = os.getenv("LLM_API_KEY", "")
MODEL    = os.getenv("LLM_MODEL", "Kimi-K2.5")

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


# ── Kimi call ──────────────────────────────────────────────────────────────

def _stream(system: str, user: str, max_tokens: int = 800) -> str:
    url = BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens, "stream": True,
    }
    collected = []
    try:
        with httpx.Client(verify=False, timeout=180) as client:
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
        result = "".join(collected).strip()
        # Strip LaTeX artifacts
        result = re.sub(r'\$+', '', result)
        result = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', result)
        result = re.sub(r'  +', ' ', result)
        return result
    except Exception as e:
        return f"[Unavailable: {e}]"


# ── Data helpers ───────────────────────────────────────────────────────────

def _fmt(v, suffix=""):
    if v is None: return "N/A"
    try: return f"{float(v):,.0f}{suffix}"
    except: return str(v)

def _pct(v):
    if v is None: return "N/A"
    try: return f"{float(v):.1f}%"
    except: return str(v)

def _chg(a, b):
    try:
        a, b = float(a), float(b)
        if b == 0: return "N/A"
        return f"{((a-b)/abs(b))*100:+.1f}%"
    except: return "N/A"


# ── Build structured memo data ────────────────────────────────────────────

def _top_movements(results: list, n: int = 5) -> list:
    """Return the n largest movements by absolute % change."""
    rows = []
    for tr in results:
        for row in tr["data"]:
            pct = row.get("pct_change")
            if pct is None: continue
            try:
                rows.append({
                    "tab":         tr["tab"],
                    "description": row.get("description", ""),
                    "code":        row.get("cy_code", ""),
                    "cy":          row.get("cy_value"),
                    "py":          row.get("py_value"),
                    "movement":    row.get("abs_movement"),
                    "pct":         float(pct),
                    "priority":    row.get("priority", "Low"),
                })
            except: continue
    rows.sort(key=lambda r: abs(r["pct"]), reverse=True)
    return rows[:n]


def generate_executive_summary(hkrbc: dict, results: list, ccr_findings: list) -> dict:
    """
    Returns a dict with sections that can be displayed and exported.
    {
        "memo_date":    str,
        "capital":      dict of key metrics,
        "top_movements":list,
        "ccr_summary":  str,
        "ai_narrative": str,   # Kimi-generated 4-paragraph memo
        "actions":      str,   # Kimi-generated follow-up actions
    }
    """
    cy = hkrbc.get("cy", {}) or {}
    py = hkrbc.get("py", {}) or {}
    top = _top_movements(results, 5)
    high_ccr = [f for f in ccr_findings if f.get("severity") == "High"]

    # ── Build context string for Kimi ────────────────────────────────────
    capital_block = f"""
CAPITAL ADEQUACY
  Eligible Capital:  YE25={_fmt(cy.get('eligible_capital'))}  YE24={_fmt(py.get('eligible_capital'))}  Change={_chg(cy.get('eligible_capital'), py.get('eligible_capital'))}
  PCA:               YE25={_fmt(cy.get('pca'))}               YE24={_fmt(py.get('pca'))}               Change={_chg(cy.get('pca'), py.get('pca'))}
  MCA:               YE25={_fmt(cy.get('mca'))}               YE24={_fmt(py.get('mca'))}               Change={_chg(cy.get('mca'), py.get('mca'))}
  PCA Coverage:      YE25={_pct(cy.get('pca_ratio'))}        YE24={_pct(py.get('pca_ratio'))}
  MCA Coverage:      YE25={_pct(cy.get('mca_ratio'))}        YE24={_pct(py.get('mca_ratio'))}
  Total Assets:      YE25={_fmt(cy.get('total_assets'))}      YE24={_fmt(py.get('total_assets'))}      Change={_chg(cy.get('total_assets'), py.get('total_assets'))}
  Total Liabilities: YE25={_fmt(cy.get('total_liabilities'))} YE24={_fmt(py.get('total_liabilities'))} Change={_chg(cy.get('total_liabilities'), py.get('total_liabilities'))}
  MOCE:              YE25={_fmt(cy.get('moce'))}              YE24={_fmt(py.get('moce'))}              Change={_chg(cy.get('moce'), py.get('moce'))}
  Market Risk RCA:   YE25={_fmt(cy.get('market_risk'))}       YE24={_fmt(py.get('market_risk'))}       Change={_chg(cy.get('market_risk'), py.get('market_risk'))}
  Life Ins Risk RCA: YE25={_fmt(cy.get('life_insurance_risk'))} YE24={_fmt(py.get('life_insurance_risk'))} Change={_chg(cy.get('life_insurance_risk'), py.get('life_insurance_risk'))}
  Operational Risk:  YE25={_fmt(cy.get('op_risk'))}           YE24={_fmt(py.get('op_risk'))}           Change={_chg(cy.get('op_risk'), py.get('op_risk'))}
"""
    movements_block = "TOP 5 MATERIAL MOVEMENTS\n"
    for i, m in enumerate(top, 1):
        movements_block += (
            f"  {i}. {m['description']} ({m['tab']})\n"
            f"     YE25={_fmt(m['cy'])}  YE24={_fmt(m['py'])}  Change={_pct(m['pct'])}  Priority={m['priority']}\n"
        )

    ccr_block = f"CCR FINDINGS ({len(high_ccr)} High-severity)\n"
    for f in high_ccr[:5]:
        ccr_block += f"  [{f.get('check')}] {f.get('tab','')}: {f.get('finding','')}\n"

    system = """
You are a senior actuary writing a formal review memo for the HKIA FCA regulatory return.
Write in professional actuarial English. Be specific with numbers (use HKD thousands).
Do NOT use LaTeX, dollar signs, or markdown formatting symbols.
Use plain text with clear paragraph breaks.
Structure your response as four clearly labelled sections:
SECTION 1 - CAPITAL ADEQUACY OVERVIEW
SECTION 2 - MATERIAL MOVEMENTS COMMENTARY
SECTION 3 - CCR FINDINGS SUMMARY
SECTION 4 - RECOMMENDED FOLLOW-UP ACTIONS
Each section should be 3-5 sentences. Be specific, reference actual numbers.
"""
    user = f"""
Please write a full actuarial review memo for the following YE2025 vs YE2024 comparison.
Today's date: {date.today().strftime('%d %B %Y')}

{capital_block}
{movements_block}
{ccr_block}

Write the four-section memo now.
"""

    ai_narrative = _stream(system, user, max_tokens=900)

    # Parse sections from AI output — robust against Kimi formatting variations
    # Kimi may output "SECTION 1", "**SECTION 1**", "Section 1:", "1.", etc.
    import re as _re
    sections = {"SECTION 1": "", "SECTION 2": "", "SECTION 3": "", "SECTION 4": ""}
    # Patterns that signal a new section
    SEC_PATTERNS = {
        "SECTION 1": _re.compile(r"(section\s*1|capital\s*adequacy\s*overview|1\.\s*capital)", _re.I),
        "SECTION 2": _re.compile(r"(section\s*2|material\s*movements|2\.\s*material)", _re.I),
        "SECTION 3": _re.compile(r"(section\s*3|ccr\s*findings|3\.\s*ccr)", _re.I),
        "SECTION 4": _re.compile(r"(section\s*4|recommended\s*follow|4\.\s*recommended)", _re.I),
    }
    current = None
    for line in ai_narrative.split("\n"):
        matched = False
        for key, pat in SEC_PATTERNS.items():
            if pat.search(line):
                current = key
                matched = True
                break
        if not matched and current:
            sections[current] += line + "\n"

    return {
        "memo_date":     date.today().strftime("%d %B %Y"),
        "capital":       {
            "eligible_capital": cy.get("eligible_capital"),
            "pca":              cy.get("pca"),
            "mca":              cy.get("mca"),
            "pca_ratio":        cy.get("pca_ratio"),
            "mca_ratio":        cy.get("mca_ratio"),
            "pca_ratio_py":     py.get("pca_ratio"),
            "total_assets":     cy.get("total_assets"),
            "total_assets_py":  py.get("total_assets"),
        },
        "top_movements":  top,
        "ccr_high_count": len(high_ccr),
        "ccr_findings":   high_ccr[:5],
        "ai_narrative":   ai_narrative,
        "sections":       sections,
    }


# ── PDF builder ───────────────────────────────────────────────────────────

def build_summary_pdf(memo: dict) -> bytes:
    if not HAS_FPDF:
        raise RuntimeError("fpdf2 not installed. Run: pip install fpdf2")

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ── Title block ───────────────────────────────────────────────────────
    pdf.set_fill_color(31, 56, 100)
    pdf.rect(0, 0, 210, 32, "F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 8)
    pdf.cell(0, 8, _p("ACTUARIAL REVIEW MEMO -- HKIA FCA RETURN"), ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_xy(20, 20)
    pdf.cell(0, 6, _p(f"YE2025 vs YE2024  |  Prepared: {memo['memo_date']}  |  CONFIDENTIAL"), ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # ── Capital metrics table ─────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(134, 188, 37)
    pdf.cell(0, 7, "KEY CAPITAL METRICS (HKD Thousands)", ln=True, fill=True)
    pdf.ln(2)

    cap = memo.get("capital", {})
    metrics = [
        ("Eligible Capital",    cap.get("eligible_capital"),  None,   None),
        ("PCA",                 cap.get("pca"),               cap.get("pca_ratio"), 150),
        ("MCA",                 cap.get("mca"),               cap.get("mca_ratio"), 200),
        ("Total Assets (YE25)", cap.get("total_assets"),      None,   None),
    ]
    col_w = [90, 42, 38]   # 90+42+38 = 170mm = full usable width
    pdf.set_fill_color(230, 240, 250)
    for h, w in zip(["Metric", "YE25 Value", "Status"], col_w):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(w, 6, h, border=1, fill=True)
    pdf.ln()

    for label, val, ratio, thr in metrics:
        val_str = f"{float(val):,.0f}" if val else "N/A"
        if ratio and thr:
            coverage = float(ratio)
            status = f"ADEQUATE ({coverage:.1f}%)" if coverage >= thr else f"LOW ({coverage:.1f}%)"
            pdf.set_fill_color(204, 255, 204) if coverage >= thr else pdf.set_fill_color(255, 204, 204)
        else:
            status = "--"
            pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(col_w[0], 6, _p(label),   border=1)
        pdf.cell(col_w[1], 6, _p(val_str), border=1, align="R")
        pdf.cell(col_w[2], 6, _p(status),  border=1, fill=True)
        pdf.ln()

    pdf.ln(5)

    # ── Top movements table ────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(134, 188, 37)
    pdf.cell(0, 7, "TOP 5 MATERIAL MOVEMENTS", ln=True, fill=True)
    pdf.ln(2)

    col_w2 = [65, 20, 26, 26, 20, 13]
    pdf.set_fill_color(230, 240, 250)
    for h, w in zip(["Description","Tab","YE25","YE24","% Chg","Priority"], col_w2):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(w, 6, h, border=1, fill=True)
    pdf.ln()

    pri_colours = {"High":(255,204,204), "Medium":(255,243,204), "Low":(204,255,204)}
    for m in memo.get("top_movements", []):
        r, g, b = pri_colours.get(m.get("priority","Low"), (255,255,255))
        pdf.set_fill_color(r, g, b)
        pdf.set_font("Helvetica", "", 8)
        desc = _p((m["description"][:36] + "..") if len(m.get("description","")) > 36 else m.get("description",""))
        pdf.cell(col_w2[0], 6, desc,                              border=1, fill=True)
        pdf.cell(col_w2[1], 6, _p(m.get("tab","")[:12]),         border=1)
        pdf.cell(col_w2[2], 6, _fmt(m.get("cy")),                border=1, align="R")
        pdf.cell(col_w2[3], 6, _fmt(m.get("py")),                border=1, align="R")
        pdf.cell(col_w2[4], 6, f"{m.get('pct',0):+.1f}%",      border=1, align="R", fill=True)
        pdf.cell(col_w2[5], 6, _p(m.get("priority","")[:6]),     border=1, fill=True)
        pdf.ln()

    pdf.ln(5)

    # ── AI Narrative sections ─────────────────────────────────────────────
    section_map = {
        "SECTION 1": "1. CAPITAL ADEQUACY OVERVIEW",
        "SECTION 2": "2. MATERIAL MOVEMENTS COMMENTARY",
        "SECTION 3": "3. CCR FINDINGS SUMMARY",
        "SECTION 4": "4. RECOMMENDED FOLLOW-UP ACTIONS",
    }
    sections = memo.get("sections", {})
    has_sections = any(v.strip() for v in sections.values())

    if has_sections:
        for key, title in section_map.items():
            text = sections.get(key, "").strip()
            if not text:
                continue
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_fill_color(134, 188, 37)
            pdf.cell(0, 7, _p(title), ln=True, fill=True)
            pdf.ln(1)
            pdf.set_font("Helvetica", "", 10)
            for line in text.split("\n"):
                line = _p(line.strip())
                if line:
                    pdf.multi_cell(0, 5, line)
            pdf.ln(4)
    else:
        # Fallback: dump full narrative
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(134, 188, 37)
        pdf.cell(0, 7, "AI MEMO", ln=True, fill=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        for line in memo.get("ai_narrative", "").split("\n"):
            line = _p(line.strip())
            if line:
                pdf.multi_cell(0, 5, line)

    # ── Footer ────────────────────────────────────────────────────────────
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 5,
        _p("AI-assisted review -- for actuarial use only. "
           "Findings require professional validation before submission."),
        align="C")

    return bytes(pdf.output())

# ── Patched build_summary_pdf replaces the original above ─────────────────

def _p(text: str) -> str:
    """Sanitize text for fpdf Latin-1 Helvetica font."""
    if not text:
        return ""
    replacements = {
        "\u2014": " - ", "\u2013": " - ",
        "\u2018": "'",   "\u2019": "'",
        "\u201c": '"',   "\u201d": '"',
        "\u2022": "*",   "\u2026": "...",
        "\u00b0": " deg","\u03c3": "sigma",
        "\u00b1": "+/-", "\u2265": ">=", "\u2264": "<=",
        "\u00ae": "(R)", "\u2122": "(TM)",
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def render_memo_to_pdf(memo: dict) -> bytes:
    """
    Render a pre-built memo dict to PDF without making any AI calls.
    Use this when the memo was already generated and stored in session state.
    """
    return build_summary_pdf(memo)
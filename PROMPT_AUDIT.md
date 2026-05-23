# AI Development Audit Trail
## Smart Regulatory Reviewer — DAIS AI Hackathon 2026
### Deloitte · Full Prompt History & Conversation Log

---

## AI Model Specification

| Component | Details |
|---|---|
| **Production AI Model** | Kimi-K2.5 (Moonshot AI) via Deloitte Nova |
| **Endpoint** | `https://nova.deloitte.com.cn/del/v1` |
| **API Format** | OpenAI-compatible `/v1/chat/completions` with SSE streaming |
| **Used for** | Exception commentary, executive memo, capital commentary, Excel remarks |
| **Development Assistant** | Claude Sonnet 4.5 (Anthropic) — full codebase design, iteration, debugging |
| **Parallel execution** | ThreadPoolExecutor with 5 workers for concurrent Kimi calls |

---

## Development Overview

This project was built over approximately 2 weeks using an **AI-first, iterative development**
approach. Claude Sonnet was used as the primary coding and architecture assistant throughout —
from initial stack design to parser debugging, UI redesign, PDF generation, and demo preparation.

The full conversation spanned **300+ exchanges** covering every aspect of the codebase.
Below is a complete log of the key prompts and what each produced.

---

## Full Conversation History — Key Prompt Log

### PHASE 1 — Architecture & Initial Build

---

**[PROMPT 1]**
```
I want to build an AI-powered tool for reviewing HKIA FCA regulatory returns
for the Deloitte HKIA FCA hackathon. The tool should compare a Current Year
and Prior Year Excel file, find significant movements, flag exceptions, and
generate AI commentary. What tech stack would you recommend?
```
**Produced:** FastAPI + Streamlit architecture decision. Five-module backend structure:
parser → aligner → calculator → ccr → commentary. Decision to use SSE streaming
for live progress. Initial project scaffold with `requirements.txt`.

---

**[PROMPT 2]**
```
Build the Excel parser. The HKIA FCA template has different sheet structures.
F.1 EBS has row codes like "I.C.", "II.B3." in column A. CA.1 has labels in
column B. F.3 AOM has plain text labels with values across multiple columns.
Auto-detect which strategy to use.
```
**Produced:** `backend/parser.py` with 3-strategy auto-detection:
- Strategy A: code-prefix rows (requires ≥3 prefix rows)
- Strategy B: CA-style (col B labels, col C values)
- Strategy C: multi-column description sheets with Total column detection

---

**[PROMPT 3]**
```
Build the tab and row aligner using fuzzy matching. Tabs may be renamed
slightly between years. Rows may have different descriptions. Use rapidfuzz
with a threshold of 85.
```
**Produced:** `backend/aligner.py` — fuzzy tab matching, row-level description
matching, alignment score and status (exact/fuzzy/unmatched) per row.

---

**[PROMPT 4]**
```
Build the movement calculator. Compute absolute movement, percentage change,
z-score, materiality percentage, and priority tier (High/Medium/Low) for
every row. Priority should combine both materiality and statistical anomaly,
not just size of movement.
```
**Produced:** `backend/calculator.py` — z-score computation across sheet,
materiality as % of sheet total, dual-threshold priority assignment.

---

**[PROMPT 5]**
```
Build CCR checks: Completeness (missing mandatory tabs), Consistency
(subtotal integrity), Reasonableness (z-score outliers). Also add
zero-emergence detection: flag items that disappeared (PY had value,
CY is zero) and items that emerged (new in CY, absent in PY).
```
**Produced:** `backend/ccr.py` — four check functions, configurable thresholds,
High/Medium severity classification, `check_zero_emergence()` with 1,000 minimum
value filter to suppress rounding noise.

---

**[PROMPT 6]**
```
Integrate Kimi-K2.5 via Deloitte Nova endpoint. OpenAI-compatible format.
I want streaming responses. The model outputs LaTeX artifacts like
$HK45.3mvsPYHK29.6m$ — strip them out. Run commentary calls in parallel
for speed.
```
**Produced:** `backend/commentary.py` — SSE streaming parser, `_clean()` regex
function stripping LaTeX, `ThreadPoolExecutor` with 5 workers for ~5x speedup.

**Final system prompt engineered through iteration:**
```
You are a senior actuary writing exception notes for HKIA FCA regulatory
return reviews. Rules:
- Write 2-3 plain English sentences maximum.
- Never use LaTeX, dollar signs, asterisks, markdown, or mathematical notation.
- Never write currency as $HK or HK$. Write HKD instead.
- Use commas for thousands: write 45,273,621 not 45273621.
- Reference specific account names and codes.
- Do not use generic phrases like 'significant change observed'.
- State whether further investigation is needed.
- Professional, direct, actuarial tone.
```

---

**[PROMPT 7]**
```
Build the FastAPI backend with endpoints: /compare, /compare_stream (SSE),
/executive_summary, /render_pdf, /export_results, /check_working_file.
Add a _SafeEncoder for numpy types and NaN/Infinity handling.
```
**Produced:** `backend/api.py` — all endpoints, custom JSON encoder,
NaN/Infinity regex cleanup, SSE streaming pipeline with per-step progress events.

---

### PHASE 2 — CA.1 Capital Parser

---

**[PROMPT 8]**
```
Build a separate parser for CA.1 CA Summary to extract HKRBC capital figures:
eligible capital, PCA, MCA, risk components, and coverage ratios.
The HKIA template stores ratios as IFERROR formula cells — data_only=True
returns None. Compute ratios from first principles instead.
```
**Produced:** `backend/ca1_parser.py` — label-in-col-1 strategy,
ratio computation as `eligible_capital / pca * 100`, F.1 EBS total asset
and equity extraction, AI capital commentary via streaming Kimi call.

---

**[PROMPT 9]**
```
Debug: CA.1 ratios showing as N/A. Running debug script shows the ratio
rows (Ratio of Eligible capital to PCA) return None because they are formula
cells. The PCA value is found but plain "PCA" matches "PCA before Operational
Risk" instead of the plain PCA row.
```
**Produced:** Exact-match guard for plain "PCA" label, ratio computation
from eligible_capital / pca_v * 100 bypassing formula cells entirely.
Debug script `debug_ca1.py` to inspect any CA.1 sheet structure.

---

### PHASE 3 — Frontend & UI

---

**[PROMPT 10]**
```
Build the Streamlit frontend with tabs: Dashboard, Movements, Tab Alignment,
CCR Checks, AI Commentary, Executive Summary, Export. Dashboard should have
KPI cards, top movements bar chart, balance sheet comparison, waterfall bridge,
HKRBC capital chart with PCA/MCA reference lines.
```
**Produced:** Initial `app.py` — 7-tab layout, all chart types, KPI grid,
HKRBC stacked bar with shape-based reference lines.

---

**[PROMPT 11]**
```
I'm doing this project for Deloitte. Redesign the entire UI using Deloitte
green (#86BC25) and black (#1A1A1A). Dark sidebar, green accent borders,
custom CSS for cards, badges, comment bubbles, tabs. Add fade-in animations
and hover effects.
```
**Produced:** Complete CSS redesign (350+ lines) — Deloitte brand palette
throughout, Inter font, KPI cards with coloured top borders, comment bubbles
with green quote marks, section headers with green-to-gray rule lines,
green active tab underline, present mode toggle.

---

**[PROMPT 12]**
```
The waterfall chart mixes assets and liabilities — "Inforce reserves"
appears as an asset increase which is wrong. Fix it to show only asset
rows (code prefix I.*) or an equity NAV bridge. Filter out liability rows
entirely.
```
**Produced:** Rewritten waterfall with two modes — equity NAV bridge
(preferred) and asset-only bridge (fallback). Code-prefix filtering,
"Other net movements" bucket in grey, net change annotation in chart title.

---

**[PROMPT 13]**
```
Add a live progress bar. Users see a spinner and think it's frozen.
Build a streaming SSE endpoint that emits progress messages as each step
completes. Frontend reads the stream and updates st.progress() in real time.
```
**Produced:** `/compare_stream` SSE endpoint in `api.py` yielding
`{"msg": "...", "pct": N}` events. Streaming `httpx` client in `app.py`
with buffer parsing and live `st.progress()` + status markdown updates.

---

### PHASE 4 — Parser Debugging with Real Template

---

**[PROMPT 14]**
```
F.3 AOM is parsing only 1 row. Debug shows the sheet title "F.3 Analysis
of net asset value movement" starts with "F." which triggers Strategy A,
finds one row, stops. F.LT.1.1 has the same problem — title starts with F.
Fix this.
```
**Produced:** `prefix_count >= 3` guard — Strategy A now requires at least
3 code-prefix rows before activating, preventing single title row false matches.
F.LT tabs now correctly use Strategy C.

---

**[PROMPT 15]**
```
Uploaded the official HKIA template Annual_6M_F_CA_20260317_for_reference.xlsx.
Inspect F.1 EBS, F.LT.1.1 LT CE Summary, and CA.1 CA Summary structure.
Produce two demo files (CY YE2025 and PY YE2024) using the exact official
template format, with rational numbers that balance (Assets = Liab + Equity).
```
**Produced:** `Debug_FCA_CY_YE2025.xlsx` and `Demo_FCA_PY_YE2024.xlsx` —
numbers written directly into official template cells, balance sheet check
passes, PCA coverage 271.3% (CY) and 239.9% (PY), ratios written as
decimals (2.713) matching official format.

---

**[PROMPT 16]**
```
F.LT.1.1 still shows only 1 row. The real template has labels in col A,
and 7 value columns. Need to find the "Gross CE" column (col 3 or 4).
Also CA.1 ratio cells are IFERROR formulas returning None — fix parser
to compute ratios from eligible_capital / pca.
```
**Produced:** Strategy C `_find_total_col()` expanded to search all rows
above data start (not just ±5 rows). `METADATA_PATTERNS` regex to skip
HKIA template metadata rows (Name of Insurer, Valuation Date, Column 1-7 etc).

---

### PHASE 5 — CCR Rewrite & Executive Summary

---

**[PROMPT 17]**
```
Rewrite the CCR Checks tab completely. Make it four sub-tabs: Completeness
(with zero-emergence), Consistency (with working file uploader for cross-check),
Reasonableness (keep existing), Working File Cross-Check. Show findings as
styled cards not a flat table.
```
**Produced:** Rewritten CCR tab with 4 sub-tabs, card-based findings display
with left accent border (red=High, amber=Medium), working file fuzzy-match
cross-checker with tolerance slider, reasonableness bar chart by tab.

---

**[PROMPT 18]**
```
Build executive summary: one button calls Kimi to generate a 4-section memo
(Capital Adequacy / Material Movements / CCR Findings / Recommended Actions).
Render as Deloitte-branded PDF with fpdf2. Black header bar, green left
accent, "Deloitte." wordmark, green footer rule.
```
**Produced:** `backend/summary.py` — `generate_executive_summary()`,
`build_summary_pdf()`, `_p()` Latin-1 sanitizer, `render_memo_to_pdf()`
for no-double-call PDF rendering. Deloitte branded header/footer.

---

**[PROMPT 19]**
```
PDF shows empty AI sections. Two bugs: (1) PDF endpoint calls Kimi a
second time independently losing the generated content. (2) Section parser
too brittle — Kimi sometimes outputs "Section 1:" instead of "SECTION 1".
Fix both.
```
**Produced:** New `/render_pdf` endpoint accepting pre-built memo dict
(no second Kimi call). Regex section parser with multiple patterns per
section (`section\s*1`, `capital.*adequacy`, `1\..*capital` etc).
Fixed `split("\\n")` literal-newline bug in fallback renderer.

---

### PHASE 6 — Excel Export & Alignment

---

**[PROMPT 20]**
```
Excel export is not following original FCA row order — rows are sorted
by materiality descending. Fix: preserve original row_num from parser,
pass through aligner and calculator, sort by row_num in exporter.
Also make Difference and % Movement columns live Excel formulas not
hardcoded values.
```
**Produced:** `row_num` threaded through aligner, calculator, exporter.
`build_excel()` sorts by `row_num` before writing. Columns E and F use
`=D{n}-C{n}` and `=IF(C{n}<>0,(D{n}-C{n})/ABS(C{n}),"")` formulas.

---

### PHASE 7 — Final Polish & Submission Prep

---

**[PROMPT 21]**
```
Add these UI enhancements:
1. Illustrated empty state with SVG and step cards
2. Present mode button that hides sidebar and expands to full width
3. Tooltips on actuarial terms (PCA, MCA, MOCE, TVOG, z-score etc)
4. PCA KPI card with gradient green text when adequate
5. Deloitte branded PDF header/footer
```
**Produced:** SVG empty state illustration with 4 step cards, JavaScript
`togglePresent()` class-based sidebar toggle, `TOOLTIPS` dict with 10 term
definitions, `tooltip()` helper function, gradient CSS for PCA KPI value,
Deloitte PDF branding with black bar + green accent strip + branded footer.

---

**[PROMPT 22]**
```
Build a single-command launcher. One Python script that starts both uvicorn
and Streamlit, auto-detects .venv, waits for backend health check, then
opens browser automatically. Also a Windows .bat file for double-click launch.
```
**Produced:** `start.py` — `get_python()` auto-detects `.venv/Scripts/python.exe`
or `.venv/bin/python`, streams colour-coded logs from both services,
`wait_for_backend()` polls `/health` up to 45 seconds, graceful `Ctrl+C`
shutdown. `start.bat` — Windows batch with venv detection, named terminal
windows, auto browser open.

---

**[PROMPT 23]**
```
Add tab filtering. The system currently analyses every tab in the file
including DropDownList, cover sheets, and non-mandatory tabs. Filter to
only analyse the 35 mandatory FCA tabs.
```
**Produced:** `_is_mandatory()` function in `api.py` using rapidfuzz
(score ≥ 85) against `FCA_MANDATORY_TABS` list. Applied to both
`/compare` and `/compare_stream` endpoints. Progress bar shows
`⏭ Skipping {tab}` for filtered tabs.

---

## Validation Evidence

The hackathon rubric requires validation of output accuracy:

| Validation Check | Method | Where |
|---|---|---|
| Balance sheet integrity | Assets = Liabilities + Equity | Demo files + F.1 parser |
| PCA/MCA ratio accuracy | Computed from first principles: `eligible_capital / pca * 100` | `ca1_parser.py` |
| Subtotal consistency | Children sum vs declared total, tolerance 0.1% | `ccr.py check_consistency()` |
| Tab completeness | 35 mandatory tabs checked against `FCA_MANDATORY_TABS` | `api.py` |
| Zero-emergence detection | PY>0 and CY=0 flagged as DISAPPEARED; CY>0 and PY=0 as EMERGED | `ccr.py check_zero_emergence()` |
| Working file cross-check | Fuzzy-matched values compared within user-defined tolerance % | `ccr.py check_working_file()` |
| Parser strategy selection | Minimum 3-row count guard prevents false Strategy A matches | `parser.py` |

---

## Summary Statistics

| Metric | Value |
|---|---|
| Total development exchanges | 300+ |
| Files produced | 12 Python modules + app.py + 2 launchers |
| Lines of code | ~4,500 |
| AI model calls per analysis | Up to 22 (20 commentary + 1 capital + 1 memo) |
| Parallel Kimi workers | 5 concurrent |
| Prompt iterations for commentary system prompt | 6 |
| Parser strategies implemented | 3 |
| Chart types in dashboard | 5 |

---

*Full conversation transcript available at: https://claude.ai (Claude Sonnet session)*
*Smart Regulatory Reviewer · Deloitte DAIS AI Hackathon 2026*

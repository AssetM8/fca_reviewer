# Smart Regulatory Reviewer
### AI-powered HKIA FCA Return Comparison Tool
**Deloitte · DAIS AI Hackathon 2026**

---

## What is this?

Smart Regulatory Reviewer is an AI-powered tool that automates the year-on-year review of Hong Kong Insurance Authority (HKIA) Pillar 3 regulatory returns (FCA format). Instead of spending days manually comparing two Excel files, an actuary uploads the Current Year and Prior Year returns and gets instant AI-generated analysis: exception flags, movement commentary, capital adequacy charts, and a formatted PDF memo — all in under 5 minutes.

**Core capabilities:**
- Parses all 35 mandatory FCA tabs automatically
- Flags High / Medium / Low priority exceptions using z-scores and materiality thresholds
- Generates AI reviewer notes for every significant movement via Kimi-K2.5
- Extracts and charts HKRBC capital structure (PCA/MCA coverage ratios)
- Runs 3 types of CCR checks: Completeness, Consistency, Reasonableness
- Exports a formatted Excel report with live formulas and a branded PDF executive memo
- Live progress bar during analysis so you know exactly what's happening

---

## Prerequisites

Before launching for the first time, make sure you have the following installed:

### 1. Python 3.10 or higher
Check if you have it:
```cmd
python --version
```
If not installed, download from: https://www.python.org/downloads/
During installation, tick **"Add Python to PATH"**.

### 2. Git (optional, for cloning)
Download from: https://git-scm.com/download/win

---

## First-Time Setup

Do this **once** before launching for the first time.

### Step 1 — Get the project files
Either clone from GitHub:
```cmd
git clone https://github.com/AssetM8/fca_reviewer.git
cd fca_reviewer
```
Or unzip the provided package and open a terminal in the `fca_reviewer` folder.

### Step 2 — Create a virtual environment
A virtual environment keeps all the required packages isolated from your system Python.

```cmd
python -m venv .venv
```

### Step 3 — Activate the virtual environment
```cmd
.venv\Scripts\activate
```
You will see `(.venv)` appear at the start of your command line. This means it worked.

### Step 4 — Install all required packages
```cmd
pip install -r requirements.txt
```
This takes 2–5 minutes. You will see packages being downloaded and installed.

### Step 5 — Create your `.env` file
The tool needs API credentials to call the AI model. Create a file called `.env` in the `fca_reviewer` folder (same level as `app.py`) with the following content:

```
LLM_BASE_URL=https://nova.deloitte.com.cn/del/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=Kimi-K2.5
```

Replace `your-api-key-here` with your actual Deloitte Nova API key.

> **Important:** Never commit the `.env` file to GitHub. It is already listed in `.gitignore`.

---

## Launching the App

You only need to do the setup above **once**. After that, use any of the three options below every time you want to launch.

---

### Option A — `start.py` (Recommended, cross-platform)

This is the easiest way. One command starts everything and opens the browser automatically.

**Step 1:** Open a terminal (Command Prompt or PowerShell) in the `fca_reviewer` folder.

**Step 2:** Run:
```cmd
py start.py
```

**That's it.** The script will:
1. Find your `.venv` automatically (no need to activate it manually)
2. Start the backend API on port 8001
3. Wait until the backend is ready
4. Start the Streamlit frontend on port 8501
5. Open `http://localhost:8501` in your browser automatically

You will see colour-coded logs from both services in the same terminal:
- `[BACKEND]` lines in green = the API server
- `[FRONTEND]` lines in cyan = the Streamlit app

To stop everything: press `Ctrl+C` once. Both services shut down cleanly.

---

### Option B — `start.bat` (Windows double-click, no terminal needed)

If you prefer not to use the terminal at all, just double-click a file.

**Step 1:** Open Windows Explorer and navigate to the `fca_reviewer` folder.

**Step 2:** Double-click `start.bat`.

**That's it.** Two terminal windows will open automatically (one for the backend, one for the frontend), and your browser will open to `http://localhost:8501` after a few seconds.

To stop: close both terminal windows.

> **Note:** If Windows asks "Do you want to allow this app to make changes?" — click Yes. If Windows SmartScreen blocks it, click "More info" then "Run anyway".

---

### Option C — Manual two-terminal launch (for developers)

If you prefer full control, you can start each service in a separate terminal window.

**Terminal 1 — Start the backend:**
```cmd
cd C:\path\to\fca_reviewer
.venv\Scripts\activate
uvicorn backend.api:app --host 0.0.0.0 --port 8001 --reload
```
Wait until you see:
```
Application startup complete.
Uvicorn running on http://0.0.0.0:8001
```

**Terminal 2 — Start the frontend:**
```cmd
cd C:\path\to\fca_reviewer
.venv\Scripts\activate
streamlit run app.py --server.port 8501
```
Wait until you see:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

Then open `http://localhost:8501` in your browser.

To stop: press `Ctrl+C` in each terminal window.

---

## Using the Tool

Once the app is open in your browser:

1. **Upload files** — Use the sidebar to upload your Current Year (CY) and Prior Year (PY) FCA return Excel files (`.xlsx` format).
2. **Run Analysis** — Click the green **Run Analysis** button. A live progress bar shows each step.
3. **Review results** — Navigate the tabs:
   - 🏠 **Dashboard** — KPI cards, top movements, waterfall bridge, HKRBC capital chart
   - 📈 **Movements** — Full row-by-row comparison for each FCA tab
   - 🔗 **Alignment** — Shows how CY tabs were matched to PY tabs
   - ✅ **CCR Checks** — Completeness, Consistency, Reasonableness findings
   - 🤖 **AI Notes** — Kimi-K2.5 commentary on High-priority exceptions
   - 📄 **Exec Summary** — Generate and download a branded PDF review memo
   - ⬇ **Export** — Download Excel report with live formulas
4. **Present mode** — Click the **⛶ Present Mode** button in the sidebar to hide the sidebar and go full-width for presentations.

---

## Demo Files

Two sample FCA return files are included for testing:

| File | Description |
|---|---|
| `templates/Demo_FCA_CY_YE2025.xlsx` | Current Year (YE2025) — Demo Insurer HK Ltd |
| `templates/Demo_FCA_PY_YE2024.xlsx` | Prior Year (YE2024) — Demo Insurer HK Ltd |

These use synthetic numbers. Key figures:
- **Total Assets:** HKD 38,500k (PY) → HKD 45,000k (CY) — +16.9% growth
- **PCA Coverage:** 239.9% (PY) → 271.3% (CY) — improving solvency
- **MCA Coverage:** 479.8% (PY) → 542.5% (CY)

Both files balance: Assets = Liabilities + Equity ✓

---

## Project Structure

```
fca_reviewer/
├── app.py                        # Streamlit frontend
├── start.py                      # Cross-platform launcher
├── start.bat                     # Windows double-click launcher
├── requirements.txt              # Python dependencies
├── .env                          # API credentials (create manually, not in git)
├── .gitignore
├── README.md
├── templates/
│   ├── Demo_FCA_CY_YE2025.xlsx   # Sample current year return
│   └── Demo_FCA_PY_YE2024.xlsx   # Sample prior year return
└── backend/
    ├── __init__.py
    ├── api.py                    # FastAPI endpoints
    ├── parser.py                 # Excel parser (3-strategy auto-detection)
    ├── aligner.py                # Fuzzy tab and row matching
    ├── calculator.py             # Movements, z-scores, priority tiers
    ├── ccr.py                    # CCR checks + working file cross-check
    ├── commentary.py             # Parallel AI commentary (5 concurrent calls)
    ├── exporter.py               # Excel export with live formulas
    ├── ca1_parser.py             # HKRBC capital extraction
    └── summary.py                # Executive memo + Deloitte branded PDF
```

---

## AI Model & Technology Stack

| Component | Technology |
|---|---|
| AI Model | Kimi-K2.5 via Deloitte Nova (`nova.deloitte.com.cn`) |
| Backend | FastAPI + uvicorn (Python) |
| Frontend | Streamlit |
| Excel parsing | openpyxl |
| Fuzzy matching | rapidfuzz |
| PDF generation | fpdf2 |
| Charts | Plotly |
| HTTP client | httpx (async streaming) |

**AI is used for:**
- Generating reviewer exception notes for High-priority movements
- Writing HKRBC capital adequacy commentary
- Drafting the 4-section executive summary memo
- Generating AI remarks in the Excel export

All AI calls use parallel execution (`ThreadPoolExecutor`, 5 workers) for ~5x speedup vs sequential calls.

---

## Business Value

| Manual process | With Smart Regulatory Reviewer |
|---|---|
| 2–3 days to compare two returns | Under 5 minutes for full analysis |
| Manual Excel VLOOKUP across 35 tabs | Automatic fuzzy matching + alignment |
| Reviewer writes exception notes by hand | AI drafts notes instantly, reviewer validates |
| Capital ratios calculated in separate spreadsheet | Extracted automatically from CA.1, computed from first principles |
| PDF memo written in Word | One-click branded PDF generation |

---

## Troubleshooting

**"No module named uvicorn" or "No module named streamlit"**
Your virtual environment is not activated or packages are not installed. Run:
```cmd
.venv\Scripts\activate
pip install -r requirements.txt
```

**"Backend offline" error in the app**
The API server is not running. Start it manually (Option C above) and check for error messages.

**"LLM unavailable" in commentary**
Check your `.env` file — the API key or base URL may be incorrect.

**Ports already in use**
If ports 8001 or 8501 are taken by another process, stop the conflicting process or change the port numbers in `start.py` and `app.py` (`BACKEND_URL`).

---

## Data Privacy

All data used in this tool must be synthetic, anonymised, or publicly available.
Do not upload real client data or sensitive proprietary information.
The `.env` file (containing API keys) is excluded from version control via `.gitignore`.

---

*Smart Regulatory Reviewer · Deloitte DAIS AI Hackathon 2026 · AI-assisted, not for regulatory submission*
"""
backend/commentary.py
---------------------
Generates AI reviewer notes via Kimi-K2.5.
Uses ThreadPoolExecutor to call Kimi in parallel — up to 5 concurrent requests.
"""

import httpx, json, os, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

BASE_URL    = os.getenv("LLM_BASE_URL", "https://nova.deloitte.com.cn/del/v1")
API_KEY     = os.getenv("LLM_API_KEY", "")
MODEL       = os.getenv("LLM_MODEL", "Kimi-K2.5")
MAX_WORKERS = 5   # parallel Kimi calls — raise to 8 if endpoint allows it

SYSTEM_PROMPT = """
You are a senior actuary writing exception notes for HKIA FCA regulatory return reviews.
Rules:
- Write 2-3 plain English sentences maximum.
- Never use LaTeX, dollar signs, asterisks, markdown, or mathematical notation.
- Never write currency as $HK or HK$. Write HKD instead.
- Use commas for thousands: write 45,273,621 not 45273621.
- Reference specific account names and codes.
- Do not use generic phrases like 'significant change observed'.
- State whether further investigation is needed.
- Professional, direct, actuarial tone.
"""


def _clean(text: str) -> str:
    text = re.sub(r'\$+', '', text)
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\(?=[A-Za-z])', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _call_one(item: dict) -> dict:
    """Call Kimi for a single exception item. Returns item with 'commentary' set."""
    pct     = item.get("pct_change")
    abs_mov = item.get("abs_movement")
    cy_v    = item.get("cy_value") or 0
    py_v    = item.get("py_value") or 0

    pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
    abs_str = f"{abs_mov:,.0f}" if abs_mov is not None else "N/A"

    user_msg = (
        f"Tab: {item.get('tab', 'Unknown')}\n"
        f"Account: {item.get('description', 'Unknown')} ({item.get('cy_code', '')})\n"
        f"CY (YE25): HKD {cy_v:,.0f}\n"
        f"PY (YE24): HKD {py_v:,.0f}\n"
        f"Movement: HKD {abs_str} ({pct_str})\n"
        f"Priority: {item.get('priority')}\n\n"
        "Write a plain English reviewer note. "
        "No LaTeX, no dollar signs, no markdown. Use HKD for currency."
    )

    url = BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        "max_tokens": 200,
        "stream": True,
    }

    collected = []
    try:
        with httpx.Client(verify=False, timeout=120) as client:
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
        item["commentary"] = _clean(result) if result else "[No commentary returned]"
    except Exception as e:
        item["commentary"] = f"[Commentary unavailable: {e}]"

    return item


def generate_commentary(exceptions: list) -> list:
    """
    Generate reviewer notes for up to 20 High-priority exceptions.
    Calls Kimi in parallel (up to MAX_WORKERS concurrent requests).
    """
    batch = exceptions[:20]
    if not batch:
        return []

    results = [None] * len(batch)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(_call_one, dict(item)): i
            for i, item in enumerate(batch)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                item = dict(batch[idx])
                item["commentary"] = f"[Commentary unavailable: {e}]"
                results[idx] = item

    return [r for r in results if r is not None]
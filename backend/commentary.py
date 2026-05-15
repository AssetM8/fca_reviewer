"""
backend/commentary.py  —  AI reviewer notes via Kimi-K2.5
"""

import httpx, json, os, re
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL", "https://nova.deloitte.com.cn/del/v1")
API_KEY  = os.getenv("LLM_API_KEY", "")
MODEL    = os.getenv("LLM_MODEL", "Kimi-K2.5")

SYSTEM_PROMPT = """
You are a senior actuary writing exception notes for HKIA FCA regulatory return reviews.
Rules:
- Write 2-3 plain English sentences maximum.
- Never use LaTeX, dollar signs, asterisks, markdown, or mathematical notation.
- Never write currency as $HK or HK$ or with dollar signs. Write HKD instead.
- Use commas for thousands: write 45,273,621 not 45273621.
- Reference specific account names and codes.
- Do not use generic phrases like "significant change observed".
- State whether further investigation is needed.
- Professional, direct, actuarial tone.
"""


def _clean(text: str) -> str:
    """Remove LaTeX artifacts and formatting noise Kimi sometimes produces."""
    # Remove LaTeX math delimiters
    text = re.sub(r'\$+', '', text)
    # Remove \text{}, \mathrm{} etc
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    # Remove stray backslashes
    text = re.sub(r'\\(?=[A-Za-z])', '', text)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _stream(system: str, user: str, max_tokens: int = 200) -> str:
    url = BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens,
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
        return _clean(result) if result else "[No commentary returned]"
    except Exception as e:
        return f"[Commentary unavailable: {e}]"


def generate_commentary(exceptions: list) -> list:
    results = []
    for item in exceptions[:20]:
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
            "Write a plain English reviewer note for this exception. "
            "No LaTeX, no dollar signs, no markdown. Use HKD for currency."
        )

        item["commentary"] = _stream(SYSTEM_PROMPT, user_msg)
        results.append(item)
    return results
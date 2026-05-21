"""
backend/parser.py
-----------------
Reads an FCA Excel workbook and converts every sheet into a DataFrame.

Three sheet structures are handled:

  Strategy A — Code-prefix rows  (F.1 EBS, CA.1, etc.)
    Col 0: account code like "I.C.", "II.B3.", "CA."
    Col 1: primary numeric value
    Detection: col 0 starts with KNOWN_PREFIXES

  Strategy B — CA-style label rows  (CA.1, some CA sub-tabs)
    Col 0: empty
    Col 1: plain text label
    Col 2: numeric value
    Detection: col 0 empty, col 1 text, col 2 numeric

  Strategy C — Multi-column description sheets  (F.3 AOM, F.LT.x, etc.)
    Col 0: plain text label (no code prefix)
    Cols 1..N: numeric values for different sub-portfolios
    A header row contains column labels; one of them says "Total"
    Detection: fallback when A and B fail
    Value used: the "Total" column if found, else last numeric col in row
"""

import openpyxl
import pandas as pd
import re
from typing import Dict, Optional, Tuple

KNOWN_PREFIXES = (
    "I.", "II.", "III.", "IV.", "V.",
    "F.", "CA.", "LT.", "GB.", "IL.", "RE.",
)

# Rows whose col-0 text exactly matches these are skipped (header/metadata)
SKIP_LABELS = {
    "column 1", "column 2", "column 3", "column 4", "column 5",
    "column 6", "column 7", "column 8", "column 9", "column 10",
    "description", "item", "name of insurer", "valuation date",
    "reporting period", "unit:", "(unit:", "as at end", "net asset value",
    "lines of business classification",
    "check (unexplained)", "check", "commentaries", "add row", "delete row",
    "clear worksheet",
}


def _to_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        import math
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _is_numeric_cell(val) -> bool:
    return _to_float(val) is not None


def _strategy_a_header(rows: list) -> Optional[int]:
    """Return the row index where col-0 first starts with a known prefix."""
    for i, row in enumerate(rows):
        if row and row[0] and str(row[0]).strip().startswith(KNOWN_PREFIXES):
            return i
    return None


def _strategy_b_header(rows: list) -> Optional[int]:
    """
    Return the row index where col-0 is empty, col-1 is text, col-2 is numeric.
    Used for CA-style sheets.
    """
    for i, row in enumerate(rows):
        if not row or len(row) < 3:
            continue
        if (row[0] is None or str(row[0]).strip() == "") and \
           row[1] is not None and len(str(row[1]).strip()) > 3 and \
           _is_numeric_cell(row[2]):
            return i
    return None


def _find_total_col(rows: list, header_row: int) -> Optional[int]:
    """
    Search ALL rows from 0 up to the first data row for a column header
    containing 'total'. Real HKIA templates have metadata rows (Name of
    Insurer, Valuation Date, Column 1/2/3/4/5...) well above the data.
    Returns 0-based column index, or None.
    """
    # Search all rows up to (and slightly past) the data start
    search_rows = rows[:header_row + 4]
    # First pass: look for exact "total" column header
    for row in reversed(search_rows):   # reversed: nearest header wins
        if not row:
            continue
        for ci, cell in enumerate(row):
            if cell is None:
                continue
            label = str(cell).strip().lower()
            if label == "total" and ci > 0:
                return ci
    # Second pass: look for "total" anywhere in cell text
    for row in reversed(search_rows):
        if not row:
            continue
        for ci, cell in enumerate(row):
            if cell is None:
                continue
            label = str(cell).strip().lower()
            if "total" in label and ci > 0 and len(label) < 30:
                return ci
    # Fallback: return the rightmost column that has numeric values
    # in the first few data rows
    data_rows = [r for r in rows[header_row:header_row+5] if r]
    for ci in range(min(10, max(len(r) for r in data_rows) if data_rows else 1) - 1,
                    0, -1):
        if any(_is_numeric_cell(r[ci]) for r in data_rows if len(r) > ci):
            return ci
    return None


def _best_value_in_row(row: list, prefer_col: Optional[int], label_col: int) -> Tuple[Optional[float], int]:
    """
    Pick the best numeric value from a data row.
    Priority: prefer_col (Total column) → rightmost numeric col → None
    Returns (value, col_index).
    """
    if prefer_col is not None and len(row) > prefer_col:
        v = _to_float(row[prefer_col])
        if v is not None:
            return v, prefer_col

    # Scan right-to-left for the last non-None numeric value
    for ci in range(min(len(row)-1, 15), label_col, -1):
        v = _to_float(row[ci])
        if v is not None:
            return v, ci

    return None, -1


# Additional metadata labels to skip in Strategy C
METADATA_PATTERNS = re.compile(
    r"^(name of insurer|valuation date|reporting period|unit:|clear worksheet|add row|delete row|commentaries|lines of business)",
    re.I
)

def _strategy_c_parse(rows: list) -> Optional[pd.DataFrame]:
    """
    Multi-column description sheet parser for HKIA FCA templates.

    Real HKIA sheets have a structure like:
      Row 0:  Sheet title ("F.3 Analysis of net asset value movement")
      Row 1:  "Name of Insurer:" | <value>
      Row 2:  "Valuation Date:"  | <value>
      Row 3:  "Reporting Period:"| <value>
      Row 4:  "(Unit: in HKD thousands)"
      Row 5:  "Column 1" | "Column 2" | ... | "Column 5 (Total)" | ...
      Row 6:  Sub-header labels (Long Term Business | GI Business | ... | Total)
      Row 7+: Data rows ("Opening balance", "Exchange rate impact", ...)

    Strategy:
    1. Scan forward to find the first NUMERIC data row (skipping metadata)
    2. From all rows before the data, find which column is labelled "Total"
    3. Parse all data rows using that column as the primary value
    """

    def _skip_row(label: str) -> bool:
        label_lower = label.lower().strip()
        if any(label_lower == s for s in SKIP_LABELS):
            return True
        if METADATA_PATTERNS.match(label_lower):
            return True
        return False

    # Find the first data row (has text label + numeric value in cols 1-15)
    first_data_row = None
    for i, row in enumerate(rows):
        if not row or row[0] is None:
            continue
        label = str(row[0]).strip()
        if not label or len(label) < 2:
            continue
        if _skip_row(label):
            continue
        has_num = any(_is_numeric_cell(row[ci])
                      for ci in range(1, min(len(row), 16)))
        if has_num:
            first_data_row = i
            break

    if first_data_row is None:
        # No rows with numeric values — try including rows without values
        for i, row in enumerate(rows):
            if not row or row[0] is None:
                continue
            label = str(row[0]).strip()
            if not label or len(label) < 2:
                continue
            if not _skip_row(label):
                first_data_row = i
                break

    if first_data_row is None:
        return None

    # Find the Total column by scanning all header rows above the data
    total_col = _find_total_col(rows, first_data_row)

    data = []
    for i, row in enumerate(rows[first_data_row:], start=first_data_row):
        if not row or row[0] is None:
            continue
        label = str(row[0]).strip()
        if not label or len(label) < 2:
            continue
        if _skip_row(label):
            continue

        value, _ = _best_value_in_row(row, total_col, 0)

        data.append({
            "row_num":     i,
            "code":        label[:60],
            "description": label,
            "value":       value,
        })

    if not data:
        return None

    df = pd.DataFrame(data)
    # Deduplicate codes (same label appears in multiple rows)
    if df["code"].duplicated().any():
        mask = df["code"].duplicated(keep=False)
        df.loc[mask, "code"] = df.loc[mask].apply(
            lambda r: f"{r['code']}_{r['row_num']}", axis=1
        )
    return df.set_index("code")


def parse_fca_file(filepath: str) -> Dict[str, pd.DataFrame]:
    wb = openpyxl.load_workbook(filepath, data_only=True)
    result: Dict[str, pd.DataFrame] = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.values)
        if not rows:
            continue

        df: Optional[pd.DataFrame] = None

        # ── Strategy A: code-prefix rows ──────────────────────────────────
        # Require >= 3 prefix rows to avoid title rows like "F.3 Analysis..."
        # being falsely matched by the "F." prefix
        prefix_count = sum(1 for row in rows
                           if row and row[0] and
                           str(row[0]).strip().startswith(KNOWN_PREFIXES))
        a_start = _strategy_a_header(rows) if prefix_count >= 3 else None
        if a_start is not None:
            label_col, value_col = 0, 1
            # Check if labels actually start with prefixes (vs col-B style)
            data = []
            for i, row in enumerate(rows[a_start:], start=a_start):
                if not row or len(row) <= label_col or row[label_col] is None:
                    continue
                raw = str(row[label_col]).strip()
                if not raw or not raw.startswith(KNOWN_PREFIXES):
                    continue
                parts = raw.split(None, 1)
                code  = parts[0]
                desc  = parts[1] if len(parts) > 1 else code
                val   = row[value_col] if len(row) > value_col else None
                data.append({"row_num": i, "code": code,
                              "description": desc, "value": val})
            if data:
                df = pd.DataFrame(data)
                if df["code"].duplicated().any():
                    mask = df["code"].duplicated(keep=False)
                    df.loc[mask, "code"] = df.loc[mask].apply(
                        lambda r: f"{r['code']}_{r['row_num']}", axis=1)
                df = df.set_index("code")

        # ── Strategy B: CA-style (label in col 1, value in col 2) ─────────
        if df is None or df.empty:
            # Count how many B-style rows exist
            b_count = sum(1 for row in rows
                          if row and len(row) >= 3
                          and (row[0] is None or str(row[0]).strip() == "")
                          and row[1] is not None
                          and _is_numeric_cell(row[2]))
            b_start = _strategy_b_header(rows) if b_count >= 2 else None
            if b_start is not None:
                data = []
                for i, row in enumerate(rows[b_start:], start=b_start):
                    if not row or len(row) < 2 or row[1] is None:
                        continue
                    label = str(row[1]).strip()
                    if not label or label.lower() in SKIP_LABELS:
                        continue
                    val = _to_float(row[2]) if len(row) > 2 else None
                    data.append({"row_num": i, "code": label[:60],
                                 "description": label, "value": val})
                if data:
                    df = pd.DataFrame(data)
                    if df["code"].duplicated().any():
                        mask = df["code"].duplicated(keep=False)
                        df.loc[mask, "code"] = df.loc[mask].apply(
                            lambda r: f"{r['code']}_{r['row_num']}", axis=1)
                    df = df.set_index("code")

        # ── Strategy C: multi-column description sheet ─────────────────────
        if df is None or df.empty:
            df = _strategy_c_parse(rows)

        if df is not None and not df.empty:
            result[sheet_name] = df

    return result
"""
backend/parser.py
-----------------
Reads an FCA Excel workbook and converts every sheet into a DataFrame.

Auto-detects whether labels are in Col0 (F.1 EBS style) or Col1 (CA.1 style).
"""

import openpyxl
import pandas as pd
from typing import Dict

KNOWN_PREFIXES = (
    "I.", "II.", "III.", "IV.", "V.",
    "F.", "CA.", "LT.", "GB.", "IL.", "RE.",
)


def _find_data_start(rows: list) -> tuple:
    """
    Returns (header_row_idx, label_col, value_col).
    Tries Col0 first (F.1 EBS style), then Col1 (CA.1 style).
    """
    # Strategy 1: Col0 has known code prefixes
    for i, row in enumerate(rows):
        if row and row[0] and str(row[0]).strip().startswith(KNOWN_PREFIXES):
            return i, 0, 1

    # Strategy 2: Col0 empty, Col1 has text labels with numeric value in Col2
    # Used by CA.1 CA Summary and similar sheets
    for i, row in enumerate(rows):
        if not row or len(row) < 3:
            continue
        col0_empty = row[0] is None or str(row[0]).strip() == ""
        col1_text  = row[1] is not None and len(str(row[1]).strip()) > 3
        col2_num   = row[2] is not None
        if col0_empty and col1_text and col2_num:
            try:
                float(row[2])
                return i, 1, 2   # labels in col1, values in col2
            except (TypeError, ValueError):
                continue

    return 0, 0, 1   # fallback


def parse_fca_file(filepath: str) -> Dict[str, pd.DataFrame]:
    wb = openpyxl.load_workbook(filepath, data_only=True)
    result: Dict[str, pd.DataFrame] = {}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.values)
        if not rows:
            continue

        header_row, label_col, value_col = _find_data_start(rows)
        desc_col = value_col + 1   # description one column after value (best effort)

        data = []
        for i, row in enumerate(rows[header_row:], start=header_row):
            if not row or len(row) <= label_col or row[label_col] is None:
                continue

            raw_label = str(row[label_col]).strip()
            if not raw_label:
                continue

            # For Col0-style sheets: only keep rows starting with known prefixes
            if label_col == 0 and not raw_label.startswith(KNOWN_PREFIXES):
                continue

            # For Col1-style sheets: skip obvious header/metadata rows
            if label_col == 1:
                low = raw_label.lower()
                if any(skip in low for skip in [
                    "column", "unit:", "name of", "valuation", "reporting period",
                    "as at end", "tier 1", "tier 2", "diversified", "rca after",
                ]):
                    continue

            # Split "I.C. Cash and cash equivalents" → code="I.C.", desc="Cash..."
            if label_col == 0:
                parts       = raw_label.split(None, 1)
                short_code  = parts[0]
                description = parts[1] if len(parts) > 1 else short_code
            else:
                short_code  = raw_label[:40]   # full label text as code
                description = raw_label

            value = row[value_col] if len(row) > value_col else None

            data.append({
                "row_num":     i,
                "code":        short_code,
                "description": description,
                "value":       value,
            })

        if data:
            df = pd.DataFrame(data)
            # Deduplicate codes
            if df["code"].duplicated().any():
                mask = df["code"].duplicated(keep=False)
                df.loc[mask, "code"] = df.loc[mask].apply(
                    lambda r: f"{r['code']}_{r['row_num']}", axis=1
                )
            result[sheet_name] = df.set_index("code")

    return result
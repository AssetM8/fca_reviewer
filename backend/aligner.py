"""
backend/aligner.py
------------------
Matches tabs and rows between CY and PY files using exact then fuzzy matching.
Handles duplicate row codes by taking the first occurrence.
"""

from rapidfuzz import fuzz, process
import pandas as pd
from typing import Dict, Optional


# ---------------------------------------------------------------
# !! CHANGE THIS if matching is too strict or too loose !!
#   90  = very strict
#   85  = balanced (default)
#   75  = permissive
# ---------------------------------------------------------------
CONFIDENCE_THRESHOLD = 85


def _scalar(val):
    """If val is a Series (caused by duplicate index), return first element."""
    if isinstance(val, pd.Series):
        return val.iloc[0] if len(val) > 0 else None
    return val


def align_tabs(cy_tabs: Dict, py_tabs: Dict) -> Dict[str, dict]:
    alignment: Dict[str, dict] = {}
    py_names = list(py_tabs.keys())

    for cy_name in cy_tabs.keys():
        result = process.extractOne(
            cy_name, py_names, scorer=fuzz.token_sort_ratio
        )
        if result:
            match, score, _ = result
            alignment[cy_name] = {
                "py_tab": match,
                "score":  score,
                "status": (
                    "exact"     if score == 100
                    else "fuzzy"     if score >= CONFIDENCE_THRESHOLD
                    else "unmatched"
                ),
            }
        else:
            alignment[cy_name] = {"py_tab": None, "score": 0, "status": "unmatched"}

    return alignment


def align_rows(cy_df: pd.DataFrame, py_df: pd.DataFrame) -> pd.DataFrame:
    # De-duplicate: if same code appears twice, keep first occurrence
    cy_df = cy_df[~cy_df.index.duplicated(keep="first")]
    py_df = py_df[~py_df.index.duplicated(keep="first")]

    cy_labels = cy_df.index.tolist()
    py_labels = py_df.index.tolist()
    matched_rows = []

    for cy_code in cy_labels:
        if cy_code in py_labels:
            matched_rows.append({
                "cy_code":      cy_code,
                "py_code":      cy_code,
                "cy_value":     _scalar(cy_df.loc[cy_code, "value"]),
                "py_value":     _scalar(py_df.loc[cy_code, "value"]),
                "description":  _scalar(cy_df.loc[cy_code, "description"]),
                "match_score":  100,
                "match_status": "exact",
                "row_num":      _scalar(cy_df.loc[cy_code, "row_num"]) if "row_num" in cy_df.columns else 9999,
            })
        else:
            cy_desc  = _scalar(cy_df.loc[cy_code, "description"])
            py_descs = py_df["description"].tolist()

            result: Optional[tuple] = (
                process.extractOne(str(cy_desc), [str(d) for d in py_descs],
                                   scorer=fuzz.token_sort_ratio)
                if py_descs and cy_desc is not None else None
            )

            if result and result[1] >= CONFIDENCE_THRESHOLD:
                best_desc = result[0]
                # Find the py_code matching this description
                matches = py_df[py_df["description"].astype(str) == best_desc]
                if len(matches) > 0:
                    py_code = matches.index[0]
                    matched_rows.append({
                        "cy_code":      cy_code,
                        "py_code":      py_code,
                        "cy_value":     _scalar(cy_df.loc[cy_code, "value"]),
                        "py_value":     _scalar(py_df.loc[py_code, "value"]),
                        "description":  cy_desc,
                        "match_score":  result[1],
                        "match_status": "fuzzy",
                        "row_num":      _scalar(cy_df.loc[cy_code, "row_num"]) if "row_num" in cy_df.columns else 9999,
                    })
                    continue

            matched_rows.append({
                "cy_code":      cy_code,
                "py_code":      None,
                "cy_value":     _scalar(cy_df.loc[cy_code, "value"]),
                "py_value":     None,
                "description":  cy_desc,
                "match_score":  0,
                "match_status": "new_in_cy",
                "row_num":      _scalar(cy_df.loc[cy_code, "row_num"]) if "row_num" in cy_df.columns else 9999,
            })

    matched_py = {r["py_code"] for r in matched_rows if r["py_code"]}
    for py_code in py_labels:
        if py_code not in matched_py:
            matched_rows.append({
                "cy_code":      None,
                "py_code":      py_code,
                "cy_value":     None,
                "py_value":     _scalar(py_df.loc[py_code, "value"]),
                "description":  _scalar(py_df.loc[py_code, "description"]),
                "match_score":  0,
                "match_status": "missing_in_cy",
            })

    return pd.DataFrame(matched_rows)
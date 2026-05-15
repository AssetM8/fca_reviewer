"""
backend/calculator.py
---------------------
Computes YoY movements, materiality, z-scores, and priority tiers
for every matched row produced by aligner.py.

Nothing in this file needs to be changed for standard use.
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------
# !! CHANGE THESE THRESHOLDS if you want different priority rules !!
# Materiality is expressed as % of the total absolute value on the sheet.
# ---------------------------------------------------------------
MATERIALITY_HIGH   = 15.0   # % → High priority
MATERIALITY_MEDIUM =  5.0   # % → Medium priority
ZSCORE_HIGH        =  3.0   # standard deviations → High
ZSCORE_MEDIUM      =  2.0   # standard deviations → Medium


def compute_movements(aligned_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds to *aligned_df*:
        abs_movement   – CY minus PY
        pct_change     – % change vs PY (NaN when PY is zero)
        materiality_pct – |CY value| as % of sheet total
        z_score        – z-score of pct_change across the sheet
        priority       – "High" | "Medium" | "Low"

    Returns rows sorted by materiality_pct descending.
    """
    df = aligned_df.copy()

    df["cy_value"] = pd.to_numeric(df["cy_value"], errors="coerce")
    df["py_value"] = pd.to_numeric(df["py_value"], errors="coerce")

    # Basic movements
    df["abs_movement"] = df["cy_value"] - df["py_value"]
    df["pct_change"] = np.where(
        df["py_value"].abs() > 0,
        (df["abs_movement"] / df["py_value"].abs()) * 100,
        np.nan,
    )

    # Materiality as % of sheet total
    total = df["cy_value"].abs().sum()
    df["materiality_pct"] = (
        (df["cy_value"].abs() / total * 100).fillna(0) if total > 0 else 0.0
    )

    # Z-score of % changes (helps detect anomalies relative to the sheet)
    pct = df["pct_change"].dropna()
    df["z_score"] = np.nan
    if len(pct) > 1 and pct.std() != 0:
        df.loc[pct.index, "z_score"] = (pct - pct.mean()) / pct.std()

    # Priority tiering
    df["priority"] = "Low"
    df.loc[
        (df["materiality_pct"] > MATERIALITY_MEDIUM) | (df["z_score"].abs() > ZSCORE_MEDIUM),
        "priority",
    ] = "Medium"
    df.loc[
        (df["materiality_pct"] > MATERIALITY_HIGH) | (df["z_score"].abs() > ZSCORE_HIGH),
        "priority",
    ] = "High"
    # Structural changes always get High regardless of size
    df.loc[df["match_status"].isin(["new_in_cy", "missing_in_cy"]), "priority"] = "High"

    return df.sort_values("materiality_pct", ascending=False).reset_index(drop=True)
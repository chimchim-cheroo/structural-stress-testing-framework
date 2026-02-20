import os
import numpy as np
import pandas as pd


def _norm_cols(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def layer_reconcile(excel_layers_csv: str, python_layer_trace_csv: str, out_dir: str):
    xl = _norm_cols(pd.read_csv(excel_layers_csv))
    py = _norm_cols(pd.read_csv(python_layer_trace_csv))

    # If multiple sims exist in python trace, take sim==0 by default
    if "sim" in py.columns:
        py = py[py["sim"] == 0].copy()

    if "month" not in xl.columns or "month" not in py.columns:
        raise ValueError("Both Excel and Python layer files must include 'month' column.")

    # Find common metrics (exclude identifiers)
    id_cols = {"month", "sim"}
    common = [c for c in xl.columns if c in py.columns and c not in id_cols]

    rows = []
    merged = xl.merge(py, on="month", how="outer", suffixes=("_excel", "_python"))

    for m in common:
        a = merged[f"{m}_excel"].astype(float)
        b = merged[f"{m}_python"].astype(float)
        diff = b - a
        diff_pct = np.where(a != 0, diff / a, np.nan)

        tmp = pd.DataFrame({
            "month": merged["month"],
            "metric": m,
            "excel_value": a,
            "python_value": b,
            "diff": diff,
            "diff_pct": diff_pct,
        })
        rows.append(tmp)

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "recon_layers.csv")
    out.to_csv(out_path, index=False)
    return out_path

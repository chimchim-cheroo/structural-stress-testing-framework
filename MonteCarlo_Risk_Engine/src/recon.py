import os
import json
import numpy as np
import pandas as pd


def _safe_float(x):
    try:
        if x is None:
            return np.nan
        if isinstance(x, str):
            x = x.replace(",", "").replace("$", "").strip()
        return float(x)
    except Exception:
        return np.nan


def _compute_python_kpis(df_mc: pd.DataFrame):
    x = df_mc["total_net_income"].to_numpy()
    return {
        "expected_total_net_income": float(np.mean(x)),
        "p5_total_net_income": float(np.percentile(x, 5)),
        "probability_of_loss": float(np.mean(x < 0)),
    }


def _read_excel_kpis(excel_kpi_path: str):
    """
    Expected format (CSV):
      kpi, value
      expected_total_net_income, 123
      p5_total_net_income, -456
      probability_of_loss, 0.37
    """
    df = pd.read_csv(excel_kpi_path)
    if "kpi" not in df.columns or "value" not in df.columns:
        raise ValueError("Excel KPI CSV must have columns: kpi, value")

    out = {}
    for _, r in df.iterrows():
        k = str(r["kpi"]).strip()
        v = _safe_float(r["value"])
        out[k] = v
    return out


def reconcile_kpis(excel_kpi_path: str, mc_results_path: str, out_dir: str):
    df_mc = pd.read_csv(mc_results_path)

    py = _compute_python_kpis(df_mc)
    xl = _read_excel_kpis(excel_kpi_path)

    all_kpis = sorted(set(py.keys()) | set(xl.keys()))

    rows = []
    for k in all_kpis:
        py_v = py.get(k, np.nan)
        xl_v = xl.get(k, np.nan)
        diff = py_v - xl_v
        diff_pct = np.nan
        if np.isfinite(xl_v) and xl_v != 0:
            diff_pct = diff / xl_v

        rows.append({
            "kpi": k,
            "excel_value": xl_v,
            "python_value": py_v,
            "diff": diff,
            "diff_pct": diff_pct,
        })

    df_recon = pd.DataFrame(rows)

    os.makedirs(out_dir, exist_ok=True)
    df_recon.to_csv(os.path.join(out_dir, "recon_kpi.csv"), index=False)

    payload = {
        "excel_kpi_path": excel_kpi_path,
        "mc_results_path": mc_results_path,
        "python_kpis": py,
        "excel_kpis": xl,
        "recon_table": rows,
    }
    with open(os.path.join(out_dir, "recon_kpi.json"), "w") as f:
        json.dump(payload, f, indent=2)

    return df_recon

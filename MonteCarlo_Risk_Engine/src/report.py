import os
import json
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def make_run_dir(base_dir="outputs"):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(base_dir, run_id)
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    return run_id, out_dir, fig_dir


def summarize(df_res: pd.DataFrame):
    x = df_res["total_net_income"].to_numpy()
    mean_income = float(np.mean(x))
    p5_income = float(np.percentile(x, 5))
    loss_prob = float(np.mean(x < 0))
    return mean_income, p5_income, loss_prob


def _pick_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def export_all(cfg: dict, df_res: pd.DataFrame, out_dir: str, fig_dir: str):
    mean_income, p5_income, loss_prob = summarize(df_res)

    # --- Save results ---
    df_res.to_csv(os.path.join(out_dir, "mc_results.csv"), index=False)

    # --- Save config snapshot + summary ---
    snapshot = dict(cfg)
    snapshot["results_summary"] = {
        "expected_total_net_income": mean_income,
        "p5_total_net_income": p5_income,
        "probability_of_loss": loss_prob,
    }

    with open(os.path.join(out_dir, "config_snapshot.json"), "w") as f:
        json.dump(snapshot, f, indent=2)

    # --- Figures ---
    x = df_res["total_net_income"].to_numpy()

    # 1) Distribution
    plt.figure()
    plt.hist(x, bins=50)
    plt.axvline(mean_income)
    plt.axvline(p5_income)
    plt.title("Distribution of Total Net Income")
    plt.xlabel("Total Net Income")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "dist_total_net_income.png"), dpi=200)
    plt.close()

    # 2) Tail view (ordered)
    xs = np.sort(x)
    plt.figure()
    plt.plot(xs)
    plt.axhline(p5_income)
    plt.title("Ordered Total Net Income (Tail View)")
    plt.xlabel("Simulation Rank")
    plt.ylabel("Total Net Income")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "tail_total_net_income.png"), dpi=200)
    plt.close()

    # 3) Sensitivity (correlation) — column-compatible
    col_default = _pick_col(df_res, ["default_rate_annual", "default_rate"])
    col_lgd = _pick_col(df_res, ["lgd"])
    col_margin = _pick_col(df_res, ["margin_shock"])

    sens_map = {}
    if col_default:
        sens_map["Default Rate"] = df_res["total_net_income"].corr(df_res[col_default])
    if col_lgd:
        sens_map["LGD"] = df_res["total_net_income"].corr(df_res[col_lgd])
    if col_margin:
        sens_map["Margin Shock"] = df_res["total_net_income"].corr(df_res[col_margin])

    if sens_map:
        sens = pd.Series(sens_map)
        plt.figure()
        sens.plot(kind="bar")
        plt.title("Sensitivity (Correlation)")
        plt.ylabel("Correlation with Net Income")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, "sensitivity_corr.png"), dpi=200)
        plt.close()

    return mean_income, p5_income, loss_prob


import os
import json
import time
import pathlib

import yaml
import pandas as pd
import matplotlib.pyplot as plt

from src.engine import run_mc
from src.reporting import generate_pdf_report


def _now_run_id():
    return time.strftime("%Y%m%d_%H%M%S")


def _save_config_snapshot(cfg, out_dir):
    snap = os.path.join(out_dir, "config_snapshot.json")
    with open(snap, "w") as f:
        json.dump(cfg, f, indent=2)


def _equity_capital(cfg):
    notional = float(cfg.get("portfolio", {}).get("notional", 0) or 0)
    funding_ratio = float(cfg.get("funding", {}).get("funding_ratio", 0.8))
    if notional <= 0:
        return None
    return notional * (1.0 - funding_ratio)


def _make_figures(out_dir: str, df: pd.DataFrame, cfg: dict):
    """
    Always generates:
      - figures/ni_distribution.png
      - figures/equity_return_distribution.png  (if equity_capital available)
      - figures/tail_total_net_income.png
      - figures/sensitivity_corr.png           (simple bar chart of correlations)
      - figures/credit_vs_liquidity_scatter.png (if credit_loss & liquidity_loss exist)
      - figures/tail_decomposition.csv          (if credit_loss & liquidity_loss exist)
    """
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    # --- NI distribution ---
    plt.figure()
    plt.hist(df["total_net_income"], bins=60)
    plt.title("Total Net Income Distribution")
    plt.xlabel("Total Net Income")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "ni_distribution.png"), dpi=200)
    plt.close()

    # --- Tail NI distribution (worst 5%) ---
    q05 = df["total_net_income"].quantile(0.05)
    tail = df[df["total_net_income"] <= q05].copy()
    plt.figure()
    plt.hist(tail["total_net_income"], bins=40)
    plt.title("Tail Total Net Income (Worst 5%)")
    plt.xlabel("Total Net Income")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "tail_total_net_income.png"), dpi=200)
    plt.close()

    # --- Equity return distribution ---
    eq_cap = _equity_capital(cfg)
    if eq_cap and eq_cap > 0:
        eq_ret = df["total_net_income"] / eq_cap
        plt.figure()
        plt.hist(eq_ret, bins=60)
        plt.title("Equity Return Distribution")
        plt.xlabel("Equity Return")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, "equity_return_distribution.png"), dpi=200)
        plt.close()

    # --- Sensitivity (correlation bar chart) ---
    candidates = ["default_rate","lgd","margin_shock","Z_sys","credit_loss","liquidity_loss"]
    cols = [c for c in candidates if c in df.columns]
    if cols:
        corr = {c: float(df["total_net_income"].corr(df[c])) for c in cols}
        s = pd.Series(corr).sort_values()
        plt.figure()
        plt.bar(s.index, s.values)
        plt.title("Sensitivity (Corr with Total Net Income)")
        plt.ylabel("Correlation")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, "sensitivity_corr.png"), dpi=200)
        plt.close()

    # --- Tail decomposition + credit vs liquidity scatter ---
    if ("credit_loss" in df.columns) and ("liquidity_loss" in df.columns):
        rows = []
        for scope_name, d in [("ALL", df), ("TAIL_WORST_5PCT", tail)]:
            rows.append({
                "scope": scope_name,
                "n": int(len(d)),
                "ni_mean": float(d["total_net_income"].mean()),
                "ni_p5": float(d["total_net_income"].quantile(0.05)),
                "ni_min": float(d["total_net_income"].min()),
                "credit_mean": float(d["credit_loss"].mean()),
                "credit_p95": float(d["credit_loss"].quantile(0.95)),
                "credit_max": float(d["credit_loss"].max()),
                "p_credit_gt_0": float((d["credit_loss"] > 0).mean()),
                "liq_mean": float(d["liquidity_loss"].mean()),
                "liq_p95": float(d["liquidity_loss"].quantile(0.95)),
                "liq_max": float(d["liquidity_loss"].max()),
                "p_liq_gt_0": float((d["liquidity_loss"] > 0).mean()),
            })
        pd.DataFrame(rows).to_csv(os.path.join(fig_dir, "tail_decomposition.csv"), index=False)

        plt.figure()
        mask_tail = df["total_net_income"] <= q05
        plt.scatter(df.loc[~mask_tail, "credit_loss"], df.loc[~mask_tail, "liquidity_loss"], s=10)
        plt.scatter(df.loc[mask_tail, "credit_loss"], df.loc[mask_tail, "liquidity_loss"], s=18)
        plt.title("Credit Loss vs Liquidity Loss (Tail Highlighted)")
        plt.xlabel("credit_loss")
        plt.ylabel("liquidity_loss")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, "credit_vs_liquidity_scatter.png"), dpi=200)
        plt.close()


def main():
    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    rid = _now_run_id()
    out_dir = os.path.join("outputs", rid)
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)

    df = run_mc(cfg)
    df.to_csv(os.path.join(out_dir, "mc_results.csv"), index=False)
    _save_config_snapshot(cfg, out_dir)

    _make_figures(out_dir, df, cfg)

    # console summary
    ni = df["total_net_income"]
    expected = float(ni.mean())
    p5 = float(ni.quantile(0.05))
    prob_loss = float((ni < 0).mean())

    eq_cap = _equity_capital(cfg)
    if eq_cap and eq_cap > 0:
        eq_ret = df["total_net_income"] / eq_cap
        eq_mean = float(eq_ret.mean())
        eq_p5 = float(eq_ret.quantile(0.05))
        prob_eq_loss = float((eq_ret < 0).mean())
    else:
        eq_mean = eq_p5 = prob_eq_loss = None

    print("===== Monte Carlo Summary =====")
    print(f"Run ID: {rid}")
    print(f"Expected Total Net Income: ${expected:,.0f}")
    print(f"5th Percentile (Worst 5%): ${p5:,.0f}")
    print(f"Probability of Loss: {prob_loss*100:.2f}%")
    if eq_mean is not None:
        print(f"Equity Return (mean): {eq_mean*100:.2f}%")
        print(f"Equity Return (5th pct): {eq_p5*100:.2f}%")
        print(f"Probability of Equity Loss: {prob_eq_loss*100:.2f}%")
    print(f"Saved outputs to: {out_dir}")

    pdf_path = generate_pdf_report(out_dir, cfg)
    print("PDF report generated:", pdf_path)
    print("Figures saved to:", os.path.join(out_dir, "figures"))


if __name__ == "__main__":
    main()

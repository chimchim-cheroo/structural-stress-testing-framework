import argparse
import os
import yaml

from src.engine import run_mc
from src.report import make_run_dir, export_all
from src.report_pdf import build_pdf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default="base")
    args = parser.parse_args()

    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    run_id, out_dir, fig_dir = make_run_dir(base_dir="outputs")

    # --- Run Monte Carlo ---
    df_res = run_mc(cfg)

    # ===== Equity summary (for interview / IC-style reporting) =====
    equity_capital = cfg["portfolio"]["notional"] * (1.0 - cfg["funding"]["funding_ratio"])
    df_res["equity_return"] = df_res["total_net_income"] / equity_capital

    equity_mean = df_res["equity_return"].mean()
    equity_p5 = df_res["equity_return"].quantile(0.05)
    equity_loss_prob = (df_res["equity_return"] < 0).mean()

    # --- Export CSV + figures ---
    mean_income, p5_income, loss_prob, out_pdf = export_all(cfg, df_res, out_dir, fig_dir)

    # --- Generate PDF report ---
    build_pdf(out_dir)

    # --- Console summary ---
    print("===== Monte Carlo Summary =====")
    print(f"Run ID: {run_id}")
    print(f"Expected Total Net Income: ${mean_income:,.0f}")
    print(f"5th Percentile (Worst 5%): ${p5_income:,.0f}")
    print(f"Probability of Loss: {loss_prob:.2%}")
    print(f"Equity Return (mean): {equity_mean:.2%}")
    print(f"Equity Return (5th pct): {equity_p5:.2%}")
    print(f"Probability of Equity Loss: {equity_loss_prob:.2%}")
    print(f"Saved outputs to: {out_dir}")
    print("PDF report generated.")

if __name__ == "__main__":
    main()

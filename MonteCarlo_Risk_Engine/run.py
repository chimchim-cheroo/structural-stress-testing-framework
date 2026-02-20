import argparse
import os
import yaml

from src.engine import run_mc
from src.report import make_run_dir, export_all


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default="base")
    args = parser.parse_args()

    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    run_id, out_dir, fig_dir = make_run_dir(base_dir="outputs")

    df_res = run_mc(cfg)

    mean_income, p5_income, loss_prob = export_all(cfg, df_res, out_dir, fig_dir)

    print("===== Monte Carlo Summary =====")
    print(f"Run ID: {run_id}")
    print(f"Expected Total Net Income: ${mean_income:,.0f}")
    print(f"5th Percentile (Worst 5%): ${p5_income:,.0f}")
    print(f"Probability of Loss: {loss_prob:.2%}")
    print(f"Saved outputs to: {out_dir}")


if __name__ == "__main__":
    main()

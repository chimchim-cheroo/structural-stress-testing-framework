import os
import json
import glob
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def _fmt_money(x):
    try:
        return f"${x:,.0f}"
    except Exception:
        return str(x)


def _fmt_pct(x):
    try:
        return f"{x:.2%}"
    except Exception:
        return str(x)


def build_pdf(run_dir: str, pdf_name: str = "report.pdf") -> str:
    """
    Build a single PDF report from outputs/<run_id>/:
      - mc_results.csv
      - config_snapshot.json (optional)
      - figures/*.png (optional)
    """
    run_dir = os.path.abspath(run_dir)
    csv_path = os.path.join(run_dir, "mc_results.csv")
    cfg_path = os.path.join(run_dir, "config_snapshot.json")
    figs_dir = os.path.join(run_dir, "figures")
    pdf_path = os.path.join(run_dir, pdf_name)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing {csv_path}")

    df = pd.read_csv(csv_path)

    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "r") as f:
            cfg = json.load(f)

    # --- summary metrics ---
    income_col = "total_net_income" if "total_net_income" in df.columns else df.columns[0]
    income = pd.to_numeric(df[income_col], errors="coerce")

    mean_income = float(income.mean())
    p5_income = float(income.quantile(0.05))
    loss_prob = float((income < 0).mean())

    # Equity metrics (if present)
    equity_lines = []
    if "equity_return" in df.columns:
        eq = pd.to_numeric(df["equity_return"], errors="coerce")
        eq_mean = float(eq.mean())
        eq_p5 = float(eq.quantile(0.05))
        eq_loss_prob = float((eq < 0).mean())
        equity_lines = [
            "",
            "Equity Return Metrics",
            f"- Equity Return (mean): {_fmt_pct(eq_mean)}",
            f"- Equity Return (5th pct): {_fmt_pct(eq_p5)}",
            f"- Probability of Equity Loss: {_fmt_pct(eq_loss_prob)}",
            "",
        ]

    # tranche loss probabilities if present
    tranche_cols = [c for c in ["WH_loss", "A_loss", "B_loss", "C_loss"] if c in df.columns]
    tranche_lines = []
    for c in tranche_cols:
        p = float((pd.to_numeric(df[c], errors="coerce") > 0).mean())
        tranche_lines.append(f"{c}: P(loss>0) = {p:.2%}")

    # --- build PDF ---
    with PdfPages(pdf_path) as pdf:
        # Page 1: text summary
        fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
        fig.suptitle("Monte Carlo Risk Report", fontsize=18, y=0.98)

        run_id = os.path.basename(run_dir.rstrip("/"))
        lines = [
            f"Run ID: {run_id}",
            "",
            "Key Metrics",
            f"- Expected Total Net Income: {_fmt_money(mean_income)}",
            f"- 5th Percentile (Worst 5%): {_fmt_money(p5_income)}",
            f"- Probability of Loss: {loss_prob:.2%}",
        ]

        # Add equity summary right after key metrics
        if equity_lines:
            lines += equity_lines

        if tranche_lines:
            lines += ["Tranche Loss Probabilities"] + [f"- {t}" for t in tranche_lines] + [""]

        # config snapshot
        if cfg:
            lines += ["Config Snapshot (selected)"]

            # try common schemas first; fall back to first few keys
            pick_keys = []
            for k in [
                "seed",
                "sim",
                "portfolio",
                "funding",
                "opex",
                "risk_engine",
                "n_sims",
                "horizon_months",
                "portfolio_notional",
                "coupon_annual",
            ]:
                if k in cfg:
                    pick_keys.append(k)

            if not pick_keys:
                pick_keys = list(cfg.keys())[:8]

            for k in pick_keys:
                v = cfg.get(k)
                vv = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                if len(vv) > 160:
                    vv = vv[:160] + "..."
                lines.append(f"- {k}: {vv}")

        fig.text(0.08, 0.92, "\n".join(lines), va="top", fontsize=11)
        plt.axis("off")
        pdf.savefig(fig)
        plt.close(fig)

        # Pages: embed saved PNG figures (if any)
        pngs = sorted(glob.glob(os.path.join(figs_dir, "*.png")))
        for p in pngs:
            img = plt.imread(p)
            fig = plt.figure(figsize=(11.69, 8.27))  # A4 landscape
            ax = fig.add_axes([0, 0, 1, 1])
            ax.imshow(img)
            ax.axis("off")
            pdf.savefig(fig)
            plt.close(fig)

    return pdf_path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="e.g. outputs/20260218_153345")
    ap.add_argument("--name", default="report.pdf")
    args = ap.parse_args()
    out = build_pdf(args.run_dir, pdf_name=args.name)
    print(f"✅ PDF written: {out}")

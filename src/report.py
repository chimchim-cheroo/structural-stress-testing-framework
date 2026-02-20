import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def make_run_dir(base_dir="outputs"):
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    run_id = ts
    out_dir = os.path.join(base_dir, run_id)
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)
    return run_id, out_dir, fig_dir

def _safe_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return default

def _fmt_money(x):
    try:
        return f"${float(x):,.0f}"
    except Exception:
        return str(x)

def _build_pdf(pdf_path, title, fig_paths, summary_lines=None):
    # delayed import (avoid env issues)
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.utils import ImageReader

    c = canvas.Canvas(pdf_path, pagesize=LETTER)
    W, H = LETTER

    # ---------------- Cover / Summary page ----------------
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, H - 80, title)

    c.setFont("Helvetica", 11)
    c.drawString(72, H - 105, f"Generated: {pd.Timestamp.now()}")

    if summary_lines:
        y = H - 140
        line_h = 14
        c.setFont("Helvetica", 11)
        for line in summary_lines:
            # basic page break if needed
            if y < 72:
                c.showPage()
                y = H - 72
                c.setFont("Helvetica", 11)
            c.drawString(72, y, str(line))
            y -= line_h

    c.showPage()

    # ---------------- One image per page ----------------
    for p in fig_paths:
        if not os.path.exists(p):
            continue

        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, H - 60, os.path.basename(p))

        img = ImageReader(p)
        x0, y0 = 72, 72
        max_w, max_h = W - 144, H - 144

        iw, ih = img.getSize()
        scale = min(max_w / iw, max_h / ih)
        w = iw * scale
        h = ih * scale

        c.drawImage(img, x0, y0, width=w, height=h, preserveAspectRatio=True, anchor="sw")
        c.showPage()

    c.save()

def export_all(cfg, df_res, out_dir, fig_dir):
    """
    Saves:
      - mc_results.csv
      - config_snapshot.json
      - figures/*.png (incl equity_return_distribution.png)
      - report.pdf (cover page includes equity return summary)
    Returns: mean_income, p5_income, loss_prob, out_pdf
    """
    # --- save raw results ---
    out_csv = os.path.join(out_dir, "mc_results.csv")
    df_res.to_csv(out_csv, index=False)

    # --- config snapshot (selected) ---
    snap = {
        "seed": cfg.get("seed"),
        "sim": cfg.get("sim", {}),
        "portfolio": cfg.get("portfolio", {}),
        "funding": cfg.get("funding", {}),
        "opex": cfg.get("opex", {}),
        "risk_engine": cfg.get("risk_engine", {}),
    }
    with open(os.path.join(out_dir, "config_snapshot.json"), "w") as f:
        json.dump(snap, f, indent=2)

    # --- key metrics (net income) ---
    df_res = df_res.copy()
    mean_income = float(df_res["total_net_income"].mean())
    p5_income = float(df_res["total_net_income"].quantile(0.05))
    loss_prob = float((df_res["total_net_income"] < 0).mean())

    # --- tranche loss probabilities (if columns exist) ---
    tranche_cols = [c for c in ["WH_loss", "A_loss", "B_loss", "C_loss"] if c in df_res.columns]
    tranche_lines = []
    for ccol in tranche_cols:
        p = float((df_res[ccol].astype(float) > 0).mean())
        tranche_lines.append(f"{ccol}: P(loss>0) = {p:.2%}")

    # --- equity return (equity = notional * (1 - funding_ratio)) ---
    notional = _safe_float(cfg.get("portfolio", {}).get("notional", np.nan))
    funding_ratio = _safe_float(cfg.get("funding", {}).get("funding_ratio", np.nan))
    equity = notional * (1.0 - funding_ratio) if np.isfinite(notional) and np.isfinite(funding_ratio) else np.nan

    equity_mean = None
    equity_p5 = None
    equity_loss_prob = None

    if np.isfinite(equity) and equity != 0:
        df_res["equity_return"] = df_res["total_net_income"] / equity
        equity_mean = float(df_res["equity_return"].mean())
        equity_p5 = float(df_res["equity_return"].quantile(0.05))
        equity_loss_prob = float((df_res["equity_return"] < 0).mean())

    # ========== FIG 1: Distribution of Total Net Income ==========
    p1 = os.path.join(fig_dir, "dist_total_net_income.png")
    plt.figure()
    plt.hist(df_res["total_net_income"], bins=40)
    plt.title("Distribution of Total Net Income")
    plt.xlabel("Total Net Income")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(p1)
    plt.close()

    # ========== FIG 2: Sensitivity (Correlation) ==========
    sens_cols = [c for c in ["default_rate", "lgd", "margin_shock"] if c in df_res.columns]
    p2 = os.path.join(fig_dir, "sensitivity_corr.png")
    if len(sens_cols) > 0:
        corrs = [df_res["total_net_income"].corr(df_res[c]) for c in sens_cols]
        plt.figure()
        plt.bar(sens_cols, corrs)
        plt.title("Sensitivity (Correlation)")
        plt.ylabel("Correlation with Net Income")
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(p2)
        plt.close()

    # ========== FIG 3: Tail View ==========
    p3 = os.path.join(fig_dir, "tail_total_net_income.png")
    ordered = np.sort(df_res["total_net_income"].values)
    plt.figure()
    plt.plot(np.arange(1, len(ordered) + 1), ordered)
    plt.title("Ordered Total Net Income (Tail View)")
    plt.xlabel("Simulation Rank")
    plt.ylabel("Total Net Income")
    plt.tight_layout()
    plt.savefig(p3)
    plt.close()

    # ========== FIG 4: Equity Return Distribution ==========
    p4 = os.path.join(fig_dir, "equity_return_distribution.png")
    if "equity_return" in df_res.columns:
        plt.figure()
        plt.hist(df_res["equity_return"], bins=40)
        plt.title("Equity Return Distribution")
        plt.xlabel("Equity Return")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(p4)
        plt.close()

    # --- Build PDF: include ALL PNGs in figures/ ---
    fig_paths = sorted(
        [os.path.join(fig_dir, f) for f in os.listdir(fig_dir) if f.lower().endswith(".png")]
    )

    # --- Summary page lines (include equity return) ---
    run_id = os.path.basename(os.path.normpath(out_dir))
    summary_lines = [
        f"Run ID: {run_id}",
        "",
        "Key Metrics",
        f"- Expected Total Net Income: {_fmt_money(mean_income)}",
        f"- 5th Percentile (Worst 5%): {_fmt_money(p5_income)}",
        f"- Probability of Loss: {loss_prob:.2%}",
    ]

    if equity_mean is not None:
        summary_lines += [
            "",
            "Equity Return (Equity = Notional × (1 - Funding Ratio))",
            f"- Equity Return (mean): {equity_mean:.2%}",
            f"- Equity Return (5th pct): {equity_p5:.2%}",
            f"- Probability of Equity Loss: {equity_loss_prob:.2%}",
        ]

    if tranche_lines:
        summary_lines += ["", "Tranche Loss Probabilities"] + [f"- {t}" for t in tranche_lines]

    out_pdf = os.path.join(out_dir, "report.pdf")
    _build_pdf(out_pdf, title="Monte Carlo Risk Report", fig_paths=fig_paths, summary_lines=summary_lines)

    return mean_income, p5_income, loss_prob, out_pdf


import os
import json
import pandas as pd

from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def _fmt_money(x):
    try:
        return "${:,.0f}".format(float(x))
    except Exception:
        return str(x)

def _fmt_pct(x):
    try:
        return "{:.2f}%".format(100.0 * float(x))
    except Exception:
        return str(x)

def _safe_read_csv(path):
    try:
        if os.path.exists(path):
            return pd.read_csv(path)
    except Exception:
        pass
    return None

def _scaled_image(path, max_w, max_h):
    if not os.path.exists(path):
        return None
    try:
        img = RLImage(path)
        iw, ih = float(img.imageWidth), float(img.imageHeight)
        if iw <= 0 or ih <= 0:
            return None
        s = min(max_w / iw, max_h / ih, 1.0)
        img.drawWidth = iw * s
        img.drawHeight = ih * s
        return img
    except Exception:
        return None


def generate_pdf_report(output_dir: str, cfg: dict | None = None) -> str:
    mc_path = os.path.join(output_dir, "mc_results.csv")
    if not os.path.exists(mc_path):
        raise FileNotFoundError(f"Missing {mc_path}")

    df = pd.read_csv(mc_path)

    if cfg is None:
        snap = os.path.join(output_dir, "config_snapshot.json")
        if os.path.exists(snap):
            with open(snap, "r") as f:
                cfg = json.load(f)
        else:
            cfg = {}

    run_id = os.path.basename(output_dir.rstrip("/"))
    styles = getSampleStyleSheet()

    # margins
    margin = 36  # 0.5 inch
    pdf_path = os.path.join(output_dir, "report.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin)
    usable_w = letter[0] - 2 * margin
    usable_h = letter[1] - 2 * margin

    story = []

    # headline
    ni = df["total_net_income"]
    expected = float(ni.mean())
    p5 = float(ni.quantile(0.05))
    prob_loss = float((ni < 0).mean())

    notional = float(cfg.get("portfolio", {}).get("notional", 0) or 0)
    funding_ratio = float(cfg.get("funding", {}).get("funding_ratio", 0.8))
    equity_capital = notional * (1.0 - funding_ratio) if notional else None

    if equity_capital and equity_capital > 0:
        eq_ret = df["total_net_income"] / equity_capital
        eq_mean = float(eq_ret.mean())
        eq_p5 = float(eq_ret.quantile(0.05))
        prob_eq_loss = float((eq_ret < 0).mean())
    else:
        eq_mean = eq_p5 = prob_eq_loss = None

    story.append(Paragraph("Monte Carlo Risk Report", styles["Title"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Model Version: <b>Freeze V3</b> (bullet maturity + refinance cliff + liquidity tail)", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Run ID: <b>{run_id}</b>", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Key Metrics", styles["Heading2"]))
    story.append(Paragraph(f"- Expected Total Net Income: <b>{_fmt_money(expected)}</b>", styles["Normal"]))
    story.append(Paragraph(f"- 5th Percentile (Worst 5%): <b>{_fmt_money(p5)}</b>", styles["Normal"]))
    story.append(Paragraph(f"- Probability of Loss: <b>{_fmt_pct(prob_loss)}</b>", styles["Normal"]))

    if eq_mean is not None:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Equity Return Metrics", styles["Heading2"]))
        story.append(Paragraph(f"- Equity Return (mean): <b>{_fmt_pct(eq_mean)}</b>", styles["Normal"]))
        story.append(Paragraph(f"- Equity Return (5th pct): <b>{_fmt_pct(eq_p5)}</b>", styles["Normal"]))
        story.append(Paragraph(f"- Probability of Equity Loss: <b>{_fmt_pct(prob_eq_loss)}</b>", styles["Normal"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Config Snapshot (selected)", styles["Heading2"]))
    sel = {
        "seed": cfg.get("seed"),
        "sim": cfg.get("sim"),
        "portfolio": cfg.get("portfolio"),
        "funding": cfg.get("funding"),
        "opex": cfg.get("opex"),
        "risk_engine": cfg.get("risk_engine"),
    }
    story.append(Paragraph(f"<font size=9>{str(sel)[:950]}{'...' if len(str(sel))>950 else ''}</font>", styles["Normal"]))

    # figures
    fig_dir = os.path.join(output_dir, "figures")
    story.append(PageBreak())
    story.append(Paragraph("Figures", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Each image fits within a "frame" height to avoid huge stretching
    max_w = usable_w
    max_h_img = 320  # keep reasonable on a letter page

    ordered_imgs = [
        "ni_distribution.png",
        "equity_return_distribution.png",
        "sensitivity_corr.png",
        "tail_total_net_income.png",
        "credit_vs_liquidity_scatter.png",
    ]
    for name in ordered_imgs:
        p = os.path.join(fig_dir, name)
        img = _scaled_image(p, max_w, max_h_img)
        if img:
            story.append(Paragraph(name, styles["Normal"]))
            story.append(img)
            story.append(Spacer(1, 14))

    # Tail table page (landscape to avoid overflow)
    tail_csv = os.path.join(fig_dir, "tail_decomposition.csv")
    decomp = _safe_read_csv(tail_csv)

    has_credit = "credit_loss" in df.columns
    has_liq = "liquidity_loss" in df.columns
    corr_credit = float(df["total_net_income"].corr(df["credit_loss"])) if has_credit else None
    corr_liq = float(df["total_net_income"].corr(df["liquidity_loss"])) if has_liq else None

    if decomp is not None or has_credit or has_liq:
        story.append(PageBreak())
        # switch to landscape doc by building a separate table-sized page using a temporary SimpleDocTemplate is messy,
        # so we keep it portrait but aggressively shrink columns + font. (Works well enough.)
        story.append(Paragraph("Tail Decomposition & Drivers", styles["Heading2"]))
        story.append(Spacer(1, 8))

    if decomp is not None:
        # Short labels to fit
        rename = {
            "scope":"Scope",
            "n":"N",
            "ni_mean":"NI mean",
            "ni_p5":"NI p5",
            "ni_min":"NI min",
            "credit_mean":"Credit mean",
            "credit_p95":"Credit p95",
            "credit_max":"Credit max",
            "p_credit_gt_0":"P(credit>0)",
            "liq_mean":"Liq mean",
            "liq_p95":"Liq p95",
            "liq_max":"Liq max",
            "p_liq_gt_0":"P(liq>0)",
        }
        cols = [c for c in decomp.columns if c in rename]
        small = decomp[cols].rename(columns=rename).copy()

        # format cells
        for c in small.columns:
            if c.startswith("P("):
                small[c] = small[c].apply(_fmt_pct)
            elif c in ["N","Scope"]:
                pass
            else:
                small[c] = small[c].apply(_fmt_money)

        data = [list(small.columns)] + small.values.tolist()

        # set column widths to fit page
        col_count = len(small.columns)
        # give Scope a bit more, percentages less
        base_w = usable_w / col_count
        col_widths = []
        for col in small.columns:
            if col == "Scope":
                col_widths.append(base_w * 1.2)
            elif col.startswith("P("):
                col_widths.append(base_w * 0.9)
            else:
                col_widths.append(base_w)
        # normalize to usable width
        s = sum(col_widths)
        col_widths = [w * (usable_w / s) for w in col_widths]

        tbl = Table(data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 2),
            ("RIGHTPADDING", (0,0), (-1,-1), 2),
            ("TOPPADDING", (0,0), (-1,-1), 2),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 10))

    if has_credit or has_liq:
        story.append(Paragraph("Drivers (Correlation with Net Income)", styles["Heading2"]))
        if corr_credit is not None:
            story.append(Paragraph(f"- Corr(NI, credit_loss): <b>{corr_credit:.3f}</b>", styles["Normal"]))
        if corr_liq is not None:
            story.append(Paragraph(f"- Corr(NI, liquidity_loss): <b>{corr_liq:.3f}</b>", styles["Normal"]))
        if has_liq:
            p_liq = float((df["liquidity_loss"] > 0).mean())
            story.append(Paragraph(f"- P(liquidity_loss &gt; 0): <b>{_fmt_pct(p_liq)}</b>", styles["Normal"]))

    doc.build(story)
    return pdf_path

import copy
import yaml
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.engine import run_mc


# ----------------------------
# Helpers
# ----------------------------
def load_base_cfg(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def deep_update(d: dict, u: dict) -> dict:
    """Recursively update dict d with u (in-place)."""
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d.get(k), dict):
            deep_update(d[k], v)
        else:
            d[k] = v
    return d


def apply_freeze_switch(cfg: dict, freeze_on: bool) -> dict:
    """
    Make Freeze OFF truly OFF:
    - p_freeze_start=0 so freeze never starts
    - p_freeze_persist=0 so freeze can't persist
    """
    cfg = copy.deepcopy(cfg)
    cfg.setdefault("funding", {})
    if freeze_on:
        # leave as-is (use config values)
        return cfg
    cfg["funding"]["p_freeze_start"] = 0.0
    cfg["funding"]["p_freeze_persist"] = 0.0
    return cfg


@st.cache_data(show_spinner=False)
def run_cached(cfg: dict) -> pd.DataFrame:
    # cfg is hashable by streamlit cache via pickle; keep it a plain dict
    return run_mc(cfg)


def tail_stats(df: pd.DataFrame, ni_col: str = "total_net_income") -> dict:
    tail_cut = float(np.percentile(df[ni_col].values, 5))
    tail = df[df[ni_col] <= tail_cut].copy()

    stats = {
        "tail_cut": tail_cut,
        "p_liq_pos_all": float((df["liquidity_loss"] > 0).mean()),
        "p_liq_pos_tail": float((tail["liquidity_loss"] > 0).mean()) if len(tail) else 0.0,
        "tail_mean_credit": float(tail["credit_loss"].mean()) if len(tail) else 0.0,
        "tail_mean_liq": float(tail["liquidity_loss"].mean()) if len(tail) else 0.0,
        "df_tail": tail,
    }
    return stats


def fmt_m(x: float) -> str:
    return f"${x/1e6:,.1f}m"


# ----------------------------
# Page
# ----------------------------
st.set_page_config(page_title="Visual Risk System Prototype", layout="wide")
st.title("Visual Risk System Prototype")
st.caption("Monte Carlo • Regime Switch (Freeze) • Tail Decomposition • Scenario Explorer")

# ----------------------------
# Load config.yaml (single source of truth)
# ----------------------------
base_cfg = load_base_cfg("config.yaml")

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    st.header("Controls")

    freeze_mode = st.radio(
        "Freeze Mode",
        options=["Compare OFF vs ON", "ON only", "OFF only"],
        index=0,
    )

    n_sims = st.slider("Simulations (N)", 1000, 50000, int(base_cfg["sim"]["N"]), step=1000)
    seed = st.number_input("Seed", value=int(base_cfg.get("seed", 42)), step=1)

    st.divider()
    st.subheader("Quick overrides (optional)")

    # Optional: a few high-impact knobs from config
    notional = st.number_input(
        "Notional",
        value=float(base_cfg["portfolio"]["notional"]),
        step=1_000_000.0,
        format="%.0f",
    )
    coupon = st.number_input(
        "Annual coupon rate",
        value=float(base_cfg["portfolio"]["annual_coupon_rate"]),
        step=0.005,
        format="%.3f",
    )

    p_freeze_start = st.number_input(
        "p_freeze_start",
        value=float(base_cfg.get("funding", {}).get("p_freeze_start", 0.06)),
        step=0.01,
        format="%.3f",
    )
    p_freeze_persist = st.number_input(
        "p_freeze_persist",
        value=float(base_cfg.get("funding", {}).get("p_freeze_persist", 0.70)),
        step=0.05,
        format="%.3f",
    )

    st.divider()
    run_btn = st.button("Run Simulation", type="primary")

# ----------------------------
# Build cfg (config.yaml + sidebar overrides)
# ----------------------------
cfg_overrides = {
    "seed": int(seed),
    "sim": {"N": int(n_sims)},
    "portfolio": {"notional": float(notional), "annual_coupon_rate": float(coupon)},
    "funding": {"p_freeze_start": float(p_freeze_start), "p_freeze_persist": float(p_freeze_persist)},
}

cfg_base = copy.deepcopy(base_cfg)
deep_update(cfg_base, cfg_overrides)

# Streamlit reruns on any widget change; we gate heavy compute behind a button
# but also allow first render to run once automatically
if "has_run" not in st.session_state:
    st.session_state["has_run"] = False

if run_btn:
    st.session_state["has_run"] = True

if not st.session_state["has_run"]:
    st.info("Adjust controls, then click **Run Simulation**.", icon="🧪")
    st.stop()

# ----------------------------
# Run simulations depending on freeze_mode
# ----------------------------
with st.spinner("Running Monte Carlo..."):
    if freeze_mode == "Compare OFF vs ON":
        cfg_on = apply_freeze_switch(cfg_base, True)
        cfg_off = apply_freeze_switch(cfg_base, False)

        df_on = run_cached(cfg_on)
        df_off = run_cached(cfg_off)

        s_on = tail_stats(df_on)
        s_off = tail_stats(df_off)

    elif freeze_mode == "ON only":
        cfg_on = apply_freeze_switch(cfg_base, True)
        df_on = run_cached(cfg_on)
        s_on = tail_stats(df_on)
        df_off, s_off = None, None

    else:  # OFF only
        cfg_off = apply_freeze_switch(cfg_base, False)
        df_off = run_cached(cfg_off)
        s_off = tail_stats(df_off)
        df_on, s_on = None, None

# ----------------------------
# Top KPI row
# ----------------------------
st.subheader("B. Tail Decomposition – One-glance Panel")

if freeze_mode == "Compare OFF vs ON":
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("OFF: Tail mean credit_loss", fmt_m(s_off["tail_mean_credit"]))
    c2.metric("OFF: Tail mean liquidity_loss", fmt_m(s_off["tail_mean_liq"]))
    c3.metric("OFF: Tail P(liq>0)", f"{s_off['p_liq_pos_tail']*100:,.1f}%")

    c4.metric("ON: Tail mean credit_loss", fmt_m(s_on["tail_mean_credit"]))
    c5.metric("ON: Tail mean liquidity_loss", fmt_m(s_on["tail_mean_liq"]))
    c6.metric("ON: Tail P(liq>0)", f"{s_on['p_liq_pos_tail']*100:,.1f}%")

    st.caption(
        f"Overall P(liq>0): OFF {s_off['p_liq_pos_all']*100:,.1f}% | ON {s_on['p_liq_pos_all']*100:,.1f}% • "
        f"Tail cutoff (5th pct NI): OFF {fmt_m(s_off['tail_cut'])} | ON {fmt_m(s_on['tail_cut'])}"
    )

else:
    s = s_on if freeze_mode == "ON only" else s_off
    c1, c2, c3 = st.columns(3)
    c1.metric("Tail mean credit_loss", fmt_m(s["tail_mean_credit"]))
    c2.metric("Tail mean liquidity_loss", fmt_m(s["tail_mean_liq"]))
    c3.metric("Tail P(liq>0)", f"{s['p_liq_pos_tail']*100:,.1f}%")

    st.caption(
        f"Overall P(liq>0): {s['p_liq_pos_all']*100:,.1f}% • Tail cutoff (5th pct NI): {fmt_m(s['tail_cut'])}"
    )

st.divider()

# ----------------------------
# Main visuals
# ----------------------------
left, right = st.columns([1.4, 1])

with left:
    st.subheader("A. Regime Switch – Distribution Impact")

    if freeze_mode == "Compare OFF vs ON":
        # Overlay histograms via plotly graph_objects for clearer comparison
        fig = go.Figure()

        fig.add_trace(go.Histogram(
            x=df_off["total_net_income"],
            nbinsx=70,
            name="Freeze OFF",
            opacity=0.55,
        ))
        fig.add_trace(go.Histogram(
            x=df_on["total_net_income"],
            nbinsx=70,
            name="Freeze ON",
            opacity=0.55,
        ))

        # Tail cut lines
        fig.add_vline(x=s_off["tail_cut"], line_dash="dash")
        fig.add_vline(x=s_on["tail_cut"], line_dash="dash")

        fig.update_layout(
            barmode="overlay",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            xaxis_title="total_net_income",
            yaxis_title="count",
        )
        st.plotly_chart(fig, width="stretch")

    else:
        df = df_on if freeze_mode == "ON only" else df_off
        s = s_on if freeze_mode == "ON only" else s_off

        fig = px.histogram(df, x="total_net_income", nbins=70, marginal="box")
        fig.add_vline(x=s["tail_cut"], line_dash="dash")
        st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Tail Composition (Worst 5%)")

    if freeze_mode == "Compare OFF vs ON":
        comp = pd.DataFrame({
            "mode": ["Freeze OFF", "Freeze OFF", "Freeze ON", "Freeze ON"],
            "component": ["credit_loss", "liquidity_loss", "credit_loss", "liquidity_loss"],
            "tail_mean_loss": [s_off["tail_mean_credit"], s_off["tail_mean_liq"], s_on["tail_mean_credit"], s_on["tail_mean_liq"]],
        })
        fig2 = px.bar(comp, x="mode", y="tail_mean_loss", color="component", barmode="stack")
        fig2.update_layout(xaxis_title="", yaxis_title="Tail mean loss")
        st.plotly_chart(fig2, width="stretch")
    else:
        s = s_on if freeze_mode == "ON only" else s_off
        comp = pd.DataFrame({
            "component": ["credit_loss", "liquidity_loss"],
            "tail_mean_loss": [s["tail_mean_credit"], s["tail_mean_liq"]],
        })
        fig2 = px.bar(comp, x="component", y="tail_mean_loss")
        fig2.update_layout(xaxis_title="", yaxis_title="Tail mean loss")
        st.plotly_chart(fig2, width="stretch")

    st.divider()
    st.subheader("Scenario Explorer (Worst 5%)")

    # choose dataset for explorer: prefer ON if comparing
    if freeze_mode == "Compare OFF vs ON":
        df_exp = s_on["df_tail"].sort_values("total_net_income").reset_index(drop=True)
        label = "Freeze ON tail"
    else:
        s = s_on if freeze_mode == "ON only" else s_off
        df_exp = s["df_tail"].sort_values("total_net_income").reset_index(drop=True)
        label = "Tail"

    if len(df_exp) == 0:
        st.warning("No tail scenarios (unexpected).")
    else:
        idx = st.slider("Pick a tail scenario (sorted by worst NI)", 0, len(df_exp) - 1, 0)
        row = df_exp.iloc[int(idx)]

        m1, m2, m3 = st.columns(3)
        m1.metric("total_net_income", fmt_m(float(row["total_net_income"])))
        m2.metric("credit_loss", fmt_m(float(row["credit_loss"])))
        m3.metric("liquidity_loss", fmt_m(float(row["liquidity_loss"])))

        k1, k2, k3 = st.columns(3)
        k1.metric("Z_sys", f"{float(row['Z_sys']):.2f}")
        k2.metric("default_rate", f"{float(row['default_rate']):.3f}")
        k3.metric("lgd", f"{float(row['lgd']):.3f}")

        st.caption(f"Explorer dataset: {label}")

st.divider()

# ----------------------------
# Downloads + config snapshot
# ----------------------------
st.subheader("Exports")

colA, colB = st.columns([1, 1])

with colA:
    if freeze_mode == "Compare OFF vs ON":
        out_df = df_on.copy()
        out_df["mode"] = "Freeze ON"
        out_df2 = df_off.copy()
        out_df2["mode"] = "Freeze OFF"
        out_all = pd.concat([out_df, out_df2], ignore_index=True)
        csv = out_all.to_csv(index=False).encode("utf-8")
    else:
        df = df_on if freeze_mode == "ON only" else df_off
        csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download simulation results (CSV)",
        data=csv,
        file_name="mc_results.csv",
        mime="text/csv",
    )

with colB:
    cfg_yaml = yaml.safe_dump(cfg_base, sort_keys=False).encode("utf-8")
    st.download_button(
        "Download config snapshot (YAML)",
        data=cfg_yaml,
        file_name="config_snapshot.yaml",
        mime="text/yaml",
    )

st.caption("Tip: edit config.yaml → click Run Simulation → dashboard updates. Sidebar values override config for experimentation.")

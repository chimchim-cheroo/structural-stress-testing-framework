import numpy as np
import pandas as pd


def _sample_params(rng, cfg):
    re = cfg["risk_engine"]

    Z = rng.normal()
    e1, e2, e3 = rng.normal(size=3)

    z_default = np.sqrt(re["rho_default"]) * Z + np.sqrt(1 - re["rho_default"]) * e1
    z_lgd = np.sqrt(re["rho_lgd"]) * Z + np.sqrt(1 - re["rho_lgd"]) * e2
    z_margin = np.sqrt(re["rho_margin"]) * Z + np.sqrt(1 - re["rho_margin"]) * e3

    default_rate = re["default_rate"]["base"] + re["default_rate"]["shock_coef"] * (-z_default)
    default_rate = float(np.clip(default_rate,
                                 re["default_rate"]["clip_min"],
                                 re["default_rate"]["clip_max"]))

    lgd = re["lgd"]["base"] + re["lgd"]["shock_coef"] * (-z_lgd)
    lgd = float(np.clip(lgd,
                        re["lgd"]["clip_min"],
                        re["lgd"]["clip_max"]))

    margin_shock = re["margin_shock"]["shock_coef"] * z_margin
    margin_shock = float(np.clip(margin_shock,
                                 re["margin_shock"]["clip_min"],
                                 re["margin_shock"]["clip_max"]))

    return default_rate, lgd, margin_shock


def _simulate_one_path(cfg, default_rate, lgd, margin_shock):

    H = cfg["sim"]["H"]
    notional = cfg["portfolio"]["notional"]

    A_limit = notional * 0.6
    B_limit = notional * 0.2
    C_limit = notional * 0.1
    WH_limit = notional * 0.1

    A_bal = B_bal = C_bal = 0.0
    WH_bal = notional  # month 0 bridge

    coupon = cfg["portfolio"]["annual_coupon_rate"] + margin_shock
    coupon_m = coupon / 12

    A_rate = 0.05 / 12
    B_rate = 0.07 / 12
    C_rate = 0.10 / 12
    WH_rate = 0.08 / 12

    monthly_principal = notional / H
    outstanding = notional

    total_income = 0.0

    for t in range(H):

        if t > 0:
            funding_needed = outstanding - (A_bal + B_bal + C_bal)

            draw_A = min(A_limit - A_bal, funding_needed)
            A_bal += draw_A
            funding_needed -= draw_A

            draw_B = min(B_limit - B_bal, funding_needed)
            B_bal += draw_B
            funding_needed -= draw_B

            draw_C = min(C_limit - C_bal, funding_needed)
            C_bal += draw_C
            funding_needed -= draw_C

            WH_bal = max(outstanding - (A_bal + B_bal + C_bal), 0)

        interest_income = outstanding * coupon_m
        funding_cost = (
            A_bal * A_rate +
            B_bal * B_rate +
            C_bal * C_rate +
            WH_bal * WH_rate
        )

        total_income += (interest_income - funding_cost)

        repay = monthly_principal
        total_bal = A_bal + B_bal + C_bal + WH_bal

        if total_bal > 0:
            A_bal -= repay * A_bal / total_bal
            B_bal -= repay * B_bal / total_bal
            C_bal -= repay * C_bal / total_bal
            WH_bal -= repay * WH_bal / total_bal

        outstanding -= repay

    # ---- Default Loss Allocation ----
    cum_default = min(default_rate * (H / 12), 1)
    total_loss = notional * cum_default * lgd

    remaining_loss = total_loss

    C_loss = min(C_bal, remaining_loss)
    remaining_loss -= C_loss

    B_loss = min(B_bal, remaining_loss)
    remaining_loss -= B_loss

    A_loss = min(A_bal, remaining_loss)
    remaining_loss -= A_loss

    WH_loss = min(WH_bal, remaining_loss)
    remaining_loss -= WH_loss

    total_income -= total_loss

    return {
        "total_net_income": total_income,
        "default_rate": default_rate,
        "lgd": lgd,
        "margin_shock": margin_shock,
        "A_loss": A_loss,
        "B_loss": B_loss,
        "C_loss": C_loss,
        "WH_loss": WH_loss
    }


def run_mc(cfg):
    rng = np.random.default_rng(cfg["seed"])
    N = cfg["sim"]["N"]

    records = []

    for i in range(N):
        res = _simulate_one_path(cfg, *_sample_params(rng, cfg))
        records.append(res)

    return pd.DataFrame(records)

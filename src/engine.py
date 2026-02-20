
# ===== REFINANCE CLIFF (LIQUIDITY-TAIL ENHANCED) =====

import numpy as np
import pandas as pd


def _sample_systemic(rng):
    # one-factor systemic driver
    return float(rng.normal())


def _sample_params(rng, cfg, Z):
    re = cfg["risk_engine"]

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


def _simulate_one_path(cfg, Z, default_rate, lgd, margin_shock, rng):
    H = int(cfg["sim"]["H"])
    notional = float(cfg["portfolio"]["notional"])
    funding_cfg = cfg.get("funding", {})

    coupon = float(cfg["portfolio"]["annual_coupon_rate"]) + float(margin_shock)
    coupon_m = coupon / 12.0

    # freeze regime
    p_freeze_start = float(funding_cfg.get("p_freeze_start", 0.06))
    p_freeze_persist = float(funding_cfg.get("p_freeze_persist", 0.70))

    # refinance cliff parameters (tail-enhanced)
    base_fail = float(funding_cfg.get("refinance_fail_prob", 0.50))
    fail_sens = float(funding_cfg.get("refinance_fail_sens", 0.35))   # higher => more likely to fail when Z is bad

    base_haircut = float(funding_cfg.get("forced_sale_haircut", 0.30))
    hair_sens = float(funding_cfg.get("haircut_sens", 0.25))          # higher => deeper haircut when Z is bad
    hair_noise = float(funding_cfg.get("haircut_noise", 0.10))        # idiosyncratic dispersion
    hair_min = float(funding_cfg.get("haircut_min", 0.10))
    hair_max = float(funding_cfg.get("haircut_max", 0.70))

    # bullet term default probability
    term_years = H / 12.0
    p_default_term = 1.0 - (1.0 - np.clip(default_rate, 0.0, 1.0)) ** term_years
    p_default_term = float(np.clip(p_default_term, 0.0, 1.0))

    total_income = 0.0
    credit_loss = 0.0
    liquidity_loss = 0.0

    in_freeze = False
    outstanding = notional

    for t in range(H):
        # freeze state (Markov)
        if in_freeze:
            in_freeze = (rng.random() < p_freeze_persist)
        else:
            in_freeze = (rng.random() < p_freeze_start)

        # interest until maturity
        total_income += outstanding * coupon_m

        if t == H - 1:
            # credit default at maturity
            D = 1.0 if (rng.random() < p_default_term) else 0.0
            credit_loss = notional * D * lgd

            # refinance failure only matters in freeze regime
            if in_freeze:
                # make fail probability stress-dependent (bad Z -> higher fail probability)
                p_fail = base_fail + fail_sens * max(-Z, 0.0)
                p_fail = float(np.clip(p_fail, 0.0, 0.995))

                # haircut becomes stress-dependent + noisy (tail fattening)
                hc = base_haircut + hair_sens * max(-Z, 0.0) + hair_noise * float(rng.normal())
                hc = float(np.clip(hc, hair_min, hair_max))

                if rng.random() < p_fail:
                    forced_value = notional * (1.0 - hc)
                    liquidity_loss = notional - forced_value

            total_income -= (credit_loss + liquidity_loss)
            outstanding = 0.0

    return {
        "total_net_income": float(total_income),
        "credit_loss": float(credit_loss),
        "liquidity_loss": float(liquidity_loss),
        "Z_sys": float(Z),
        "default_rate": float(default_rate),
        "lgd": float(lgd),
        "margin_shock": float(margin_shock),
    }


def run_mc(cfg):
    rng = np.random.default_rng(cfg["seed"])
    N = int(cfg["sim"]["N"])
    out = []
    for _ in range(N):
        Z = _sample_systemic(rng)
        dr, lg, ms = _sample_params(rng, cfg, Z)
        out.append(_simulate_one_path(cfg, Z, dr, lg, ms, rng))
    return pd.DataFrame(out)

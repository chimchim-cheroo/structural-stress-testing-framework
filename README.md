# Structural Stress Testing Framework for a Leveraged Lending Facility

## Overview

This repository contains a structural Monte Carlo framework designed to evaluate the capital resilience of a leveraged lending facility under correlated macroeconomic stress.

The model rebuilds a legacy deterministic Excel facility model into a distribution-based stress testing architecture.  
The focus shifts from single-path cashflow sufficiency to systemic behaviour under joint credit and liquidity stress.

The objective is not forecasting precision, but structural risk diagnosis.

---

---

## Interactive Visual Risk Dashboard

An interactive Streamlit-based dashboard is included to visualise regime-dependent tail behaviour and capital structure transmission.

Live App:
https://chimchim-cheroo-structural-stress-testing-framework.streamlit.app

The dashboard enables:

- Freeze OFF vs ON regime comparison
- Distribution overlay of Total Net Income
- Tail decomposition (credit vs liquidity loss)
- Worst-5% scenario exploration
- Config-driven simulation reruns

To run locally:

```bash
pip install -r requirements.txt
streamlit run app.py

## Analytical Motivation

Leveraged facilities with bullet maturity structures exhibit non-linear downside behaviour when:

- Default rates cluster under macro deterioration
- Loss-given-default increases simultaneously
- Refinancing conditions tighten
- Market liquidity deteriorates

This framework evaluates how these forces interact within a capital stack.

Key question:

How does correlated macro stress transmit through credit risk, refinancing risk, and tranche subordination?

---

## Structural Features

### 1. Correlated Macro Driver

A single systematic factor (Z ~ N(0,1)) drives:

- Default rate
- Loss given default (LGD)
- Refinancing failure probability
- Liquidity haircut severity

This introduces stress clustering rather than independent parameter variation.

---

### 2. Liquidity Freeze Regime

A regime variable models temporary market dysfunction:

- Stress-contingent activation
- Markov persistence
- Additive impact on refinancing probability
- Amplified liquidation haircuts

Liquidity risk is therefore regime-dependent rather than constant.

---

### 3. Dual Loss Channels

The framework decomposes downside risk into:

• Credit Loss  
  Borrower insolvency driven  

• Liquidity Loss  
  Market access / refinancing failure driven  

These channels are correlated but structurally distinct.

---

### 4. Capital Structure Transmission

Capital stack:

- Senior (A)
- Mezzanine (B)
- Junior (C)
- Warehouse bridge

Loss waterfall:

Equity → Junior → Mezzanine → Senior

The model evaluates how macro-correlated stress propagates through this hierarchy.

---

## Simulation Design

Horizon: 60 months  
Paths: 10,000  
Structure: Bullet maturity  
Portfolio: Construction + Bridging loans  

Each simulation path includes:

1. Correlated credit parameter realisation  
2. Freeze regime activation  
3. Refinancing assessment at maturity  
4. Liquidity haircut conditional on failure  
5. Monthly funding cost and tranche balance evolution  

Outputs include:

- Total Net Income distribution
- Tranche-level loss allocation
- Credit vs liquidity decomposition
- Tail diagnostics (worst 5%)

---

## Key Structural Observations

• Expected Net Income remains positive under base conditions  
• Downside distribution exhibits left-skewed convexity  
• Credit loss is the dominant driver in magnitude  
• Liquidity loss activates disproportionately in severe tail states  
• Senior tranches remain insulated unless extreme clustering occurs  

The results suggest that tail amplification is structural and correlation-driven rather than idiosyncratic.

---

## Risk & Policy Relevance

The framework aligns with:

- Macro-prudential stress testing logic  
- Capital resilience diagnostics  
- Liquidity regime analysis  
- Structural transmission analysis across capital stacks  

It complements deterministic facility models by explicitly modelling clustering, regime persistence, and refinancing cliffs.

---

## Limitations

- Single systematic macro factor  
- Linear parameter mapping with clipping  
- Static portfolio composition  
- Exogenous liquidity haircut  
- Simplified refinancing mechanism  

The model is intended for structural insight rather than market prediction.

---

## Repository Structure

src/        Core simulation logic  
run.py      Execution entry point  
config.yaml Parameter configuration  
outputs/    Simulation results  

---

## Author Focus

This project demonstrates:

- Structural risk modelling  
- Distribution-based stress analysis  
- Capital stack transmission mechanics  
- Systemic downside interpretation  

The emphasis is resilience analysis rather than optimisation or trading performance.


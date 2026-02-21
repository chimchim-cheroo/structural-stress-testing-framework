# Structural Stress Testing Framework  
## Monte Carlo Risk Engine + Interactive Regime-Based Dashboard

---

## Overview

This repository contains a structural Monte Carlo framework designed to evaluate the capital resilience of a leveraged lending facility under correlated macroeconomic stress.

The project consists of:

- A distribution-based stress testing engine
- A regime-dependent liquidity freeze model
- A capital stack transmission framework
- An interactive Streamlit visual risk dashboard

The objective is structural risk diagnosis rather than point forecasting.

---

## Live Interactive Dashboard
https://structural-stress-testing-framework-hkeqbytfdvfwd7rqgitweu.streamlit.app/

The framework includes a Streamlit dashboard enabling:

- Freeze OFF vs ON regime comparison
- Distribution overlay visualisation
- Tail (worst 5%) decomposition
- Credit vs Liquidity loss breakdown
- Scenario-level inspection (systemic shock diagnostics)

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Analytical Motivation

Leveraged facilities with bullet maturity structures exhibit non-linear downside behaviour when:

- Default rates cluster under macro deterioration
- Loss-given-default increases simultaneously
- Refinancing conditions tighten
- Market liquidity deteriorates

This framework evaluates how these forces interact within a capital stack.

Core question:

How does correlated macro stress transmit through credit risk, refinancing risk, and tranche subordination?

---

## Structural Architecture

### 1. Correlated Systemic Driver

A single macro factor (Z ~ N(0,1)) drives:

- Default rate
- Loss given default (LGD)
- Margin stress
- Refinancing failure probability
- Liquidity haircut severity

This introduces stress clustering and tail convexity.

---

### 2. Liquidity Freeze Regime

A Markov regime variable models temporary market dysfunction:

- Stress-contingent activation
- Persistence dynamics
- Conditional refinancing failure
- Stress-amplified forced sale haircut

Liquidity risk is regime-dependent rather than static.

---

### 3. Dual Loss Channels

Downside risk is decomposed into:

• Credit Loss  
Borrower insolvency driven  

• Liquidity Loss  
Refinancing failure / market access driven  

These channels are correlated but structurally distinct.

---

### 4. Capital Stack Transmission

Capital structure:

Senior → Mezzanine → Junior → Equity

Loss waterfall:

Equity absorbs first  
Senior insulated unless extreme clustering occurs  

The framework diagnoses capital buffer resilience under macro stress.

---

## Simulation Design

Horizon: 60 months  
Paths: configurable (default 10,000)  
Structure: Bullet maturity  
Portfolio: Construction + Bridging loans  

Each path includes:

1. Correlated macro parameter realisation  
2. Freeze regime evolution  
3. Credit realisation at maturity  
4. Conditional refinancing failure  
5. Liquidity haircut stress  
6. Net income aggregation  

---

## Key Structural Observations

• Expected Net Income remains positive under base case  
• Downside distribution exhibits left-skew convexity  
• Credit loss dominates magnitude  
• Liquidity loss activates disproportionately in tail states  
• Tail amplification is regime-dependent and correlation-driven  

The model highlights systemic clustering effects rather than idiosyncratic shocks.

---

## Risk & Policy Relevance

This framework aligns with:

- Macro-prudential stress testing logic
- Capital adequacy diagnostics
- Liquidity regime analysis
- Structural transmission modelling

It extends deterministic facility modelling into a distribution-based stress architecture.

---

## Repository Structure

```
src/                Core Monte Carlo engine
app.py              Streamlit visual dashboard
config.yaml         Parameter configuration
requirements.txt    Dependencies
```

---

## Limitations

- Single macro factor
- Linear shock mapping
- Static portfolio composition
- Simplified refinancing mechanism
- Stylised liquidity haircut dynamics

The framework is intended for structural insight, not predictive forecasting.

---

## Author Focus

This project demonstrates:

- Structural risk modelling
- Regime-dependent stress architecture
- Distribution-based diagnostics
- Tail decomposition analytics
- Risk storytelling via interactive systems

Emphasis is placed on systemic resilience interpretation rather than trading optimisation.

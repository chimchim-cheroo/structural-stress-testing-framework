# Monte Carlo Risk Engine (Python Upgrade of Excel Model)

## 1. Project Objective
This project upgrades the original Excel-based Monte Carlo model into a structured, modular, and interpretable Python risk engine.

The goal is to:
- Improve transparency of assumptions
- Centralise model configuration
- Enable scenario testing
- Produce reproducible risk reports
- Support future reuse by the company

This is not a full financial engineering rebuild, but a structured and explainable risk simulation framework.

---

## 2. Model Structure
The model is organised into logical layers:

### (1) Risk Engine Layer
Generates stochastic risk drivers:
- Annual default rate
- Loss given default (LGD)
- Margin shock
- Optional correlation structure

### (2) Cash Flow Layer
Simulates:
- Monthly interest income
- Monthly default events
- Recovery
- Scheduled amortisation

### (3) Tranche Allocation Layer
Implements economic loss waterfall:
C → B → A → Warehouse

Outputs:
- Total net income
- Tranche losses
- Probability of impairment

### (4) Reporting Layer
Automatically exports:
- Distribution plots
- Tail risk charts
- Sensitivity analysis
- CSV outputs for further analysis

---

## 3. Key Assumptions
All assumptions are configurable via `config.yaml`.

Key parameters include:
- Portfolio notional
- Annual coupon rate
- Simulation horizon
- Number of Monte Carlo runs
- Default base rate and bounds
- LGD base and bounds
- Margin shock range
- Tranche structure limits

---

## 4. How to Run

Install dependencies:
pip install -r requirements.txt

Run simulation:
python run.py

Outputs will be saved to:
outputs/<timestamp>/

---

## 5. Outputs Generated
For each run:
- Expected Total Net Income
- 5% Value-at-Risk
- Probability of Loss
- Tranche loss probabilities
- Distribution plots (PNG)
- Scenario comparison plots
- CSV result file

---

## 6. Example Risk Insights
The engine allows answering key decision questions:
- Which variable drives losses most strongly?
- Under what stress does the Senior tranche incur capital loss?
- Is the loss distribution skewed?
- How does risk change under higher default scenarios?

---

## 7. Why This Is an Upgrade (vs Excel)
- Centralised assumptions (no hidden sheet logic)
- Clear modular structure
- Scenario flexibility
- Automated reporting
- Reproducible simulation runs
- Easier future extension

---

## 8. Future Extensions (Optional)
- Full cash waterfall priority of payments
- Dynamic interest rate modelling
- More detailed amortisation structure
- Excel front-end interface
- Portfolio-level loan simulation

---

## Author
Developed as part of structured finance Monte Carlo upgrade project.

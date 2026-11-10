# Mega Makmur Quant ERP (`megamakmur-quant-erp`)

**Quantitative Automotive Arbitrage Engine, Workshop BOM/HPP Estimator & Automated QRIS/Bank Ledger Reconciliation System**

`megamakmur-quant-erp` is a domain-driven back-office and capital allocation engine built for **Mega Makmur** (Jabodetabek automotive variation workshop & secondary market vehicle arbitrage operation). It replaces fragmented spreadsheet workflows with deterministic Python domain modeling, automated unit-economics scoring, knapsack portfolio optimization under a fixed working capital ceiling, and fuzzy bank/QRIS mutation reconciliation.

## Core Architecture & Engineering Modules

1. **Quantitative Vehicle Arbitrage & Windfall Engine (`src/megamakmur/arbitrage.py`)**
   - Evaluates Jabodetabek secondary-market vehicle candidates across three liquidity tiers (`Tier 1` compact/LCGC, `Tier 2` diesel MPV/SUV, `Tier 3` executive/luxury ATPM).
   - Computes all-in acquisition cost at target and walk-away prices by integrating in-house workshop variation HPP (`Bi-LED`, `Audioteq AQ-A9 Android Head Unit`, `360 Camera`, `Nano Ceramic Coating`, `HVAC Evaporator`), buyer negotiation buffers, and mechanical contingency reserves.
   - Solves a constrained **0/1 Knapsack capital allocation problem** (`optimize_capital_allocation`) across active scouting batches under a **Rp 1,000,000,000** working capital ceiling while enforcing Tier 3 concentration limits.

2. **Workshop POS & Bank/QRIS Reconciliation Engine (`src/megamakmur/reconciliation.py`)**
   - Reconciles daily workshop job orders (`BK-YYYYMM-XXX`) and vehicle inventory records (`MB-YYYY-XXX`) against BCA bank transfers and QRIS settlement logs.
   - Implements a two-pass matching pipeline: exact regex reference-tag extraction followed by a fuzzy amount + date-window + payer-name heuristic matcher.

3. **Fonnte WhatsApp Webhook & Alert Dispatcher (`src/megamakmur/webhooks.py`)**
   - Formats structured mobile inspection cards and dispatches real-time windfall alerts to field scouts via the Fonnte WhatsApp API with HMAC-SHA256 webhook verification.

4. **SQLite Persistence & Terminal CLI (`src/megamakmur/storage.py`, `src/megamakmur/cli.py`)**
   - Zero-overhead SQLite storage and a multi-command CLI (`radar`, `allocate`, `reconcile`, `seed`, `alert-preview`) designed for rapid terminal workflows.

## Quickstart & Terminal Usage

```bash
# 1. Run the test suite
PYTHONPATH=src pytest -v

# 2. Rank active Jabodetabek scouting radar listings by Composite Alpha Score
PYTHONPATH=src python3 -m megamakmur.cli radar --csv data/scouting_radar_2026_10_31.csv

# 3. Optimize working capital allocation under Rp 1,000,000,000 ceiling
PYTHONPATH=src python3 -m megamakmur.cli allocate --csv data/scouting_radar_2026_10_31.csv --capital 1000000000

# 4. Reconcile October Workshop POS jobs against BCA/QRIS settlement mutations
PYTHONPATH=src python3 -m megamakmur.cli reconcile --jobs data/workshop_jobs_2026_10.csv --mutations data/bank_qris_mutations_2026_10.csv

# 5. Preview Fonnte WhatsApp alert payload for a windfall unit
PYTHONPATH=src python3 -m megamakmur.cli alert-preview --csv data/scouting_radar_2026_10_31.csv --unit-id MB-2026-005
```

## Active Engineering Roadmap (Next Milestones)

- [ ] **Issue #1**: Build dynamic Workshop BOM catalog (`Audioteq AQ-A9` 4/128GB vs 8/256GB, `Bi-LED 3-inch`, `NVH Peredam`) to auto-calculate `recon_hpp_idr` from itemized part codes.
- [ ] **Issue #2**: Add BCA & Suzuki Finance 4-year credit refund simulation (`total_dp`, `tenor_months`, `dealer_refund_pct`) into `evaluate_listing()`.
- [ ] **Issue #3**: Implement SQLite-backed inventory aging tracker (`days_in_stock` carrying cost decay on annualized IRR).
- [ ] **Issue #4**: Add CSV/JSON export adapter for Google Sheets bidirectional sync via service account.

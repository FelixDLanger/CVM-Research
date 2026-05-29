# cvm-research

**Empirical validation of the Concentric Value Model**

Companion research repository to [`concentric-value-model`](https://github.com/FelixDLanger/concentric-value-model). Contains doctoral-research code that empirically tests the framework against 10 years of historical fundamentals.

## Research questions

- **Q-A:** Do CVM top-quartile firms deliver higher risk-adjusted forward returns than bottom-quartile firms over 2016–2025, after controlling for sector, country, size, beta, and regime?
- **Q-B:** Are the proposed CVM layer weights consistent with the empirical principal components of firm-level scores across a 200-firm sample over 2016–2025?

## Methodology — what makes this work defensible

**Point-in-time discipline.** Every firm-quarter observation uses only data publicly available at that quarter-end (filtered via SimFin's `publish_date`). No look-ahead bias.

**Engine parity.** The Python scoring engine (`cvm_research/scoring.py`) is a byte-for-byte port of the JavaScript engine in the public tool (build `2026-05-11.r` and later). Parity is verified by `tests/test_parity.py` — 18 representative test cases must agree within ±1 point per dimension/layer/composite. **Parity holds against the actual production JS** (not just my reference implementation), confirmed by extracting `computeDimensions`, `computeLayerScores`, `computeComposite` and the constants directly from `index.html` and running them under Node.js. This means the empirical analysis is validating *the framework as published*, not a parallel implementation.

**Proper derivations.** PE, PB, market_cap, and beta are properly computed (price × shares; 252-day trailing regression for beta), not approximated. ROE uses trailing-twelve-month net income, not crude quarterly × 4 annualization.

**All five controls.** Sector fixed effects, country fixed effects, log market cap, market beta, and regime dummies for COVID-2020 + the 2022–2023 inflation/hiking cycle. Zero-variance dummies are explicitly dropped before estimation to avoid silent collinearity failures.

**Cluster-robust standard errors.** Clustered by `as_of` quarter — accounts for cross-sectional correlation in same-quarter forward returns.

**Trading-day calendar.** Forward returns use pandas business-day offsets (BDay × 252), not calendar-day approximations that drift on weekends.

## Sample

200 publicly listed firms (S&P top 100, EuroStoxx + UK top 50, Nikkei top 20, APAC ex-Japan top 30) × 40 quarter-ends (2016-Q1 through 2025-Q4) = up to **8,000 firm-quarter observations**. Effective sample after NA-dropping on regression inputs typically ~6,000–7,000.

## Files

```
cvm-research/
├── README.md                          # this file
├── requirements.txt                   # Python dependencies
├── .gitignore                         # excludes data caches
├── notebooks/
│   ├── 01_simfin_pipeline.ipynb       # Point-in-time data assembly + forward returns
│   ├── 02_pca_analysis.ipynb          # Q-B: empirical layer weights + parity verification
│   └── 03_backtest_regression.ipynb   # Q-A: framework alpha with all 5 controls
├── cvm_research/                      # shared Python module
│   ├── __init__.py
│   ├── scoring.py                     # Byte-for-byte port of JS scoring engine
│   ├── pit_data.py                    # Point-in-time data assembly
│   └── stats.py                       # Panel regression utilities
├── tests/
│   ├── js_reference.js                # JS scoring engine (Node.js CLI)
│   └── test_parity.py                 # Python vs JS parity test (18 cases)
└── thesis_appendix/                   # generated tables/charts (gitignored content)
```

## Running on Google Colab

1. Sign in to [colab.research.google.com](https://colab.research.google.com)
2. File → Open notebook → GitHub tab → `FelixDLanger/cvm-research`
3. Add your SimFin API key to Colab Secrets (left sidebar, key icon → name `SIMFIN_API_KEY`)
4. Open `notebooks/01_simfin_pipeline.ipynb` → Runtime → Run all
5. Repeat for notebooks 02 and 03

Full step-by-step guide: see the setup guide shipped with this release.

## Running parity test locally (requires Node.js)

```bash
cd cvm-research
python tests/test_parity.py
```

All 18 cases should report `✓ passed`. If any case fails, the Python engine has drifted from the JS reference; do not run empirical analysis until parity is restored.

## Limitations

Honest about what this study does and doesn't address:

- **SimFin coverage.** Data sourced via the SimFin Start tier (10-year bulk history), covering the 2016–2025 window. Coverage is US-strong; EU and APAC coverage varies, so the effective sample for non-US firms may be below nominal. A validation gate in Notebook 01 halts the pipeline if fundamental coverage falls below 50%, preventing silently-degraded panels.

- **Culture dimension (D8).** This dimension uses sector-stratified baseline scoring (TECH 75 / ENERGY 50 / FIN 55 / etc.) informed by published workplace-quality distributions (Glassdoor sector aggregates, Best Places to Work lists). The Python scoring engine *also* accepts per-firm `glassdoorRating` and `glassdoorRecommend` inputs when sourced. The baseline approach is **semi-live evidence-based** — refreshed annually with public sector data — and captures roughly 70% of the signal a per-firm scrape would provide. For DBA-grade rigor a future revision could integrate per-firm Glassdoor data (currently blocked by API partnership requirements).

- **Forward returns.** 1-year horizon. Different horizons (6m, 2y, 3y) may produce different magnitudes; this is a quantitative robustness check worth running but it's not a methodological limitation.

- **PCA is on contemporary scores.** The PCA in notebook 02 pools all firm-quarter observations and computes loadings on the combined sample. A more sophisticated analysis would examine whether the principal-component structure is stable across sub-periods. The current build is structured to meet the methodological expectations of a DBA viva defence; a richer time-varying analysis is a natural follow-up paper.

- **Sample selection.** The 200-firm reference universe was selected to represent investable mega-cap and large-cap firms across major markets. Results may not generalise to small caps, micro caps, or emerging-market frontier names.

- **Survivorship bias.** SimFin includes delisted firms in its historical data, mitigating but not eliminating survivorship effects. The 200-firm reference universe is itself defined ex-post; a fully survivorship-free study would require constructing the universe at each quarter-end from a contemporaneously-defined index membership list. The framework alpha estimate should be interpreted with this in mind.

## Data sources

- **Fundamentals:** [SimFin](https://simfin.com) — accessed under SimFin's free-tier license for academic research. Bulk CSVs are not redistributed in this repository.
- **Country macro:** [World Bank Open Data](https://data.worldbank.org) — public API, no key required.
- **Sector reference baselines:** internal to the CVM framework; see `index.html` in the public tool repo for source.

## Citing this work

> Langer, F. (forthcoming). *Concentric Value Model: A modernised extension of Benjamin Graham's defensive criteria.* DBA thesis, GlobalNxt University.

## Status

- **Phase 1** (public tool): live at [github.com/FelixDLanger/concentric-value-model](https://github.com/FelixDLanger/concentric-value-model)
- **Phase 2** (this repo): private during thesis development; transitions to public on thesis submission

## Disclaimer

This is academic research code structured to meet the methodological expectations of a DBA viva defence. The historical analyses are intended as empirical validation of a methodology, not as investment recommendations. Past performance does not predict future returns. See the public tool's footer for full terms.

## Changelog

**v2.1 (audit fixes — current)**
- **Phase 1 reconciliation:** the public tool's `index.html` had a latent bug where `sec.id === 'X'` evaluated to `undefined` (the `SECTOR_BASELINES` entries have no `id` field), so sector-conditional anchors in `computeDimensions` silently fell through to defaults. Phase 1 build `2026-05-11.r` corrects this — anchors now reference `stock.sector` directly. Phase 2 Python and Phase 1 production JS now agree across all 18 parity test cases.
- **Banks + insurance schema (audit item #2):** Notebook 01 now loads SimFin's specialized statement schemas for financial-sector firms (`load_income_banks`, `load_income_insurance`, etc.). Without this, ~41 FIN-sector tickers (20% of the universe) silently fell back to baseline scoring.
- **Forward-return horizon validation (audit item #3):** `forward_total_return` now returns None when the target end-date is unreachable in the price data, eliminating late-sample partial-horizon bias.
- **Strict TTM (audit item #4):** `trailing_twelve_month_net_income` now requires all 4 quarters available. Previously accepted 3-quarter sums, biasing PE estimates upward by ~33% for affected firms.
- **Market-proxy availability check (audit item #5):** Notebook 01 explicitly verifies SPY is available before using it as the market index for beta computation. Falls back to equal-weighted universe return if not. Provenance recorded in `panel_metadata.json`.

**v2.0 (initial rigorous rebuild)** — see commit history.

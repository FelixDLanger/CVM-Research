# Concentric Value Model — Empirical Methodology

**Document version:** 1.0 (2026-05-31)

-----

## 1. Research Design

This study tests whether the Concentric Value Model (CVM) — a 10-dimension framework for quantitative quality classification of publicly traded firms — produces statistically significant differential forward returns at the firm level and the sector level.

The empirical strategy uses an unbalanced quarterly panel of 200 large-cap firms across 12 industry sectors and 5 geographic regions, observed over 2016-Q1 through 2025-Q4 (40 quarters). The primary analysis is restricted to the US sub-sample (100 firms) where data quality permits clean per-firm inference. The full 200-firm global panel is used as a robustness check.

For each firm-quarter observation, scoring on the 10 CVM dimensions is performed using a Python implementation of the production scoring engine, which itself was validated against the public web tool’s JavaScript engine on 18 reference cases (100% parity). The framework produces a composite score on a 0-100 scale, with quartile assignment based on the sample-wide distribution at each as-of date.

The dependent variable is the 1-year forward total return measured from the as-of date, computed from adjusted close prices with a 10-business-day lookforward window.

-----

## 2. Data Sources

### 2.1 Firm-Level Fundamental Data

Quarterly fundamental data for 6 of the 10 CVM dimensions (macro environment, financial metrics, financial engineering, technology adoption, strategic transformation, market dynamics) is sourced from SimFin’s bulk US, EU, and Asia datasets via paid Start tier subscription. Coverage:

- Reporting quarters: 40 per firm (2016-Q1 through 2025-Q4)
- Fundamental coverage: 51.8% of observations have complete fundamentals
- Forward-return coverage: 47.7% of observations have realized 1-year forward returns
- Validation: independent recomputation against publicly available financial data confirmed accuracy on a random sample of 20 firms

Raw data is cached to Google Drive and reproduced from local cache for replication purposes.

### 2.2 Ownership Data

Insider ownership percentage (D6 management stake) and institutional ownership percentage (D7 ownership structure) are obtained from yfinance snapshots of Yahoo Finance fundamentals data, restricted to US firms. Coverage: ~49% of observations for both dimensions. Non-US firms retain sector-tier baseline scores on these dimensions.

**Important methodological note:** ownership values are point-in-time snapshots held constant across the study period. The cross-sectional ranking (which firms have more institutional ownership) is the source of variation in quartile assignment. Within-firm time-series variation in ownership is NOT captured by this data source. Building true historical 13F-aggregated institutional ownership would require fanning out across thousands of filer-level filings per quarter, which was not feasible within the study’s data-collection constraints.

### 2.3 Sector-Tier Dimensions

Two CVM dimensions are derived from sector-tier baselines refreshed annually from public aggregators:

- **D8 (culture purpose):** Glassdoor sector aggregates of median employer rating, calibrated to a 0-100 scale where higher reflects stronger reported organizational culture.
- **D9 (progressive practices):** Sustainalytics annual industry ESG aggregate scores, inverted to a 0-100 scale where higher reflects lower ESG risk. Anchored to publicly available 2024 sector reports; refreshed annually.

Both dimensions are “semi-live”: values are constant for all firms within a sector for a given annual cohort but differ across sectors. This is a known limitation discussed in Section 6.

### 2.4 Market Data

Adjusted close prices, market capitalization, and rolling beta (3-year window vs MSCI ACWI) for all firms are obtained from yfinance. Market-cap data is point-in-time on the as-of date. Beta is computed monthly with 36-month lookback.

### 2.5 Universe Construction

The 200-firm universe was constructed by selecting 100 largest US S&P 500 firms by market capitalization, 50 European Stoxx + UK FTSE constituents, 30 APAC ex-Japan large-caps, and 20 Japan Nikkei 225 constituents, with ~2.5% tail for sector balance. The universe was finalized after data-availability checks: Fiserv was excluded due to absence in SimFin Start tier bulk data despite multiple ticker variants; Marsh & McLennan was updated to its current ticker MRSH following the 2025 rebrand.

-----

## 3. Variable Construction

### 3.1 Composite Score

The composite score is computed as the weighted average of the 10 dimension scores, with weights derived from the CVM theoretical framework:

- Layer 1 (operating efficiency): 25% weight, comprising 2 dimensions
- Layer 2 (transformation): 22% weight, comprising 2 dimensions
- Layer 3 (governance): 25% weight, comprising 2 dimensions
- Layer 4 (culture): 18% weight, comprising 2 dimensions
- Layer 5 (market dynamics): 10% weight, comprising 2 dimensions

Theoretical layer weights are pre-specified and not derived from empirical data.

### 3.2 Quartile Assignment

For each as-of date, firms are sorted by composite score and bucketed into quartiles Q1 (highest) through Q4 (lowest) using the 25th, 50th, and 75th percentile cutoffs of the sample-wide composite distribution.

### 3.3 Regime Dummies

Three regime dummies are constructed:

- **Pre-COVID:** 2016-Q1 through 2019-Q4
- **COVID era:** 2020-Q1 through 2021-Q4
- **Inflation+:** 2022-Q1 through 2025-Q4

The COVID and inflation regimes are used as controls in the pooled regression and as separating filters for sub-period analysis.

-----

## 4. Econometric Specification

### 4.1 Continuous Composite Regression

The primary specification regresses 1-year forward returns on the composite score with standard asset-pricing controls:

```
forward_return_pct ~ composite
                   + C(sector)
                   + C(country)
                   + log_mcap
                   + beta
                   + covid_regime
                   + inflation_regime
```

Standard errors are cluster-robust by as-of quarter to address residual autocorrelation. Country fixed effect is omitted in US-only regressions due to zero variance.

### 4.2 Quartile Dummy Regression

A parallel specification uses quartile membership as the explanatory variable:

```
forward_return_pct ~ C(quartile, Treatment(reference='Q4'))
                   + [same controls as above]
```

Quartile coefficients are interpreted as differential forward returns versus the reference quartile.

### 4.3 Sub-Period Decomposition

The quartile dummy regression is re-estimated separately within each of the three regime subsamples. This decomposes the pooled estimate into regime-conditional alphas.

### 4.4 Robustness Specifications

Six robustness checks probe the sensitivity of headline findings:

1. **Top-20 composition audit** — examines whether high-composite firms are concentrated in AI/mega-cap names that drove cap-weighted index returns.
1. **Correlation matrix** — reports composite × log_mcap, composite × beta, and composite × forward_return raw correlations.
1. **No-beta regression** — re-runs continuous specification excluding beta to test signal absorption.
1. **No-size regression** — same test for log_mcap.
1. **No-sector-FE regression** — tests whether sector identity is absorbing the framework’s signal.
1. **Equal-weighted vs cap-weighted quartile spreads** — tests robustness to weighting scheme.

Three additional refinements provide alternative bucket specifications:

1. **Above-median vs below-median binary** — preserves quartile assignment but pools Q1+Q2 against Q3+Q4 to address Q4 sparsity.
1. **Tercile regression** — re-buckets sample into thirds for higher statistical power.
1. **Composite excluding D8 and D9** — rebuilds composite from 8 per-firm dimensions only to isolate sector-tier baseline contamination.

### 4.5 Sector Portfolio Backtest

A sector-allocation backtest applies three quarterly-rebalanced allocation rules to the panel, testing whether sector-level CVM scores translate to portfolio outperformance:

- **Top-N overweight (±5pp):** identify top 3 sectors by CVM score, overweight each by +5pp vs equal-weight baseline; underweight bottom 3 by -5pp each.
- **Equal-weight overlay (±3pp):** apply small CVM-proportional tilts capped at ±3pp per sector.
- **Score-proportional:** weight sectors proportional to their CVM composite score.

Each rule is tested against an equal-weight-sector benchmark using paired t-tests on quarterly excess returns. Attribution analysis decomposes the Top-N excess return into per-sector contributions.

-----

## 5. Validation

The Python scoring engine produces results identical to the production JavaScript implementation on 18 reference cases (100% parity) covering all sector × dimension combinations. This validates that empirical results are not artifacts of a divergent implementation.

The validation reference cases are published as part of the research code repository.

-----

## 6. Known Limitations

The following limitations are disclosed transparently and discussed in Section 7 of the empirical chapter:

1. **Snapshot ownership data.** D6 and D7 use point-in-time yfinance snapshots, not historical 13F-aggregated data. Cross-sectional variation is captured; within-firm time-series variation is not.
1. **Sector-tier dimensions.** D8 (culture) and D9 (progressive practices) are derived from annual sector aggregates rather than per-firm data. These dimensions contribute sector-correlated signal to the composite. The empirical chapter reports a robustness specification excluding both dimensions.
1. **Geographic scope.** Primary analysis is US-only; global panel is used as robustness. Findings are not directly generalizable to other geographies or time periods.
1. **Regime specificity.** The study window (2016-2025) is dominated by post-GFC bull market conditions with one major crisis period (COVID 2020-2021). Findings may not generalize to extended bear markets or pre-2008 regimes.
1. **Survivorship bias.** Universe is constructed from current S&P 500 / Stoxx 600 / Nikkei 225 constituents. Firms that were delisted or acquired during the study period are not included. This is a known bias in cross-sectional asset-pricing studies and is acknowledged but not corrected here.
1. **Transaction costs and frictions.** Sector portfolio backtest does not model transaction costs, taxes, or market-impact frictions. Realized live-trading returns would be lower than reported backtest returns.
1. **Statistical power on Q4.** The empirical Q4 quartile contains only 5-6 observations in the US-only sample, limiting power for Q1-vs-Q4 quartile comparisons. The above-median binary specification is included as a more statistically powerful alternative.

-----

## 7. Reproducibility

All code is published in a public GitHub repository (FelixDLanger/CVM-Research). Raw data downloads from SimFin are cached locally; the cached data is available on request. The empirical chapter’s tables and figures can be reproduced by running the three notebooks in sequence (01_simfin_pipeline → 02_pca_analysis → 03_backtest_regression). Random seed is fixed at 42 throughout for any stochastic operations.

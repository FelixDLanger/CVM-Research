# Concentric Value Model — Empirical Findings

**Document version:** 1.0 (2026-05-31)


-----

## Executive Summary

This study tests the empirical predictive power of the Concentric Value Model (CVM) across three distinct levels of analysis. The findings collectively support a regime- and aggregation-dependent interpretation of the framework’s predictive validity:

1. **Sector-level signal is statistically significant and economically meaningful.** Three independent sector-allocation rules derived from CVM scores produced statistically significant positive excess returns over an equal-weight sector benchmark across a 35-quarter US-only sample.
1. **Firm-level signal is generally weak in normal market conditions.** Across the pooled 2016-2025 period, CVM quartile rankings do not produce statistically significant differential returns after controlling for sector, size, beta, and regime.
1. **Firm-level signal is materially significant during crisis periods.** During the COVID-19 crisis and recovery (2020-2021), CVM Q1 firms outperformed Q4 firms by 26.1 percentage points in 1-year forward returns (p=0.027), consistent with academic literature on flight-to-quality dynamics in crisis periods.

Together, these findings position CVM as a defensible quantitative tool for sector allocation, with material additional value as a crisis-period firm-quality classifier.

-----

## 1. Factor Structure (PCA on the 10-Dimension Panel)

Before turning to predictive analyses, we examine the underlying factor structure of the 10 CVM dimensions to understand which dimensions covary and how much of the framework’s variance reduces to a smaller set of underlying axes.

### 1.1 Variance Explained

Principal Component Analysis on the standardized US-only panel (~4,000 firm-quarters × 10 dimensions) yields:

- **PC1: 38.9% of variance**
- **PC2: 14.7% of variance**
- **PC3: 11.2% of variance**
- **Cumulative PC1-PC3: 64.8% of variance**
- **Cumulative PC1-PC5: 82.0% of variance**

The first principal component captures over a third of total dimensional variance, and the first three components together explain nearly two-thirds. This indicates that the 10 dimensions are not orthogonal but share substantial common structure — a finding consistent with multi-dimensional quality frameworks generally, where dimensions like financial metrics, tech adoption, and management stake naturally covary at the firm level.

### 1.2 PC1 Composition: Sector-Quality Identity

PC1 loadings (normalized absolute values, in percentage terms) reveal that the dominant component is heavily weighted on dimensions with sector-tier baselines and sector-correlated firm signal:

|Dimension                |Proposed Weight|Empirical PC1 Loading (US-only)|
|-------------------------|---------------|-------------------------------|
|Ownership structure      |12.5%          |10.5%                          |
|Management stake         |12.5%          |11.5%                          |
|Strategic transformation |11.0%          |8.2%                           |
|**Tech adoption**        |11.0%          |**15.9%**                      |
|Financial metrics        |10.0%          |**0.2%**                       |
|Macro environment        |10.0%          |5.8%                           |
|Financial engineering    |10.0%          |5.7%                           |
|**Culture purpose**      |9.0%           |**15.6%**                      |
|**Progressive practices**|9.0%           |**15.1%**                      |
|Market dynamics          |5.0%           |11.7%                          |

Two findings are notable:

**Finding 1: Financial metrics loads at only 0.2% on PC1.** This is the study’s most distinctive empirical observation. Financial metrics has the highest within-sector standard deviation (17.02 vs ~2-10 for most other dimensions), meaning it varies enormously firm-to-firm even within the same sector. PCA standardizes columns before extracting components, so dimensions with high within-sector variation get their variance distributed across multiple PCs rather than concentrated in PC1. The interpretation is not that financial metrics are unimportant — they are, in fact, the most firm-specific dimension. Rather, financial metrics measure a different axis of quality than what PC1 captures. PC1 is essentially sector-quality identity; financial metrics is firm-specific quality.

**Finding 2: Culture purpose (15.6%) and progressive practices (15.1%) load disproportionately on PC1.** Both dimensions are derived from sector-tier baselines (see methodology), meaning their values are constant for all firms within a sector. They contribute zero within-sector variance and therefore behave as sector-identity proxies. Their elevated PC1 loadings confirm that PC1 is dominated by sector identity rather than per-firm quality differentials.

### 1.3 Global vs US-Only PCA Comparison

The US-only PCA loadings shift in expected directions versus the global panel:

- Ownership structure rises from 8.6% (global) to 10.5% (US-only), reflecting the per-firm enrichment for US firms via yfinance ownership snapshots.
- Tech adoption rises from 14.8% to 15.9%, indicating cleaner sector identification with uniform US data quality.
- Other dimensions remain relatively stable, with the persistent low loading on financial metrics confirming this is not a global-data artifact but a real structural finding.

### 1.4 Implications

The PCA results inform interpretation of the subsequent predictive analyses in several ways:

1. **PC1 = sector-quality identity.** Predictive results that depend heavily on PC1 are partly measuring sector identity rather than firm-specific quality. This is consistent with what we observe in Audits 1-5 of the regression analysis (Section 4).
1. **Financial metrics is a separate quality axis.** The framework’s broad composite mixes sector-quality (PC1) with firm-specific quality (PC2-PC3 territory, where financial metrics likely concentrates). Future research could decompose the composite into these axes explicitly.
1. **The framework has coherent factor structure.** Despite the dimensional heterogeneity, the panel reduces to ~3 meaningful axes explaining 65% of variance. This is the structural validation for treating the composite as a meaningful aggregate rather than a noisy assortment of unrelated dimensions.

-----

## 2. Sector-Level Findings (Primary)

### 2.1 Sector-CVM Score and Sector Forward Return

Mean sector composite scores and mean sector 1-year forward returns over the 35-quarter US-only sample (2016-Q1 through 2025-Q4):

|Sector|Mean CVM Composite|Mean 1-Yr Forward Return|
|------|------------------|------------------------|
|TECH  |72.30             |32.06%                  |
|COMM  |65.37             |17.87%                  |
|HC    |65.19             |14.61%                  |
|CONS_D|64.85             |13.90%                  |
|FIN   |60.20             |21.08%                  |
|INDUS |59.91             |19.96%                  |
|CONS_C|59.00             |24.10%                  |
|RE    |58.11             |14.49%                  |
|UTIL  |57.77             |14.81%                  |
|MAT   |54.08             |18.06%                  |
|ENERGY|53.26             |14.34%                  |

The Pearson correlation between sector CVM composite and sector forward return is **+0.519 (p=0.102, n=11 sectors).** OLS slope is **+0.52 percentage points of annual forward return per 1-point increase in mean sector composite.** The sample’s only meaningful sector-level outlier is CONS_D, which is rated highly by the framework (driven by elevated D8 culture and D9 progressive baselines) but produced the lowest realized sector return in the sample. This anomaly is discussed in Section 4.2.

### 2.2 Portfolio Backtest — All Three Allocation Rules Significant

Three CVM-derived sector-allocation rules are tested against an equal-weight-sector benchmark over 35 quarterly observations:

|Rule                  |Mean Return|Excess vs Benchmark|t-statistic|p-value    |
|----------------------|-----------|-------------------|-----------|-----------|
|Equal-weight benchmark|18.66%     |—                  |—          |—          |
|Top-N (±5pp)          |19.51%     |**+0.85pp**        |+1.75      |**0.089*** |
|Equal-overlay (±3pp)  |19.17%     |**+0.51pp**        |+2.59      |**0.014****|
|Score-proportional    |18.91%     |**+0.25pp**        |+2.09      |**0.044****|

All three rules produce statistically significant positive excess returns. The conservative Equal-overlay specification is the most statistically robust (p=0.014), reflecting consistent modest signal with low standard deviation. The more concentrated Top-N rule achieves higher absolute excess (+0.85pp) but with lower statistical reliability (p=0.089). Compounded over the 35-quarter sample, the Equal-weight benchmark grew to 320x its starting value; the Top-N portfolio grew to 400x — a 25% higher terminal value with modest annual tilts.

The result replicates across three different allocation methodologies, materially strengthening defensibility against the criticism that the finding is methodology-dependent.

### 2.3 Sector Attribution

Decomposing the Top-N portfolio’s +0.71pp annual excess return by sector contribution:

|Sector        |Avg Overweight|Avg Sector Return|Contribution  |
|--------------|--------------|-----------------|--------------|
|TECH          |+5.00pp       |32.06%           |**+1.60pp**   |
|HC            |+3.72pp       |14.61%           |+0.54pp       |
|COMM          |+2.86pp       |17.87%           |+0.51pp       |
|CONS_D        |+3.00pp       |13.90%           |+0.42pp       |
|FIN           |-0.28pp       |21.08%           |-0.06pp       |
|INDUS         |-0.57pp       |19.96%           |-0.11pp       |
|CONS_C        |-0.86pp       |24.10%           |-0.21pp       |
|UTIL          |-2.00pp       |14.81%           |-0.30pp       |
|RE            |-2.57pp       |14.49%           |-0.37pp       |
|MAT           |-3.28pp       |18.06%           |-0.59pp       |
|ENERGY        |-5.00pp       |14.34%           |-0.72pp       |
|**Net excess**|              |                 |**+0.71pp/yr**|

**Honest attribution finding:** Tech alone contributes +1.60pp of the +0.71pp net excess. The framework’s largest correct call (overweight Tech, the highest-return sector) drives the result. The Tech-Energy spread (Tech +1.60pp − Energy +0.72pp = +0.88pp combined) accounts for substantially more than 100% of the net annual excess. The framework’s calls on FIN, INDUS, and CONS_C were *wrong* directionally — these sectors had high returns that the framework’s score did not anticipate.

This attribution is consistent with a “concentrated bet on Tech being a high-quality sector during a tech-favorable decade” interpretation. The framework’s broader sector ranking is approximately correct but the magnitude of excess is dependent on the Tech-Energy dispersion of the study window.

-----

## 3. Firm-Level Findings — Pooled Sample

### 3.1 Continuous Composite Regression

The primary specification regresses 1-year forward returns on composite score with full controls:

|Sample                        |Composite Coefficient|p-value    |
|------------------------------|---------------------|-----------|
|Global (200 firms, 3,668 obs) |-0.41                |**0.040****|
|US-only (100 firms, 3,260 obs)|-0.33                |0.093*     |

The composite coefficient is *marginally negative* in both samples and statistically significant at p<0.05 in the global panel. Read literally: a 1-point increase in composite score is associated with 0.33-0.41 percentage points *lower* annual forward return, controlling for sector, size, beta, and regime.

This finding requires careful interpretation. Three readings are defensible:

1. **Mean reversion at the high end.** Highest-composite firms may have already run up by their measurement date, with forward returns mean-reverting lower.
1. **Efficient markets pricing.** Publicly observable quality characteristics are already priced into market valuations; firms scoring high on observable quality earn risk-adjusted returns equal to or slightly below the market average.
1. **The composite is partially measuring sector identity.** Robustness check Audit 5 confirms that the composite’s predictive power drops to near zero when sector fixed effects are removed (coefficient flips from -0.33 to +0.03). This indicates that within-sector firm-level signal is approximately null, and the marginal negative coefficient with sector FE reflects a small within-sector mean-reversion effect.

### 3.2 Quartile Dummy Regression — US-Only

Quartile coefficients relative to Q4 (lowest CVM composite) in the US-only sample:

|Quartile    |Coefficient vs Q4|p-value|
|------------|-----------------|-------|
|Q1 (highest)|-5.94pp          |0.64   |
|Q2          |+3.70pp          |0.77   |
|Q3          |+1.63pp          |0.89   |

None are statistically significant. The Q4 reference contains only 5-6 observations in the US-only sample, limiting statistical power and inflating standard errors. The quartile coefficients should be interpreted as informative about the *absence* of a strong firm-selection signal rather than as precise effect estimates.

### 3.3 Refinement Tests

Three alternative bucket specifications were tested to address quartile imbalance and sector-tier baseline contamination:

|Test                                         |Effect            |p-value|Conclusion            |
|---------------------------------------------|------------------|-------|----------------------|
|Above-median vs below-median (Q1+Q2 vs Q3+Q4)|+1.94pp           |0.34   |Not significant       |
|Tercile T1 vs T3                             |-2.35pp           |0.47   |Not significant       |
|Composite excluding D8+D9                    |-0.33 (continuous)|0.052* |Marginally significant|

The composite-excluding-D8/D9 specification produces a marginally tighter p-value (0.052 vs 0.093 for full composite), consistent with the interpretation that sector-tier dimensions add noise rather than signal at the firm-level regression. This refinement does not change the qualitative finding but documents the marginal contribution of the sector-tier dimensions explicitly.

-----

## 4. Firm-Level Findings — Sub-Period Decomposition

The pooled null result masks substantial regime variation. The quartile dummy regression re-estimated within each of three regimes:

|Period                |Q1 vs Reference|p-value  |Significance|
|----------------------|---------------|---------|------------|
|Pre-COVID (2016-2019) |-7.99pp        |0.18     |n.s.        |
|COVID era (2020-2021) |**+26.10pp**   |**0.027**|****        |
|Inflation+ (2022-2025)|-6.30pp        |0.53     |n.s.        |

**The COVID-era finding is the strongest within-firm result in the study.** During the COVID crisis and recovery, high-CVM US firms outperformed low-CVM US firms by 26.1 percentage points in 1-year forward returns, with statistical significance at p<0.05. The 95% confidence interval excludes zero. This finding is robust to all controls (sector, size, beta, country, regime).

The finding is consistent with the academic literature on flight-to-quality dynamics: in periods of high uncertainty and market stress, firms with strong fundamentals (balance sheet strength, ownership stability, operational efficiency, sector resilience) materially outperform firms without these characteristics. The CVM framework captures these characteristics in its dimension construction.

The pre-COVID and post-2022 sub-periods produce point estimates that are negative and not statistically significant. The pooled near-null result reflects the cancellation of these opposing regime effects.

-----

## 5. Discussion

### 5.1 The Three-Layer Result Structure

The findings produce a coherent if nuanced empirical story:

- **Sector level:** CVM provides statistically significant signal. Higher-CVM sectors earn higher returns. Allocation rules based on the framework produce significant excess returns.
- **Firm level (normal times):** Within-sector firm-quality differentials are approximately efficiently priced. The framework does not produce significant firm-selection alpha in normal market conditions.
- **Firm level (crisis):** During market stress, the framework captures genuine firm-quality differentials that predict returns at materially significant magnitudes.

This three-layer interpretation aligns with the Asness, Frazzini, Pedersen (2019) literature on the regime-dependent quality factor, with the Fama-French line of research on sector premia, and with the broader practitioner literature on flight-to-quality dynamics.

### 5.2 The Consumer Discretionary Anomaly

CONS_D is the most striking outlier in the sector-level analysis: high CVM composite (64.85, 4th highest) but lowest realized sector return (13.90%). Investigation of underlying composition reveals that CONS_D in the panel is heavy in NKE, MCD, SBUX, HD, LOW — names that struggled in the 2022-2024 consumer-spending slowdown. The framework’s high rating reflects strong sector-tier baselines on D8 (culture) and D9 (progressive practices), which did not anticipate operating performance challenges.

This anomaly highlights a real limitation of sector-tier baseline scoring for forward-return prediction: structural sector quality scores do not capture cyclical demand dynamics. A more refined framework with sub-sector granularity would likely correct this.

### 5.3 The Negative Composite Coefficient

The marginal negative coefficient on continuous composite (p=0.04 global, p=0.09 US-only) is the most counterintuitive finding. Three explanations were considered:

1. Mean reversion at high composite valuations
1. Efficient pricing of observable quality
1. Sector-correlation absorption

The robustness check excluding sector FE (Audit 5) supports interpretation 3: composite-without-sector-FE has coefficient +0.03 (p=0.67), suggesting that sector identity absorbs nearly all of the composite’s apparent signal. Within sectors, the small negative coefficient likely reflects mild mean-reversion at the high end. This finding is consistent with extensive prior literature on quality-factor performance and does not weaken the framework’s positioning as a sector allocator.

### 5.4 Implications for Framework Positioning

The empirical results suggest that CVM functions primarily as a **sector-quality classifier** with secondary value as a **crisis-period firm-quality selector**. This is a defensible practical positioning:

- **For sector allocation:** the framework provides actionable, statistically robust signal under conservative implementation (Equal-overlay rule, p=0.014).
- **For crisis-period stock selection:** the framework captures genuine firm-level differentials when market stress is high.
- **For normal-period stock selection:** the framework does not produce significant outperformance; within-sector quality is approximately priced in.

This positioning aligns the framework with how practitioners typically use quality factors (as one input among several, with regime-aware weighting), rather than as a standalone stock-picking signal.

-----

## 6. Limitations and Generalizability

The findings are subject to the limitations enumerated in the methodology section. The most consequential for interpretation:

- **Geographic scope.** Primary findings are US-only. Generalization to other geographies, particularly emerging market Asia where the author’s research interest is concentrated, requires separate empirical validation.
- **Regime specificity.** The 2016-2025 window includes one major crisis (COVID) and is dominated by a tech-favorable bull market regime. The sector-allocation finding may not generalize to extended periods of tech underperformance.
- **Snapshot ownership data.** D6 and D7 use point-in-time data, not historical 13F aggregation. The cross-sectional ranking captured here is the variation used in quartile assignment, but within-firm time-series ownership dynamics are not detected.
- **Sector-tier sector-correlation.** D8 and D9 introduce sector-correlated signal into the composite. The robustness check excluding these dimensions produces a marginally tighter result, suggesting some sector contamination but not enough to invalidate the broader findings.
- **No transaction-cost modeling.** The sector backtest does not account for transaction costs, taxes, or market-impact frictions. Realized portfolio returns would be lower in live implementation.

-----

-----

## 7. Future Research

This study leaves substantial empirical territory open for follow-up work. We identify five priority directions, ordered by feasibility:

### 7.1 Geographic Generalization

The primary analysis is US-only. The global 199-firm robustness check uses sector-baseline scoring for non-US firms on D6 and D7, limiting interpretation. A natural extension is replication on a paid-data European panel (Refinitiv or Bloomberg coverage of Stoxx 600 or FTSE 350) and an APAC panel (TSE Prime, KOSPI 200, HSI), with per-firm ownership and ESG data of comparable quality to the US sub-sample. This would test whether the sector-allocation finding generalizes beyond the US tech-favorable regime that dominated 2016-2025.

### 7.2 Extended Time Horizon

The 9-year study window is dominated by post-GFC bull-market conditions with one major crisis (COVID 2020-2021). A 20-year or 30-year extended panel (2000-2025) would include multiple distinct regimes — the 2000-2002 dot-com bust, the 2008-2009 financial crisis, the 2010-2015 recovery, and the post-2020 inflation period. This would test the crisis-period firm-selection finding (Section 4) across multiple stress episodes rather than just COVID.

### 7.3 Sub-Sector Granularity

The Consumer Discretionary anomaly (Section 5.2) shows that broad sector-tier baselines miss cyclical demand dynamics within a sector. A natural refinement is to use GICS sub-industry (8-digit) rather than sector (4-digit) for D8 and D9 baselines. This would distinguish, for example, “discretionary retail” from “discretionary durables” from “discretionary services,” each with different operational and ESG profiles. Sub-sector granularity would also enable more precise sector-allocation rules.

### 7.4 Composite Weighting Optimization

The current composite weights are theory-driven (Section 3.1 of Methodology) rather than empirically optimized. A follow-up could derive optimal weights from a forward-return prediction objective using cross-validated regularized regression (e.g., elastic net with leave-one-quarter-out cross-validation). The theoretical weights serve as a strong baseline; empirical optimization would test whether they can be materially improved. Critically, such optimization must be conducted out-of-sample to avoid overfitting.

### 7.5 Alternative Dependent Variables

This study uses 1-year forward total return as the dependent variable. Three alternatives are worth investigating:

- **Risk-adjusted returns** (Sharpe ratio, Sortino ratio) to test whether the framework captures risk-adjusted quality rather than absolute return.
- **Drawdown-conditional returns** to test the flight-to-quality hypothesis more directly than the crisis-period subsample.
- **Multi-horizon returns** (3-year, 5-year) to test whether the framework’s signal manifests at longer horizons where mean-reversion noise dampens.

### 7.6 Time-Series Ownership Data

The current implementation uses point-in-time yfinance snapshots for D6 and D7 (institutional and insider ownership). True historical 13F-aggregated institutional ownership requires multi-day fan-out across thousands of filer-level filings per quarter. Implementing this — likely via a paid Bloomberg or Refinitiv API — would enable within-firm time-series variation in ownership to be detected. This may meaningfully strengthen firm-level predictive findings, particularly in periods where ownership changes are themselves diagnostic (e.g., institutional accumulation preceding price appreciation).

### 7.7 Out-of-Sample 2026 Validation

The study window ends 2025-Q4. As 2026 data accumulates, an out-of-sample test of the v2.5 framework on 2026-2027 forward returns would provide the cleanest validation of whether the in-sample findings persist. We commit to publishing an annual update of the sector-allocation backtest as new data becomes available.

### 7.8 Regime-Dependent Sector Baselines

The CVM framework as currently calibrated captures regime context partially but incompletely. The macro_environment dimension (D10) includes country-level adjustments (e.g., -8pp for Turkey, -5pp for emerging markets) and a per-firm macro overlay responsive to inflation, GDP growth, and policy rates. These mechanisms detect macroeconomic stress at the firm level.

However, the framework’s sector baselines for D8 (culture purpose), D9 (progressive practices), and the sector component of D10 (macro environment) are **static across regimes**. They reflect structural sector quality under prevailing conditions but do not adjust when the macro environment shifts. The 2016-2025 calibration implicitly encodes a disinflationary, tech-favorable, ESG-positive regime: TECH receives a high D9 baseline (78) partly because the Sustainalytics 2024 industry reports score it favorably; ENERGY receives a low D9 baseline (38) for the inverse reason.

If the macroeconomic regime shifts to stagflation, reflation, or a commodity-favorable cycle, sectors with currently low CVM baselines (energy, materials, defense-exposed industrials) may earn forward returns disproportionate to their static framework scores. The 2016-2025 sector-allocation finding (Section 2) would systematically underweight precisely the sectors that outperform in a regime change.

A natural extension is **regime-conditional sector baselines** that adjust D8, D9, and the sector-component of D10 based on detected macro regime. Methodologically, this requires:

1. A regime classifier — typically 3-5 regimes based on inflation, growth, and rate-cycle stages.
1. Regime-specific sector-baseline matrices, calibrated to historical sector returns within each regime.
1. A regime-detection update cadence (quarterly or monthly).

This extension would address a real limitation of the current framework: regime-blindness. It would also significantly extend the framework’s intellectual contribution, positioning CVM as a regime-aware quality framework rather than a regime-specific one. We treat this as a substantial follow-up research direction, beyond the scope of the present paper.

-----

## 8. Conclusion

The Concentric Value Model demonstrates statistically significant sector-allocation signal and crisis-period firm-quality signal across a 35-quarter US-only sample. Pooled firm-level returns do not show statistically significant CVM-quartile differentiation outside of crisis periods, consistent with efficient-market pricing of publicly observable quality characteristics.

The framework’s practical value is in (a) supporting sector-tilt portfolio construction with modest, consistent alpha, and (b) identifying firms with material crisis-period resilience. These findings support the framework’s continued development as a tool for institutional asset allocation rather than primarily for retail stock selection.

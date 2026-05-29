"""
cvm_research.stats — Statistical analysis utilities.

Implements:
  - Panel regression with all five controls (sector, country, log market cap,
    beta, regime dummies). Zero-variance dummies are dropped automatically
    before estimation to avoid silent collinearity failures.
  - Quartile portfolio aggregation and Q1-minus-Q4 spread series
  - Cluster-robust standard errors (clustered by quarter-end date)
  - Sharpe-ratio and risk-adjusted return helpers
  - Significance stars and clean DataFrame outputs for the thesis appendix
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


# ============================================================================
# QUARTILE PORTFOLIO AGGREGATION
# ============================================================================

def build_quartile_portfolios(panel: pd.DataFrame,
                              return_col: str = "forward_return_pct") -> pd.DataFrame:
    """Aggregate firm-quarter panel into quartile-quarter equal-weighted portfolios.

    For each (as_of, quartile) cell, compute the mean forward return across all
    firms in that quartile at that quarter-end. Equal-weighted within quartile.
    """
    df = panel.dropna(subset=[return_col]).copy()
    grouped = df.groupby(["as_of", "quartile"]).agg(
        mean_return=(return_col, "mean"),
        median_return=(return_col, "median"),
        n_firms=(return_col, "count"),
        std_return=(return_col, "std"),
    ).reset_index()
    return grouped


def quartile_spread_series(quartile_portfolios: pd.DataFrame) -> pd.DataFrame:
    """Time series of Q1-minus-Q4 long-short spread returns."""
    pivot = quartile_portfolios.pivot(index="as_of", columns="quartile", values="mean_return")
    pivot["Q1_minus_Q4"] = pivot.get("Q1", pd.Series()) - pivot.get("Q4", pd.Series())
    return pivot.reset_index()


# ============================================================================
# REGIME DUMMIES
# ============================================================================

def add_regime_dummies(panel: pd.DataFrame, date_col: str = "as_of") -> pd.DataFrame:
    """Add binary indicators for COVID-2020 and the 2022-2023 inflation/hiking regime.

    Definitions (defensible to a thesis reviewer):
      - covid_regime: 1 if as_of in 2020-Q1 through 2020-Q4 (calendar)
      - inflation_regime: 1 if as_of in 2022-Q1 through 2023-Q2
        (Fed hiking cycle: Mar 2022 - mid 2023)
    """
    panel = panel.copy()
    d = pd.to_datetime(panel[date_col])
    panel["covid_regime"] = ((d >= "2020-01-01") & (d <= "2020-12-31")).astype(int)
    panel["inflation_regime"] = ((d >= "2022-01-01") & (d <= "2023-06-30")).astype(int)
    return panel


# ============================================================================
# REGRESSION HELPERS
# ============================================================================

def _drop_zero_variance_dummies(df: pd.DataFrame, candidate_cols: list[str]) -> list[str]:
    """Return the subset of candidate columns that have variance > 0.

    A dummy with no variance (all 1s or all 0s) is perfectly collinear with
    the intercept and causes statsmodels to silently drop it. We do the drop
    explicitly so the formula reflects what was actually estimated.
    """
    keep = []
    dropped = []
    for c in candidate_cols:
        if c not in df.columns:
            dropped.append((c, "missing"))
            continue
        col = df[c].dropna()
        if len(col) == 0 or col.nunique() < 2:
            dropped.append((c, "zero variance"))
            continue
        keep.append(c)
    if dropped:
        print(f"  ⚠ Dropped controls (zero variance or missing): {dropped}")
    return keep


def run_panel_regression(
    panel: pd.DataFrame,
    return_col: str = "forward_return_pct",
    composite_col: str = "composite",
    cluster_by: str = "as_of",
    verbose: bool = True,
):
    """Estimate forward_return_pct ~ composite + 5 controls.

    Specification:
      forward_return ~ composite
                     + C(sector)            # sector fixed effects
                     + C(country)           # country fixed effects
                     + log_mcap             # market cap (size)
                     + beta                 # market beta
                     + covid_regime         # 2020 dummy
                     + inflation_regime     # 2022-2023 dummy

    Standard errors clustered by quarter-end date.
    Returns the fitted statsmodels OLS results object.
    """
    if not HAS_STATSMODELS:
        raise RuntimeError("statsmodels is required for regression. pip install statsmodels.")

    df = panel.dropna(subset=[return_col, composite_col]).copy()

    # Derive log_mcap if market_cap is present
    if "market_cap" in df.columns:
        df["log_mcap"] = np.log(df["market_cap"].replace(0, np.nan))

    # Identify available controls, dropping zero-variance ones
    candidate_controls = ["sector", "country", "log_mcap", "beta",
                          "covid_regime", "inflation_regime"]
    active_controls = _drop_zero_variance_dummies(df, candidate_controls) if verbose else \
                      [c for c in candidate_controls if c in df.columns]

    # Build formula
    parts = [f"{return_col} ~ {composite_col}"]
    for c in active_controls:
        if c in ("sector", "country"):
            parts.append(f"C({c})")
        else:
            parts.append(c)
    formula = " + ".join(parts)
    if verbose:
        print(f"  Formula: {formula}")

    # Drop NA rows in regressors
    needed_cols = [composite_col] + [c for c in active_controls if c not in ("sector", "country")]
    df = df.dropna(subset=needed_cols)
    if verbose:
        print(f"  N after NA-drop: {len(df)}")

    model = smf.ols(formula, data=df)
    if cluster_by in df.columns:
        results = model.fit(cov_type="cluster", cov_kwds={"groups": df[cluster_by]})
    else:
        results = model.fit(cov_type="HC1")
    return results


def run_quartile_dummy_regression(
    panel: pd.DataFrame,
    return_col: str = "forward_return_pct",
    reference_quartile: str = "auto",
    cluster_by: str = "as_of",
    verbose: bool = True,
):
    """Regress forward return on quartile dummies + controls.

    reference_quartile:
        "auto" (default) — uses the WORST available quartile as the reference
        (Q4 if present, else Q3, else Q2). This makes the other quartile
        coefficients read as "outperformance vs the worst group", which is the
        natural framing for a framework-alpha interpretation. Auto-selection
        prevents the PatsyError that occurs when a hardcoded reference level
        (e.g. 'Q4') is absent from the sample.
        Or pass an explicit level ('Q1'/'Q2'/'Q3'/'Q4').

    The framework alpha is the coefficient on the BEST quartile (Q1) relative
    to the reference. With auto/Q4 reference, look for the [T.Q1] coefficient.
    """
    if not HAS_STATSMODELS:
        raise RuntimeError("statsmodels is required.")

    df = panel.dropna(subset=[return_col, "quartile"]).copy()
    if "market_cap" in df.columns:
        df["log_mcap"] = np.log(df["market_cap"].replace(0, np.nan))

    # Resolve the reference quartile against what's actually present
    present = set(df["quartile"].unique())
    if reference_quartile == "auto":
        for cand in ["Q4", "Q3", "Q2", "Q1"]:  # worst-first
            if cand in present:
                reference_quartile = cand
                break
        if verbose:
            print(f"  Auto-selected reference quartile: {reference_quartile} "
                  f"(present quartiles: {sorted(present)})")
    elif reference_quartile not in present:
        # Requested level absent — fall back gracefully instead of PatsyError
        fallback = sorted(present)[-1]  # worst alphabetically present (Q3>Q2>Q1)
        if verbose:
            print(f"  ⚠ Requested reference '{reference_quartile}' not in sample "
                  f"{sorted(present)}; falling back to '{fallback}'.")
        reference_quartile = fallback

    candidate_controls = ["sector", "country", "log_mcap", "beta",
                          "covid_regime", "inflation_regime"]
    active_controls = _drop_zero_variance_dummies(df, candidate_controls) if verbose else \
                      [c for c in candidate_controls if c in df.columns]

    parts = [f"{return_col} ~ C(quartile, Treatment(reference='{reference_quartile}'))"]
    for c in active_controls:
        if c in ("sector", "country"):
            parts.append(f"C({c})")
        else:
            parts.append(c)
    formula = " + ".join(parts)
    if verbose:
        print(f"  Formula: {formula}")

    needed_cols = [c for c in active_controls if c not in ("sector", "country")]
    df = df.dropna(subset=needed_cols)
    if verbose:
        print(f"  N after NA-drop: {len(df)}")

    model = smf.ols(formula, data=df)
    results = model.fit(cov_type="cluster", cov_kwds={"groups": df[cluster_by]}) \
              if cluster_by in df.columns else model.fit(cov_type="HC1")
    # Stash the reference for downstream interpretation
    results._cvm_reference_quartile = reference_quartile
    return results


# ============================================================================
# SHARPE / RISK-ADJUSTED RETURNS
# ============================================================================

def annualized_sharpe(quarterly_returns: pd.Series, rf_quarterly: float = 0.0) -> float:
    """Sharpe from quarterly returns (in %). Annualize by ×√4."""
    excess = quarterly_returns.dropna() - rf_quarterly
    if len(excess) < 2 or excess.std() == 0:
        return float("nan")
    return float(excess.mean() / excess.std() * np.sqrt(4))


# ============================================================================
# OUTPUT FORMATTING — for thesis appendix
# ============================================================================

def regression_table_summary(results) -> pd.DataFrame:
    """Clean DataFrame of (variable, coef, se, t, p, ci_lower, ci_upper) for thesis."""
    df = pd.DataFrame({
        "variable": results.params.index,
        "coefficient": results.params.values,
        "std_error": results.bse.values,
        "t_stat": results.tvalues.values,
        "p_value": results.pvalues.values,
    })
    ci = results.conf_int()
    df["ci_lower"] = ci.iloc[:, 0].values
    df["ci_upper"] = ci.iloc[:, 1].values
    return df


def sig_stars(p: float) -> str:
    if pd.isna(p):
        return ""
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""

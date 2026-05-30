"""cvm_research.ownership_enrichment — Free ownership + ESG data for the panel.

Adds three columns to the point-in-time panel that the scoring engine
already accepts as enrichment inputs:

  D6 management_stake      ← yfinance heldPercentInsiders (snapshot)
  D7 ownership_structure   ← yfinance heldPercentInstitutions (snapshot)
  D9 progressive_practices ← yfinance Sustainalytics totalEsg (snapshot)

DESIGN CHOICES — read this before interpreting results.

1. Snapshot, not time-series. Per-quarter historical ownership data
   would require fanning out across thousands of Form 13F filers per
   quarter to find every position in each issuer. That's a multi-day
   data engineering job and not feasible for free at this scope.
   We use yfinance's current snapshot instead. The CROSS-SECTIONAL
   ranking (which firms have more insider/institutional ownership)
   is the source of variation that the CVM quartile analysis uses.
   Time-series variation within ticker is NOT captured.

2. US firms only by default. yfinance's institutional/insider coverage
   for non-US tickers is unreliable (often returns None or stale data).
   Non-US firms retain their sector baseline scores on D6/D7.

3. ESG point-in-time discipline. Yahoo Sustainability returns today's
   Sustainalytics rating. Attaching this to a 2017 observation is
   look-ahead contamination. ESG is therefore ONLY attached to
   observations within `esg_recency_months` of the snapshot date
   (default 18 months). Earlier observations retain sector baseline
   on D9, which the scoring engine and thesis chapter should note
   explicitly.

4. Cross-sectional vs time-series interpretation. Because ownership
   values are a snapshot held constant, panel regressions with firm
   fixed effects will not detect within-firm changes in ownership.
   Pooled and cross-sectional regressions (as in nb03) DO use this
   variation. This is documented in nb03's thesis-prose template.
"""
from __future__ import annotations

import logging
from typing import Optional
import pandas as pd

log = logging.getLogger(__name__)


def fetch_insider_pct(ticker: str) -> Optional[float]:
    """Return heldPercentInsiders as a percent (0-100), or None."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        v = info.get("heldPercentInsiders")
        if v is None:
            return None
        v = float(v)
        if abs(v) <= 1:
            v *= 100
        return v if 0 <= v <= 100 else None
    except Exception as e:
        log.warning(f"insider {ticker}: {e}")
        return None


def fetch_institutional_pct(ticker: str) -> Optional[float]:
    """Return heldPercentInstitutions as a percent (0-100), or None."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        v = info.get("heldPercentInstitutions")
        if v is None:
            return None
        v = float(v)
        if abs(v) <= 1:
            v *= 100
        return v if 0 < v <= 100 else None
    except Exception as e:
        log.warning(f"institutional {ticker}: {e}")
        return None


def fetch_esg_risk(ticker: str) -> Optional[float]:
    """Return Sustainalytics ESG risk score, or None.

    Lower = better. Scale: <10 negligible, 10-20 low, 20-30 medium,
    30-40 high, >40 severe. The scoring engine inverts this so lower
    risk → higher dimension score.
    """
    try:
        import yfinance as yf
        sust = yf.Ticker(ticker).sustainability
        if sust is None or len(sust) == 0:
            return None
        for label in ("totalEsg", "esgScore"):
            if label in sust.index:
                v = sust.loc[label]
                if hasattr(v, "iloc"):
                    v = v.iloc[0]
                v = float(v)
                if 0 < v < 100:
                    return v
        return None
    except Exception as e:
        log.warning(f"ESG {ticker}: {e}")
        return None


def enrich_panel_with_ownership(
    panel: pd.DataFrame,
    us_only: bool = True,
    attach_esg: bool = True,
    esg_recency_months: int = 18,
    verbose: bool = True,
) -> pd.DataFrame:
    """Attach insider/institutional/ESG columns to the panel.

    See module docstring for design rationale and limitations.

    Args:
        panel: nb01 output panel (must have ticker, country, as_of columns)
        us_only: only enrich US firms (default; non-US data is unreliable)
        attach_esg: fetch ESG from Yahoo Sustainability
        esg_recency_months: ESG attached only to observations within this many
            months of today, to limit look-ahead contamination
        verbose: print progress

    Returns:
        panel with insider_ownership_pct, institutional_ownership_pct,
        esg_risk columns added (NaN where not available — scoring engine
        will fall to sector baseline for those observations)
    """
    panel = panel.copy()
    panel["insider_ownership_pct"] = pd.NA
    panel["institutional_ownership_pct"] = pd.NA
    panel["esg_risk"] = pd.NA

    if us_only:
        tickers = sorted(panel.loc[panel["country"] == "US", "ticker"].unique())
    else:
        tickers = sorted(panel["ticker"].unique())

    if verbose:
        print(f"Enriching {len(tickers)} tickers (us_only={us_only})...")

    snapshots: dict[str, dict] = {}
    for i, tk in enumerate(tickers):
        if verbose and i % 25 == 0:
            print(f"  [{i:>3}/{len(tickers)}] {tk}")
        snapshots[tk] = {
            "insider": fetch_insider_pct(tk),
            "institutional": fetch_institutional_pct(tk),
            "esg": fetch_esg_risk(tk) if attach_esg else None,
        }

    esg_cutoff = pd.Timestamp.now() - pd.DateOffset(months=esg_recency_months)
    n_ins = n_inst = n_esg = 0
    for tk, snap in snapshots.items():
        mask = panel["ticker"] == tk
        if snap["insider"] is not None:
            panel.loc[mask, "insider_ownership_pct"] = snap["insider"]
            n_ins += int(mask.sum())
        if snap["institutional"] is not None:
            panel.loc[mask, "institutional_ownership_pct"] = snap["institutional"]
            n_inst += int(mask.sum())
        if snap["esg"] is not None and attach_esg:
            recent_mask = mask & (pd.to_datetime(panel["as_of"]) >= esg_cutoff)
            panel.loc[recent_mask, "esg_risk"] = snap["esg"]
            n_esg += int(recent_mask.sum())

    if verbose:
        n_total = len(panel)
        print(f"\nEnrichment complete on {n_total:,} observations:")
        print(f"  insider_ownership_pct:       {n_ins:>5} obs ({100*n_ins/n_total:.1f}%)")
        print(f"  institutional_ownership_pct: {n_inst:>5} obs ({100*n_inst/n_total:.1f}%)")
        print(f"  esg_risk (recent only):      {n_esg:>5} obs ({100*n_esg/n_total:.1f}%)")
        n_snapshots_hit = sum(1 for s in snapshots.values()
                              if s["insider"] is not None or s["institutional"] is not None)
        print(f"\nTickers with ANY ownership data: {n_snapshots_hit}/{len(tickers)}")

        # Diagnostic: which tickers came back completely empty?
        missing = [tk for tk, snap in snapshots.items()
                   if snap["insider"] is None and snap["institutional"] is None]
        if missing:
            print(f"\nTickers with NO yfinance ownership data ({len(missing)}):")
            for tk in missing:
                print(f"  - {tk}")
            print("Possible reasons: delisted, recent ticker change, dual-class structure, "
                  "or temporary yfinance/Yahoo issue. Retry the enrichment cell after a "
                  "few minutes if you suspect transient throttling.")

    return panel

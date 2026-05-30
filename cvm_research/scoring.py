"""
cvm_research.scoring — Python port of the JavaScript scoring engine.

This module is a faithful port of computeDimensions() from index.html
(lines 457-698 in build 2026-05-11.q). Every constant, every multiplier,
every clamp call matches the JS implementation. The verify() function at
the bottom checks agreement against a held-out set of reference cases.

If the JS engine changes in the public tool, this module must be updated
in lockstep. The unit tests in tests/test_parity.py guard against drift.

References:
  - SECTOR_BASELINES: index.html lines 373-386
  - CAP_ADJ:          index.html lines 388-393
  - COUNTRY_ADJ:      index.html lines 395-421
  - computeDimensions: index.html lines 457-698
  - tickerVariance:   index.html lines 442-454
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd


# ============================================================================
# CONSTANTS — ported from index.html, verbatim
# ============================================================================

LAYERS = [
    {"id": "macro",   "weight": 0.10, "dimensions": ["macro_environment"]},
    {"id": "finarch", "weight": 0.20, "dimensions": ["financial_metrics", "financial_engineering"]},
    {"id": "corp",    "weight": 0.22, "dimensions": ["tech_adoption", "strategic_transformation"]},
    {"id": "gov",     "weight": 0.25, "dimensions": ["management_stake", "ownership_structure"]},
    {"id": "org",     "weight": 0.18, "dimensions": ["culture_purpose", "progressive_practices"]},
    {"id": "opt",     "weight": 0.05, "dimensions": ["market_dynamics"]},
]

DIMENSIONS = [
    "macro_environment", "financial_metrics", "financial_engineering",
    "tech_adoption", "strategic_transformation", "management_stake",
    "ownership_structure", "culture_purpose", "progressive_practices",
    "market_dynamics",
]

# Sector baselines — exact port of SECTOR_BASELINES from index.html lines 373-386.
# Keys MUST match what the JS uses, so the ticker list's `sector` column must
# also use these keys (TECH, FIN, HC, CONS_C, CONS_D, ENERGY, INDUS, MAT, COMM, UTIL, RE, ETF).
# SECTOR BASELINES — defensible defaults for every sector × dimension.
# Refreshed annually from public aggregators. Source provenance per dimension:
#   - culture_purpose (D8): Glassdoor sector aggregates (median employer rating);
#     TECH/HC/CONS_D rank highest, ENERGY/FIN/MAT lowest. Re-anchored annually.
#   - progressive_practices (D9): Sustainalytics ESG Risk sector aggregates
#     inverted to 0-100 scale (low risk = high CVM score). 2024 sector ordering:
#     TECH/HC/COMM/CONS_C lowest ESG risk; ENERGY/UTIL/MAT/INDUS highest.
#     Source: Sustainalytics annual sector reports + MSCI ACWI sector reviews,
#     reviewed Jan 2026 for next refresh.
#   - macro_environment, financial_metrics, etc.: derived from market data
#     and fundamental statistics, not externally sourced.
#
# All sector keys (TECH, FIN, HC, CONS_C, CONS_D, ENERGY, INDUS, MAT, COMM, UTIL,
# RE, ETF) must remain in sync with the canonical sector list used in scoring.py
# and the public tool's index.html.
SECTOR_BASELINES = {
    "TECH": {
        "fundamentals": {"pe": 32, "pb": 6.5, "currentRatio": 2.4, "epsCagr": 14, "divYield": 0.6, "shareholderYield": 1.5, "debtEquity": 0.4},
        "dims": {"financial_metrics": 62, "financial_engineering": 70, "tech_adoption": 88, "strategic_transformation": 78, "management_stake": 72, "ownership_structure": 65, "culture_purpose": 75, "progressive_practices": 78, "macro_environment": 60, "market_dynamics": 65},
    },
    "FIN": {
        "fundamentals": {"pe": 12, "pb": 1.4, "currentRatio": None, "epsCagr": 7, "divYield": 3.2, "shareholderYield": 5.5, "debtEquity": None},
        "dims": {"financial_metrics": 70, "financial_engineering": 62, "tech_adoption": 55, "strategic_transformation": 55, "management_stake": 60, "ownership_structure": 62, "culture_purpose": 55, "progressive_practices": 62, "macro_environment": 50, "market_dynamics": 55},
    },
    "HC": {
        "fundamentals": {"pe": 24, "pb": 4.2, "currentRatio": 1.9, "epsCagr": 9, "divYield": 1.8, "shareholderYield": 3.0, "debtEquity": 0.6},
        "dims": {"financial_metrics": 72, "financial_engineering": 68, "tech_adoption": 62, "strategic_transformation": 62, "management_stake": 58, "ownership_structure": 60, "culture_purpose": 70, "progressive_practices": 72, "macro_environment": 72, "market_dynamics": 60},
    },
    "CONS_C": {
        "fundamentals": {"pe": 22, "pb": 4.0, "currentRatio": 1.4, "epsCagr": 8, "divYield": 1.4, "shareholderYield": 2.8, "debtEquity": 0.7},
        "dims": {"financial_metrics": 60, "financial_engineering": 62, "tech_adoption": 60, "strategic_transformation": 62, "management_stake": 55, "ownership_structure": 55, "culture_purpose": 62, "progressive_practices": 68, "macro_environment": 50, "market_dynamics": 55},
    },
    "CONS_D": {
        "fundamentals": {"pe": 21, "pb": 5.5, "currentRatio": 1.2, "epsCagr": 6, "divYield": 2.6, "shareholderYield": 4.5, "debtEquity": 0.8},
        "dims": {"financial_metrics": 75, "financial_engineering": 70, "tech_adoption": 55, "strategic_transformation": 55, "management_stake": 55, "ownership_structure": 60, "culture_purpose": 68, "progressive_practices": 60, "macro_environment": 75, "market_dynamics": 55},
    },
    "ENERGY": {
        "fundamentals": {"pe": 11, "pb": 1.8, "currentRatio": 1.4, "epsCagr": 5, "divYield": 4.0, "shareholderYield": 7.0, "debtEquity": 0.5},
        "dims": {"financial_metrics": 62, "financial_engineering": 60, "tech_adoption": 48, "strategic_transformation": 50, "management_stake": 55, "ownership_structure": 55, "culture_purpose": 50, "progressive_practices": 38, "macro_environment": 45, "market_dynamics": 55},
    },
    "INDUS": {
        "fundamentals": {"pe": 20, "pb": 3.6, "currentRatio": 1.7, "epsCagr": 7, "divYield": 1.8, "shareholderYield": 3.2, "debtEquity": 0.7},
        "dims": {"financial_metrics": 65, "financial_engineering": 65, "tech_adoption": 60, "strategic_transformation": 60, "management_stake": 58, "ownership_structure": 60, "culture_purpose": 60, "progressive_practices": 52, "macro_environment": 60, "market_dynamics": 55},
    },
    "MAT": {
        "fundamentals": {"pe": 15, "pb": 2.4, "currentRatio": 1.7, "epsCagr": 5, "divYield": 2.5, "shareholderYield": 4.0, "debtEquity": 0.6},
        "dims": {"financial_metrics": 62, "financial_engineering": 58, "tech_adoption": 50, "strategic_transformation": 55, "management_stake": 55, "ownership_structure": 55, "culture_purpose": 55, "progressive_practices": 45, "macro_environment": 50, "market_dynamics": 55},
    },
    "COMM": {
        "fundamentals": {"pe": 23, "pb": 3.8, "currentRatio": 1.3, "epsCagr": 8, "divYield": 2.0, "shareholderYield": 3.5, "debtEquity": 1.1},
        "dims": {"financial_metrics": 60, "financial_engineering": 62, "tech_adoption": 75, "strategic_transformation": 65, "management_stake": 62, "ownership_structure": 58, "culture_purpose": 62, "progressive_practices": 70, "macro_environment": 60, "market_dynamics": 60},
    },
    "UTIL": {
        "fundamentals": {"pe": 18, "pb": 1.9, "currentRatio": 1.0, "epsCagr": 4, "divYield": 3.6, "shareholderYield": 3.8, "debtEquity": 1.4},
        "dims": {"financial_metrics": 68, "financial_engineering": 60, "tech_adoption": 50, "strategic_transformation": 50, "management_stake": 52, "ownership_structure": 55, "culture_purpose": 60, "progressive_practices": 48, "macro_environment": 75, "market_dynamics": 50},
    },
    "RE": {
        "fundamentals": {"pe": 30, "pb": 2.1, "currentRatio": 1.1, "epsCagr": 5, "divYield": 4.2, "shareholderYield": 4.5, "debtEquity": 1.2},
        "dims": {"financial_metrics": 62, "financial_engineering": 60, "tech_adoption": 50, "strategic_transformation": 55, "management_stake": 58, "ownership_structure": 60, "culture_purpose": 58, "progressive_practices": 65, "macro_environment": 55, "market_dynamics": 50},
    },
    "ETF": {
        "fundamentals": {"pe": 18, "pb": 2.5, "currentRatio": None, "epsCagr": 6, "divYield": 2.0, "shareholderYield": 2.0, "debtEquity": None},
        "dims": {"financial_metrics": 65, "financial_engineering": 65, "tech_adoption": 60, "strategic_transformation": 60, "management_stake": 50, "ownership_structure": 60, "culture_purpose": 60, "progressive_practices": 60, "macro_environment": 60, "market_dynamics": 60},
    },
}

# Cap-tier adjustments — exact port of CAP_ADJ from index.html lines 388-393
CAP_ADJ = {
    "M": {"financial_metrics": +8, "financial_engineering": +5, "tech_adoption": +3, "strategic_transformation": -2, "management_stake": -5, "market_dynamics": -3},
    "L": {"financial_metrics": +3, "financial_engineering": +2},
    "I": {"financial_metrics": -2, "strategic_transformation": +5, "tech_adoption": +2, "market_dynamics": +3},
    "S": {"financial_metrics": -8, "strategic_transformation": +8, "tech_adoption": +3, "management_stake": +8, "market_dynamics": +5},
}

# Country adjustments — exact port of COUNTRY_ADJ from index.html lines 395-421
COUNTRY_ADJ = {
    "US": {"ownership_structure": +3, "management_stake": +2},
    "GB": {"ownership_structure": +3},
    "DE": {"ownership_structure": +2, "culture_purpose": +2},
    "FR": {"ownership_structure": +2},
    "NL": {"ownership_structure": +3},
    "CH": {"ownership_structure": +3, "financial_engineering": +3},
    "CA": {"ownership_structure": +2},
    "AU": {"ownership_structure": +2},
    "JP": {"ownership_structure": -2, "progressive_practices": -3, "culture_purpose": +3},
    "KR": {"ownership_structure": -5, "management_stake": -3},
    "CN": {"ownership_structure": -10, "management_stake": -5, "macro_environment": -5},
    "HK": {"ownership_structure": -3, "macro_environment": -3},
    "TW": {"ownership_structure": -2, "macro_environment": -3},
    "IN": {"ownership_structure": -5, "management_stake": -3, "strategic_transformation": +3},
    "BR": {"ownership_structure": -7, "macro_environment": -6},
    "MX": {"ownership_structure": -5, "macro_environment": -4},
    "ZA": {"ownership_structure": -5, "macro_environment": -5},
    "TR": {"ownership_structure": -7, "macro_environment": -8},
    "ID": {"ownership_structure": -6, "macro_environment": -4},
    "TH": {"ownership_structure": -4, "macro_environment": -3},
    "SG": {"ownership_structure": +2},
    "SA": {"ownership_structure": -8, "macro_environment": -3},
    "AE": {"ownership_structure": -5},
    "EU": {"ownership_structure": +2},
    "EM": {"ownership_structure": -5, "macro_environment": -5},
}

# Quartile thresholds — exact port of getQuartile() from index.html lines 724-733
QUARTILE_THRESHOLDS = [
    (70, "Q1"),  # High Conviction
    (58, "Q2"),  # Selective Quality
    (45, "Q3"),  # Mixed Signals
    (0,  "Q4"),  # Structural Concerns
]


# ============================================================================
# CORE HELPERS — exact ports from JS
# ============================================================================

def clamp(n: float, lo: float = 0, hi: float = 100) -> int:
    """Port of clamp(n, lo, hi) from index.html line 438. Returns integer
    (JS uses Math.round before clamp implicitly via context, but compute
    site always wraps with Math.round so we always return int)."""
    if n is None or (isinstance(n, float) and math.isnan(n)):
        return int(max(lo, min(hi, 50)))
    return int(max(lo, min(hi, round(n))))


def fnv1a(s: str) -> int:
    """Port of fnv1a hash from index.html line 442.

    JS uses signed-int32 semantics on XOR and float64-precision-losing arithmetic
    on multiply, then `>>> 0` to convert back to uint32. Both quirks must be
    emulated to produce byte-identical hashes.

    JS algorithm:
        h ^= str.charCodeAt(i);           // 32-bit signed XOR
        h = (h * 0x01000193) >>> 0;       // float64 multiply, then ToUint32
    """
    h = 0x811c9dc5  # initial value (signed: -2128831035)
    PRIME = 0x01000193

    for ch in s:
        # XOR — JS uses signed int32 here. Reinterpret h as signed first.
        if h >= 0x80000000:
            h_signed = h - 0x100000000
        else:
            h_signed = h
        h_signed ^= ord(ch)
        # h_signed is now in signed int32 range; multiply with float64 precision loss
        product = float(h_signed) * float(PRIME)
        # JS `>>> 0`: ToInt32 (modular), then reinterpret as uint32.
        # Python int() truncates toward zero. For negative floats we need to
        # match JS's wrap-around behavior: result = (truncated_int) mod 2^32.
        truncated = int(product)  # truncates toward zero
        h = truncated % 0x100000000  # wrap to uint32

    return h


def ticker_variance(ticker: str, dim_id: str, range_val: int) -> int:
    """Port of tickerVariance() from index.html line 450. Deterministic
    pseudo-random offset based on ticker + dimension. Critical: must
    produce identical output to JS for any (ticker, dim) pair."""
    seed = fnv1a((ticker + ":" + dim_id).lower())
    r = (seed % 10000) / 10000
    return round((r - 0.5) * 2 * range_val)


def get_quartile(composite: int) -> str:
    """Port of getQuartile() — returns quartile string (Q1/Q2/Q3/Q4 only,
    drops the name/desc fields used for rendering)."""
    for threshold, label in QUARTILE_THRESHOLDS:
        if composite >= threshold:
            return label
    return "Q4"


def _safe_get(d: Optional[dict], key: str):
    """Like dict.get but normalises None/NaN to None."""
    if d is None:
        return None
    v = d.get(key)
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


# ============================================================================
# CORE SCORING — exact port of computeDimensions()
# ============================================================================

def compute_dimensions(stock: dict, fundamentals: Optional[dict]) -> tuple[dict, dict]:
    """Faithful port of computeDimensions() from index.html lines 457-698.

    Args:
        stock: dict with keys ticker, sector, cap, country
        fundamentals: dict with snake_case keys matching JS (pe, pb, currentRatio, etc.)
                      In Python we accept BOTH camelCase (JS) and snake_case (Phase 1 JSON)
                      to ease cross-source compatibility. If `source == 'demo'`, falls
                      back to pure sector/cap/country baseline.

    Returns:
        (dims, data_driven) — dims is the 10-element dict of scores 0-100,
        data_driven is the dict marking which dimensions used live data.
    """
    sector = stock.get("sector", "INDUS")
    sec = SECTOR_BASELINES.get(sector, SECTOR_BASELINES["INDUS"])
    sec_id = sector  # JS uses sec.id; in JS that's the same as sector key

    # Start from sector dim baselines
    dims = dict(sec["dims"])

    # Cap adjustment (lines 461-463)
    cap = stock.get("cap")
    cap_adj = CAP_ADJ.get(cap, {})
    for k, adj in cap_adj.items():
        if k in dims:
            dims[k] = clamp(dims[k] + adj, 0, 100)

    # Country adjustment (lines 465-467)
    country = stock.get("country")
    cty_adj = COUNTRY_ADJ.get(country, {})
    for k, adj in cty_adj.items():
        if k in dims:
            dims[k] = clamp(dims[k] + adj, 0, 100)

    # Per-ticker variance (lines 470-474). Dampened when live data present.
    def _is_real(v):
        if v is None:
            return False
        if isinstance(v, float) and math.isnan(v):
            return False
        return True
    has_live = (fundamentals is not None and
                fundamentals.get("source") != "demo" and
                any(_is_real(v) for k, v in fundamentals.items() if k != "source"))
    var_range = 2 if has_live else 6
    ticker = stock.get("ticker", "")
    for k in list(dims.keys()):
        dims[k] = clamp(dims[k] + ticker_variance(ticker, k, var_range), 0, 100)

    data_driven: dict = {}
    if not has_live:
        return dims, data_driven

    # Normalise fundamentals — accept BOTH camelCase (JS source) and snake_case (Phase 1 JSON)
    f = _normalise_fundamentals(fundamentals)
    sb = sec["fundamentals"]

    # === FINANCIAL METRICS (Graham's classical) — lines 482-504
    if f.get("pe") is not None and sb.get("pe"):
        pe_delta = (sb["pe"] - f["pe"]) / sb["pe"]
        dims["financial_metrics"] = clamp(dims["financial_metrics"] + round(pe_delta * 14), 0, 100)
        data_driven["financial_metrics"] = True
    if f.get("pb") is not None and sb.get("pb"):
        pb_delta = (sb["pb"] - f["pb"]) / sb["pb"]
        dims["financial_metrics"] = clamp(dims["financial_metrics"] + round(pb_delta * 8), 0, 100)
        data_driven["financial_metrics"] = True
    if f.get("currentRatio") is not None and sb.get("currentRatio"):
        cr_delta = (f["currentRatio"] - sb["currentRatio"]) / sb["currentRatio"]
        dims["financial_metrics"] = clamp(dims["financial_metrics"] + round(cr_delta * 6), 0, 100)
        data_driven["financial_metrics"] = True
    if f.get("operatingMargin") is not None:
        om_anchor = 25 if sec_id == "TECH" else 30 if sec_id == "FIN" else 12 if sec_id == "CONS_D" else 15
        om_delta = (f["operatingMargin"] - om_anchor) / om_anchor
        dims["financial_metrics"] = clamp(dims["financial_metrics"] + round(om_delta * 6), 0, 100)
        data_driven["financial_metrics"] = True

    # === FINANCIAL ENGINEERING — lines 507-537
    if f.get("shareholderYield") is not None and sb.get("shareholderYield"):
        sy_delta = (f["shareholderYield"] - sb["shareholderYield"]) / max(0.5, sb["shareholderYield"])
        dims["financial_engineering"] = clamp(dims["financial_engineering"] + round(sy_delta * 8), 0, 100)
        data_driven["financial_engineering"] = True
    if f.get("roe") is not None:
        roe_anchor = 20 if sec_id == "TECH" else 12 if sec_id == "FIN" else 10 if sec_id == "UTIL" else 15
        roe_delta = (f["roe"] - roe_anchor) / max(5, roe_anchor)
        dims["financial_engineering"] = clamp(dims["financial_engineering"] + round(roe_delta * 8), 0, 100)
        data_driven["financial_engineering"] = True
    if f.get("debtEquity") is not None:
        de_anchor = 1.5 if sec_id == "FIN" else 1.4 if sec_id == "UTIL" else 1.2 if sec_id == "RE" else 0.6
        de_delta = (de_anchor - f["debtEquity"]) / max(0.3, de_anchor)
        dims["financial_engineering"] = clamp(dims["financial_engineering"] + round(de_delta * 6), 0, 100)
        data_driven["financial_engineering"] = True
    if f.get("payoutRatio") is not None:
        pr = f["payoutRatio"]
        pr_adj = 0
        if 30 <= pr <= 60:
            pr_adj = 3
        elif pr > 100:
            pr_adj = -8
        elif pr > 80:
            pr_adj = -4
        dims["financial_engineering"] = clamp(dims["financial_engineering"] + pr_adj, 0, 100)
        data_driven["financial_engineering"] = True

    # === STRATEGIC TRANSFORMATION — lines 540-570
    if f.get("epsCagr") is not None and sb.get("epsCagr"):
        g_delta = (f["epsCagr"] - sb["epsCagr"]) / max(1, abs(sb["epsCagr"]))
        dims["strategic_transformation"] = clamp(dims["strategic_transformation"] + round(g_delta * 8), 0, 100)
        dims["financial_metrics"] = clamp(dims["financial_metrics"] + round(g_delta * 4), 0, 100)
        data_driven["strategic_transformation"] = True
    if f.get("epsCagr") is None and f.get("quarterlyEarningsGrowth") is not None:
        anchor = sb.get("epsCagr") or 8
        q_delta = (f["quarterlyEarningsGrowth"] - anchor) / max(2, abs(anchor))
        dims["strategic_transformation"] = clamp(dims["strategic_transformation"] + round(q_delta * 5), 0, 100)
        data_driven["strategic_transformation"] = True
    if f.get("quarterlyRevenueGrowth") is not None:
        rg_delta = (f["quarterlyRevenueGrowth"] - 5) / 10
        dims["strategic_transformation"] = clamp(dims["strategic_transformation"] + round(rg_delta * 3), 0, 100)
        data_driven["strategic_transformation"] = True
    # Fallback: ROE + D/E proxy when no growth data
    if not data_driven.get("strategic_transformation") and f.get("roe") is not None and f.get("debtEquity") is not None:
        roe_anchor = 18 if sec_id == "TECH" else 11 if sec_id == "FIN" else 9 if sec_id == "UTIL" else 13
        roe_delta = (f["roe"] - roe_anchor) / max(5, roe_anchor)
        dims["strategic_transformation"] = clamp(dims["strategic_transformation"] + round(roe_delta * 6), 0, 100)
        data_driven["strategic_transformation"] = True

    # === MARKET DYNAMICS — lines 573-593
    if f.get("beta") is not None:
        beta_penalty = round((f["beta"] - 1.0) * -6)
        dims["market_dynamics"] = clamp(dims["market_dynamics"] + beta_penalty, 0, 100)
        data_driven["market_dynamics"] = True
    if f.get("priceInRange") is not None:
        pos = f["priceInRange"]
        if 0.3 <= pos <= 0.7:
            range_adj = 4
        elif 0.7 <= pos <= 0.9:
            range_adj = 1
        elif pos > 0.9:
            range_adj = -3
        elif 0.1 <= pos <= 0.3:
            range_adj = -1
        else:
            range_adj = -5
        dims["market_dynamics"] = clamp(dims["market_dynamics"] + range_adj, 0, 100)
        data_driven["market_dynamics"] = True

    # === MANAGEMENT STAKE — lines 596-606
    if f.get("insiderOwnershipPct") is not None:
        ins = f["insiderOwnershipPct"]
        if ins >= 20:
            adj = 18
        elif ins >= 10:
            adj = 12
        elif ins >= 5:
            adj = 6
        elif ins >= 1:
            adj = 0
        else:
            adj = -6
        dims["management_stake"] = clamp(dims["management_stake"] + adj, 0, 100)
        data_driven["management_stake"] = True

    # === OWNERSHIP STRUCTURE — lines 609-619
    if f.get("institutionalOwnershipPct") is not None:
        inst = f["institutionalOwnershipPct"]
        if 40 <= inst <= 80:
            adj = 8
        elif 80 < inst <= 95:
            adj = 3
        elif inst > 95:
            adj = -4
        elif 20 <= inst < 40:
            adj = 4
        else:
            adj = -2
        dims["ownership_structure"] = clamp(dims["ownership_structure"] + adj, 0, 100)
        data_driven["ownership_structure"] = True

    # === TECH ADOPTION — lines 622-632
    if f.get("rdIntensity") is not None:
        rd = f["rdIntensity"]
        if rd >= 15:
            adj = 15
        elif rd >= 8:
            adj = 10
        elif rd >= 4:
            adj = 5
        elif rd >= 1:
            adj = 0
        else:
            adj = -4
        dims["tech_adoption"] = clamp(dims["tech_adoption"] + adj, 0, 100)
        data_driven["tech_adoption"] = True

    # === MACRO ENVIRONMENT — lines 635-661
    has_macro = (f.get("macroRate") is not None or f.get("macroGdp") is not None
                 or f.get("macroInflation") is not None)
    if has_macro:
        adj = 0
        signals = 0
        if f.get("macroRate") is not None:
            if f["macroRate"] < 3:
                adj += 4
            elif f["macroRate"] > 5:
                adj -= 4
            signals += 1
        if f.get("macroGdp") is not None:
            if f["macroGdp"] >= 2.5:
                adj += 6
            elif f["macroGdp"] < 0:
                adj -= 8
            elif f["macroGdp"] < 1:
                adj -= 3
            signals += 1
        if f.get("macroInflation") is not None:
            if f["macroInflation"] > 6:
                adj -= 5
            elif f["macroInflation"] < 1:
                adj -= 2
            elif 1.5 <= f["macroInflation"] <= 3:
                adj += 3
            signals += 1
        if signals > 0:
            dims["macro_environment"] = clamp(dims["macro_environment"] + adj, 0, 100)
            data_driven["macro_environment"] = True

    # === CULTURE & PURPOSE — lines 664-678
    if f.get("glassdoorRating") is not None or f.get("glassdoorRecommend") is not None:
        adj = 0
        if f.get("glassdoorRating") is not None:
            delta = f["glassdoorRating"] - 3.5
            adj += round(delta * 10)
        if f.get("glassdoorRecommend") is not None:
            delta = (f["glassdoorRecommend"] - 65) / 10
            adj += round(delta * 2)
        dims["culture_purpose"] = clamp(dims["culture_purpose"] + adj, 0, 100)
        data_driven["culture_purpose"] = True

    # === PROGRESSIVE PRACTICES — lines 681-692
    if f.get("esgRisk") is not None:
        risk = f["esgRisk"]
        if risk < 10:
            adj = 12
        elif risk < 20:
            adj = 6
        elif risk < 30:
            adj = 0
        elif risk < 40:
            adj = -6
        else:
            adj = -12
        dims["progressive_practices"] = clamp(dims["progressive_practices"] + adj, 0, 100)
        data_driven["progressive_practices"] = True

    return dims, data_driven


def compute_layer_scores(dims: dict) -> dict:
    """Port of computeLayerScores() from index.html lines 700-711."""
    layer_scores = {}
    for layer in LAYERS:
        total, count = 0, 0
        for dim_id in layer["dimensions"]:
            if dim_id.startswith("_"):
                continue
            if dims.get(dim_id) is not None:
                total += dims[dim_id]
                count += 1
        layer_scores[layer["id"]] = round(total / count) if count else 50
    return layer_scores


def compute_composite(layer_scores: dict) -> int:
    """Port of computeComposite() from index.html lines 713-722."""
    total = 0.0
    weight_sum = 0.0
    for layer in LAYERS:
        if layer_scores.get(layer["id"]) is not None:
            total += layer_scores[layer["id"]] * layer["weight"]
            weight_sum += layer["weight"]
    return round(total / weight_sum) if weight_sum > 0 else 50


# ============================================================================
# FIELD NAME NORMALISATION
# ============================================================================

# Maps Phase 1 snake_case JSON keys → JS camelCase. The compute_dimensions
# function operates on camelCase internally to match the JS port exactly.
_SNAKE_TO_CAMEL = {
    "pe": "pe", "pb": "pb", "peg": "peg", "eps": "eps",
    "current_ratio": "currentRatio",
    "debt_equity": "debtEquity",
    "roe": "roe",
    "operating_margin": "operatingMargin",
    "profit_margin": "profitMargin",
    "payout_ratio": "payoutRatio",
    "div_yield": "divYield",
    "five_year_avg_div_yield": "fiveYearAvgDivYield",
    "shareholder_yield": "shareholderYield",
    "beta": "beta",
    "fifty_two_week_low": "fiftyTwoWeekLow",
    "fifty_two_week_high": "fiftyTwoWeekHigh",
    "price_in_range": "priceInRange",
    "quarterly_earnings_growth": "quarterlyEarningsGrowth",
    "quarterly_revenue_growth": "quarterlyRevenueGrowth",
    "eps_cagr": "epsCagr",
    "rd_intensity": "rdIntensity",
    "insider_ownership_pct": "insiderOwnershipPct",
    "institutional_ownership_pct": "institutionalOwnershipPct",
    "esg_risk": "esgRisk",
    "macro_rate": "macroRate",
    "macro_gdp": "macroGdp",
    "macro_inflation": "macroInflation",
    "glassdoor_rating": "glassdoorRating",
    "glassdoor_recommend": "glassdoorRecommend",
}


def _normalise_fundamentals(f: dict) -> dict:
    """Returns a new dict with all keys normalised to camelCase, accepting
    both snake_case (Phase 1 JSON / Python style) and camelCase (JS native).
    NaN values are filtered to None so downstream `is not None` checks work
    correctly on rows coming from pandas DataFrames."""
    out = {}
    for k, v in f.items():
        if v is None:
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        if k in _SNAKE_TO_CAMEL:
            out[_SNAKE_TO_CAMEL[k]] = v
        else:
            out[k] = v
    return out


# ============================================================================
# CONVENIENCE WRAPPERS
# ============================================================================

def score_one(stock: dict, fundamentals: Optional[dict] = None) -> dict:
    """Score a single firm; returns dict with dims, layers, composite, quartile."""
    dims, data_driven = compute_dimensions(stock, fundamentals)
    layers = compute_layer_scores(dims)
    composite = compute_composite(layers)
    return {
        "ticker": stock.get("ticker"),
        "sector": stock.get("sector"),
        "country": stock.get("country"),
        "cap": stock.get("cap"),
        "dims": dims,
        "data_driven": data_driven,
        "layer_scores": layers,
        "composite": composite,
        "quartile": get_quartile(composite),
    }


def score_panel(panel: pd.DataFrame,
                ticker_meta: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Batch-score a DataFrame of firm-quarter observations.

    Args:
        panel: DataFrame with columns including 'ticker' and any fundamental fields
        ticker_meta: optional DataFrame with ticker → (sector, country, cap)
                     If not provided, expects sector/country/cap columns in panel

    Returns:
        Original panel + columns for each dimension, layer, composite, quartile, dims_live
    """
    rows = []
    meta_lookup = {}
    if ticker_meta is not None:
        meta_lookup = ticker_meta.set_index("ticker").to_dict("index")

    for _, row in panel.iterrows():
        ticker = row.get("ticker", "")
        if ticker in meta_lookup:
            meta = meta_lookup[ticker]
            stock = {
                "ticker": ticker,
                "sector": meta.get("sector", "INDUS"),
                "country": meta.get("country", "US"),
                "cap": meta.get("cap", "L"),
            }
        else:
            stock = {
                "ticker": ticker,
                "sector": row.get("sector", "INDUS"),
                "country": row.get("country", "US"),
                "cap": row.get("cap", "L"),
            }

        fundamentals = row.to_dict()
        # Inject source flag so compute_dimensions treats this as live data
        fundamentals.setdefault("source", "panel")

        result = score_one(stock, fundamentals)

        out_row = dict(row)
        for d, v in result["dims"].items():
            out_row[d] = v
        for layer_id, v in result["layer_scores"].items():
            out_row[f"layer_{layer_id}"] = v
        out_row["composite"] = result["composite"]
        out_row["quartile"] = result["quartile"]
        out_row["dims_live"] = len(result["data_driven"])
        out_row["data_driven_set"] = "|".join(sorted(result["data_driven"].keys()))
        rows.append(out_row)

    return pd.DataFrame(rows)


# ============================================================================
# COVERAGE REPORT — explicit, no proxies
# ============================================================================

def coverage_report(scored_panel: pd.DataFrame) -> pd.DataFrame:
    """For each dimension, classify scoring source.

    Three tiers:
      - data_driven (per-firm): real fundamentals available for this observation
      - sector_tier: sector-stratified baseline (semi-live, e.g. D8 culture)
      - flat_default: no signal — falls to a global default

    Uses the data_driven_set column (built by score_panel) for per-firm classification.
    Sector-tier classification is inferred from std-dev > 0 within sector_baselines
    (D8 culture_purpose has TECH=75 / ENERGY=50 / etc., so std-dev across sectors > 0).
    """
    if "data_driven_set" not in scored_panel.columns:
        raise ValueError("Run score_panel first to produce data_driven_set column")

    n = len(scored_panel)
    # Compute per-dimension std across the (sector-only) baseline lookup
    sector_baseline_std = {}
    for dim in DIMENSIONS:
        baseline_vals = []
        for s_id, b in SECTOR_BASELINES.items():
            if isinstance(b, dict) and "dims" in b:
                v = b["dims"].get(dim)
                if v is not None:
                    baseline_vals.append(v)
        sector_baseline_std[dim] = (
            float(pd.Series(baseline_vals).std()) if len(baseline_vals) > 1 else 0.0
        )

    rows = []
    for dim in DIMENSIONS:
        live = scored_panel["data_driven_set"].str.contains(dim, regex=False).sum()
        sector_tier = sector_baseline_std.get(dim, 0.0) > 1.0
        # Classify: per-firm data_driven for the 'live' obs, sector-tier for rest if applicable
        if sector_tier:
            source_label = "per-firm + sector-tier"
        elif live > 0:
            source_label = "per-firm + flat baseline"
        else:
            source_label = "flat baseline only"
        rows.append({
            "dimension": dim,
            "n_per_firm": int(live),
            "pct_per_firm": round(100 * live / n, 1) if n else 0.0,
            "source": source_label,
            "n_baseline": int(n - live),
            "mean_score": round(scored_panel[dim].mean(), 1) if dim in scored_panel else None,
            "std_score": round(scored_panel[dim].std(), 1) if dim in scored_panel else None,
        })
    return pd.DataFrame(rows)


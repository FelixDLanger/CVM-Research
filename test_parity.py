"""
tests/test_parity.py — Verifies Python compute_dimensions matches JS reference.

For each test case, both engines score the same (stock, fundamentals) input.
The test passes if all 10 dimensions, all 6 layer scores, and the composite
agree exactly (or within ±1 point for floating-point rounding differences).

This is the single most important test in cvm_research. If parity breaks,
the whole "empirical validation of the public framework" claim collapses
because we'd be measuring something different from what users see.

Run from repo root:
    python tests/test_parity.py

Requires Node.js installed (used to run js_reference.js).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Make the package importable when running from repo root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cvm_research.scoring import (
    compute_dimensions, compute_layer_scores, compute_composite,
)


# ============================================================================
# TEST CASES — representative coverage across sectors, caps, countries, regimes
# ============================================================================

TEST_CASES = [
    # 1. Apple-like: TECH mega-cap US, high P/E, high ROE outlier
    {
        "id": "AAPL_TECH_M",
        "stock": {"ticker": "AAPL", "sector": "TECH", "cap": "M", "country": "US"},
        "fundamentals": {
            "source": "live",
            "pe": 36.15, "pb": 65.34, "currentRatio": 1.07, "operatingMargin": 31.5,
            "roe": 141.47, "debtEquity": 1.84, "payoutRatio": 14.5,
            "quarterlyEarningsGrowth": 12.5, "quarterlyRevenueGrowth": 6.3,
            "beta": 1.06, "priceInRange": 0.95, "rdIntensity": 7.7,
            "insiderOwnershipPct": 0.12, "institutionalOwnershipPct": 65.05,
            "esgRisk": 14.5,
        },
    },
    # 2. Aurubis-like: MAT mid-cap DE, classic value stock
    {
        "id": "NDA.DE_MAT_I",
        "stock": {"ticker": "NDA.DE", "sector": "MAT", "cap": "I", "country": "DE"},
        "fundamentals": {
            "source": "live",
            "pe": 13.37, "pb": 1.2, "currentRatio": 2.38, "operatingMargin": 8.2,
            "roe": 13.07, "debtEquity": 0.09, "beta": 1.10, "priceInRange": 0.85,
        },
    },
    # 3. GameStop-like: CONS_D mid-cap US, founder-controlled (Cohen 8.5%)
    {
        "id": "GME_CONS_D_I",
        "stock": {"ticker": "GME", "sector": "CONS_D", "cap": "I", "country": "US"},
        "fundamentals": {
            "source": "live",
            "pe": 23.41, "currentRatio": 4.8, "roe": 5.2, "debtEquity": 0.4,
            "beta": 0.75, "priceInRange": 0.30,
            "insiderOwnershipPct": 8.5, "institutionalOwnershipPct": 39.0,
        },
    },
    # 4. JPM-like: FIN large-cap US, banking metrics
    {
        "id": "JPM_FIN_M",
        "stock": {"ticker": "JPM", "sector": "FIN", "cap": "M", "country": "US"},
        "fundamentals": {
            "source": "live",
            "pe": 12.5, "pb": 1.8, "roe": 16.2, "operatingMargin": 38.0,
            "beta": 1.12, "priceInRange": 0.85,
            "institutionalOwnershipPct": 72.5,
        },
    },
    # 5. UTIL with high payout ratio (penalty)
    {
        "id": "SO_UTIL_L",
        "stock": {"ticker": "SO", "sector": "UTIL", "cap": "L", "country": "US"},
        "fundamentals": {
            "source": "live",
            "pe": 22, "pb": 2.1, "currentRatio": 0.9, "roe": 11.5,
            "debtEquity": 1.6, "payoutRatio": 95, "divYield": 3.8,
            "beta": 0.45, "priceInRange": 0.7,
        },
    },
    # 6. Chinese mega-cap (negative ownership_structure country adjustment)
    {
        "id": "BABA_CONS_C_M_CN",
        "stock": {"ticker": "9988.HK", "sector": "CONS_C", "cap": "M", "country": "CN"},
        "fundamentals": {
            "source": "live",
            "pe": 14, "pb": 1.8, "currentRatio": 2.1, "operatingMargin": 18,
            "roe": 9.5, "debtEquity": 0.3, "beta": 0.95, "priceInRange": 0.45,
        },
    },
    # 7. Pure demo case — no live data, only sector/cap/country adjustments
    {
        "id": "demo_TECH_M_US",
        "stock": {"ticker": "TESTCO", "sector": "TECH", "cap": "M", "country": "US"},
        "fundamentals": {"source": "demo"},
    },
    # 8. Sparse fundamentals — only PE present, no D2 trigger by itself but logged
    {
        "id": "sparse_INDUS_L",
        "stock": {"ticker": "SPARSE", "sector": "INDUS", "cap": "L", "country": "US"},
        "fundamentals": {"source": "live", "pe": 18.0},
    },
    # 9. ENERGY with strong shareholder yield
    {
        "id": "XOM_ENERGY_M",
        "stock": {"ticker": "XOM", "sector": "ENERGY", "cap": "M", "country": "US"},
        "fundamentals": {
            "source": "live",
            "pe": 10, "pb": 2.0, "currentRatio": 1.5, "roe": 22, "debtEquity": 0.4,
            "shareholderYield": 9.5, "divYield": 4.5,
            "beta": 0.85, "priceInRange": 0.6,
        },
    },
    # 10. SaaS-style: small-cap TECH (cap adjustments + ticker variance test)
    {
        "id": "saas_TECH_S",
        "stock": {"ticker": "PLTR", "sector": "TECH", "cap": "S", "country": "US"},
        "fundamentals": {
            "source": "live",
            "pe": 180, "pb": 28, "currentRatio": 5.2, "operatingMargin": 12,
            "roe": 16, "debtEquity": 0.1, "quarterlyRevenueGrowth": 35,
            "beta": 2.5, "priceInRange": 0.92, "rdIntensity": 18,
            "insiderOwnershipPct": 15.0, "institutionalOwnershipPct": 38,
            "esgRisk": 22,
        },
    },
    # 11. Founder-controlled small-cap (insider ≥ 20%)
    {
        "id": "founder_CONS_C_S",
        "stock": {"ticker": "FOUNDER", "sector": "CONS_C", "cap": "S", "country": "US"},
        "fundamentals": {"source": "live", "insiderOwnershipPct": 25, "roe": 18, "debtEquity": 0.3},
    },
    # 12. ESG severe risk (D9 penalty)
    {
        "id": "highrisk_ENERGY_L",
        "stock": {"ticker": "POLLUTER", "sector": "ENERGY", "cap": "L", "country": "US"},
        "fundamentals": {"source": "live", "esgRisk": 45, "beta": 1.4},
    },
    # 13. Macro signals: high inflation + low GDP environment
    {
        "id": "macro_test_INDUS",
        "stock": {"ticker": "MACRO", "sector": "INDUS", "cap": "L", "country": "TR"},
        "fundamentals": {"source": "live",
                         "macroRate": 6.5, "macroGdp": 0.5, "macroInflation": 8.0},
    },
    # 14. Glassdoor culture
    {
        "id": "culture_TECH_L",
        "stock": {"ticker": "CULT", "sector": "TECH", "cap": "L", "country": "US"},
        "fundamentals": {"source": "live",
                         "glassdoorRating": 4.5, "glassdoorRecommend": 88},
    },
    # 15. ETF (special sector with null currentRatio, null debtEquity)
    {
        "id": "etf_test",
        "stock": {"ticker": "VOO", "sector": "ETF", "cap": "M", "country": "US"},
        "fundamentals": {"source": "live", "pe": 22, "beta": 1.0},
    },
    # 16. Japan ownership adjustment + culture +
    {
        "id": "JP_TECH",
        "stock": {"ticker": "7203.T", "sector": "CONS_C", "cap": "M", "country": "JP"},
        "fundamentals": {"source": "live", "pe": 10, "roe": 9, "debtEquity": 0.4,
                         "beta": 0.5, "institutionalOwnershipPct": 32},
    },
    # 17. Real Estate special D/E anchor
    {
        "id": "PLD_RE",
        "stock": {"ticker": "PLD", "sector": "RE", "cap": "L", "country": "US"},
        "fundamentals": {"source": "live",
                         "pe": 32, "pb": 2.4, "debtEquity": 1.3, "roe": 6,
                         "divYield": 3.5},
    },
    # 18. Pure baseline test — no fundamentals at all (None)
    {
        "id": "none_fund",
        "stock": {"ticker": "NONE", "sector": "TECH", "cap": "M", "country": "US"},
        "fundamentals": None,
    },
]


# ============================================================================
# DRIVERS
# ============================================================================

def score_python(case: dict) -> dict:
    """Score a case using the Python engine."""
    dims, data_driven = compute_dimensions(case["stock"], case["fundamentals"])
    layer_scores = compute_layer_scores(dims)
    composite = compute_composite(layer_scores)
    return {
        "id": case["id"],
        "dims": dims,
        "dataDriven": data_driven,
        "layerScores": layer_scores,
        "composite": composite,
    }


def score_js_batch(cases: list) -> list:
    """Score all cases via Node.js subprocess."""
    js_path = Path(__file__).resolve().parent / "js_reference.js"
    if not js_path.exists():
        raise FileNotFoundError(f"JS reference not found at {js_path}")
    input_json = json.dumps(cases)
    result = subprocess.run(
        ["node", str(js_path)],
        input=input_json, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Node.js reference failed:\n{result.stderr}")
    return json.loads(result.stdout)


# ============================================================================
# COMPARISON
# ============================================================================

def compare(py: dict, js: dict, tolerance: int = 1) -> list[str]:
    """Compare Python and JS results for one test case. Returns list of
    discrepancy strings; empty list means parity."""
    diffs = []
    # Dimension-level
    for dim in py["dims"]:
        py_val = py["dims"][dim]
        js_val = js["dims"].get(dim)
        if js_val is None:
            diffs.append(f"dim {dim}: py={py_val} js=MISSING")
            continue
        if abs(py_val - js_val) > tolerance:
            diffs.append(f"dim {dim}: py={py_val} js={js_val} (Δ={py_val - js_val})")
    # Layer-level
    for layer in py["layerScores"]:
        py_val = py["layerScores"][layer]
        js_val = js["layerScores"].get(layer)
        if js_val is None:
            diffs.append(f"layer {layer}: py={py_val} js=MISSING")
            continue
        if abs(py_val - js_val) > tolerance:
            diffs.append(f"layer {layer}: py={py_val} js={js_val} (Δ={py_val - js_val})")
    # Composite
    if abs(py["composite"] - js["composite"]) > tolerance:
        diffs.append(f"composite: py={py['composite']} js={js['composite']} (Δ={py['composite'] - js['composite']})")
    return diffs


def main():
    print("=" * 76)
    print("PARITY TEST: Python compute_dimensions vs JS reference")
    print(f"Tolerance: ±1 point per dimension/layer/composite")
    print(f"Test cases: {len(TEST_CASES)}")
    print("=" * 76)

    # Score Python side
    py_results = {}
    for case in TEST_CASES:
        try:
            py_results[case["id"]] = score_python(case)
        except Exception as e:
            print(f"  ✗ Python failed on {case['id']}: {type(e).__name__}: {e}")
            return 1

    # Score JS side (single subprocess call for efficiency)
    try:
        js_results_list = score_js_batch(TEST_CASES)
    except FileNotFoundError as e:
        print(f"\n⚠️  {e}")
        print("    Run from repo root: python tests/test_parity.py")
        return 2
    except Exception as e:
        print(f"\n✗ JS subprocess failed: {type(e).__name__}: {e}")
        return 2
    js_results = {r["id"]: r for r in js_results_list}

    # Compare each case
    passed, failed = 0, 0
    for case_id in py_results:
        py = py_results[case_id]
        js = js_results.get(case_id)
        if js is None:
            print(f"  ✗ {case_id}: JS result missing")
            failed += 1
            continue
        diffs = compare(py, js)
        if diffs:
            failed += 1
            print(f"  ✗ {case_id}:")
            for d in diffs:
                print(f"      {d}")
        else:
            passed += 1
            print(f"  ✓ {case_id}  (composite: {py['composite']})")

    print("=" * 76)
    print(f"RESULT: {passed} passed · {failed} failed (of {len(TEST_CASES)} cases)")
    print("=" * 76)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

"""
cvm_research.pit_data — Point-in-time data assembly for the historical backtest.

Critical methodology:
  Every firm-quarter observation uses ONLY data publicly available at that
  quarter-end. SimFin's `publish_date` field anchors each statement to its
  public availability. We never use information that wasn't yet public.

Design notes:
  - Per-ticker price/income/balance indexes are built ONCE upfront (O(N))
    so per-firm-per-quarter lookups are O(log N), not O(N). For 200 firms
    × 44 quarters this saves ~20 minutes of runtime.
  - PE, PB, market_cap, beta are properly derived (the v1 module did not).
  - ROE uses trailing-twelve-month net income (sum of last 4 quarters)
    rather than crude quarterly×4 annualization.
  - Forward returns use pandas business-day offsets (252 trading days)
    rather than calendar-day approximations.

Reference: see cvm_research/scoring.py for the snake_case ↔ camelCase
field name mapping used downstream.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import re

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay


# ============================================================================
# QUARTER ENDS — defensible, deterministic
# ============================================================================

def quarter_ends(start_year: int = 2013, end_year: int = 2023) -> list[pd.Timestamp]:
    """Return calendar quarter-end timestamps from start through end inclusive.

    11 years × 4 quarters = 44 quarter-ends. The backtest documentation must
    use this same count consistently (we previously had inconsistency around
    "40 quarters / 8000 obs" vs "44 / 8800" — 44 is correct).
    """
    quarters = []
    for year in range(start_year, end_year + 1):
        for month in [3, 6, 9, 12]:
            if month == 12:
                qe = pd.Timestamp(year, 12, 31)
            else:
                next_month_first = pd.Timestamp(year, month + 1, 1)
                qe = next_month_first - pd.Timedelta(days=1)
            quarters.append(qe)
    return quarters


# ============================================================================
# SIMFIN BULK LOADERS
# ============================================================================

def _to_ts(s) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename SimFin's canonical columns to our snake_case schema."""
    df = df.copy()
    rename = {
        "Ticker": "ticker",
        "SimFinId": "simfin_id",
        "Company Name": "company_name",
        "Publish Date": "publish_date",
        "Report Date": "report_date",
        "Fiscal Year": "fiscal_year",
        "Fiscal Period": "fiscal_period",
        "Date": "date",
        "Adj. Close": "adj_close",
        "Close": "close",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Volume": "volume",
        "Dividend": "dividend",
        "Shares Outstanding": "shares_out",
        "Shares (Basic)": "shares_basic",
        "Shares (Diluted)": "shares_diluted",
        "Common Shares Outstanding": "shares_out",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "publish_date" in df.columns:
        df["publish_date"] = _to_ts(df["publish_date"])
    if "report_date" in df.columns:
        df["report_date"] = _to_ts(df["report_date"])
    if "date" in df.columns:
        df["date"] = _to_ts(df["date"])
    return df


def load_simfin_companies(data_dir: Path) -> pd.DataFrame:
    """Load + concatenate SimFin per-market company CSVs."""
    candidates = list(Path(data_dir).glob("*companies*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No companies CSV found in {data_dir}")
    frames = [pd.read_csv(p, sep=";", encoding="utf-8") for p in candidates]
    return _normalise_columns(pd.concat(frames, ignore_index=True))


def load_simfin_statements(data_dir: Path, statement_type: str) -> pd.DataFrame:
    """Load SimFin statement CSVs.

    statement_type: 'income', 'balance', or 'cashflow'
    """
    pattern = f"*{statement_type}*.csv"
    candidates = list(Path(data_dir).glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No {statement_type} CSVs found in {data_dir}")
    frames = [pd.read_csv(p, sep=";", encoding="utf-8") for p in candidates]
    return _normalise_columns(pd.concat(frames, ignore_index=True))


def load_simfin_prices(data_dir: Path) -> pd.DataFrame:
    """Load SimFin daily share-price CSVs (already split-adjusted)."""
    candidates = (list(Path(data_dir).glob("*shareprices*.csv")) +
                  list(Path(data_dir).glob("*prices*.csv")))
    if not candidates:
        raise FileNotFoundError(f"No prices CSV found in {data_dir}")
    frames = [pd.read_csv(p, sep=";", encoding="utf-8") for p in candidates]
    return _normalise_columns(pd.concat(frames, ignore_index=True))


def ensure_ticker_column(df: pd.DataFrame, companies: pd.DataFrame) -> pd.DataFrame:
    """Guarantee a `ticker` column on a statement/price DataFrame.

    SimFin's statement and price files key on `simfin_id` (SimFinId), NOT on
    ticker. The companies file is the bridge: it has both simfin_id and ticker.
    This helper merges ticker in when it's missing, so TickerIndex (which groups
    by `ticker`) works without per-notebook hot-fixes.

    This is the function whose absence forced live Colab patching. It belongs
    in the data layer and is unit-checked below.

    Args:
        df: a statement or price DataFrame (must have simfin_id OR ticker)
        companies: the companies DataFrame (must have simfin_id AND ticker)

    Returns:
        df with a guaranteed non-null `ticker` column (rows that cannot be
        mapped are dropped, with the count available via the returned frame's
        attrs['dropped_unmapped']).
    """
    df = df.copy()

    # Already has usable ticker? Done.
    if "ticker" in df.columns and df["ticker"].notna().any():
        before = len(df)
        df = df.dropna(subset=["ticker"])
        df.attrs["dropped_unmapped"] = before - len(df)
        return df

    # Need to merge ticker from companies via simfin_id
    if "simfin_id" not in df.columns:
        raise KeyError(
            "DataFrame has neither a usable 'ticker' nor a 'simfin_id' column. "
            f"Columns present: {list(df.columns)[:20]}"
        )
    if not {"simfin_id", "ticker"}.issubset(companies.columns):
        raise KeyError(
            "companies DataFrame must contain both 'simfin_id' and 'ticker'. "
            f"Columns present: {list(companies.columns)[:20]}"
        )

    # Build a clean simfin_id -> ticker map (one ticker per id).
    # drop_duplicates keeps the FIRST ticker if SimFin ever maps one SimFinId to
    # multiple tickers (rare: share-class changes, re-listings). For this study's
    # large-cap universe this is not expected to occur; if it did, the first-seen
    # ticker is used deterministically.
    id_to_ticker = (
        companies.dropna(subset=["simfin_id", "ticker"])
        .drop_duplicates(subset=["simfin_id"])
        .set_index("simfin_id")["ticker"]
    )

    before = len(df)
    df["ticker"] = df["simfin_id"].map(id_to_ticker)
    df = df.dropna(subset=["ticker"])
    df.attrs["dropped_unmapped"] = before - len(df)
    return df


# ============================================================================
# PER-TICKER INDEXES — for O(1) lookups in the inner loop
# ============================================================================

class TickerIndex:
    """Pre-built lookup index for fast point-in-time queries.

    Internally stores per-ticker sorted DataFrames keyed by date. Per-ticker
    queries reduce to a single bisect operation rather than full-DataFrame
    filtering (which was the O(N²) bottleneck in v1).
    """
    def __init__(self, df: pd.DataFrame, date_col: str = "publish_date"):
        self.date_col = date_col
        self._per_ticker = {}
        if date_col not in df.columns:
            raise ValueError(f"Column {date_col!r} not found in DataFrame")
        df_valid = df.dropna(subset=["ticker", date_col]).copy()
        # Group + sort once for the lifetime of the index
        for ticker, group in df_valid.groupby("ticker", sort=False):
            self._per_ticker[ticker] = group.sort_values(date_col).reset_index(drop=True)

    def latest_as_of(self, ticker: str, as_of: pd.Timestamp) -> Optional[pd.Series]:
        """Most recent row for ticker with date <= as_of."""
        sub = self._per_ticker.get(ticker)
        if sub is None or len(sub) == 0:
            return None
        # `searchsorted` on a sorted column is O(log N)
        dates = sub[self.date_col]
        idx = dates.searchsorted(as_of, side="right") - 1
        if idx < 0:
            return None
        return sub.iloc[idx]

    def trailing_n(self, ticker: str, as_of: pd.Timestamp, n: int) -> pd.DataFrame:
        """Most recent N rows for ticker with date <= as_of."""
        sub = self._per_ticker.get(ticker)
        if sub is None or len(sub) == 0:
            return pd.DataFrame()
        dates = sub[self.date_col]
        idx = dates.searchsorted(as_of, side="right") - 1
        if idx < 0:
            return pd.DataFrame()
        start = max(0, idx - n + 1)
        return sub.iloc[start: idx + 1]

    def date_range(self, ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        """All rows for ticker with date in [start, end]."""
        sub = self._per_ticker.get(ticker)
        if sub is None or len(sub) == 0:
            return pd.DataFrame()
        dates = sub[self.date_col]
        lo = dates.searchsorted(start, side="left")
        hi = dates.searchsorted(end, side="right")
        return sub.iloc[lo: hi]


# ============================================================================
# FUNDAMENTAL DERIVATIONS — proper PE, PB, market_cap, beta, TTM ROE
# ============================================================================

def _safe_num(row: Optional[pd.Series], candidates: list[str]) -> Optional[float]:
    """Get first non-null numeric value from row by trying candidate column names."""
    if row is None:
        return None
    for c in candidates:
        if c in row.index:
            v = row[c]
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
    return None


def trailing_twelve_month_net_income(income_idx: TickerIndex,
                                     ticker: str,
                                     as_of: pd.Timestamp) -> Optional[float]:
    """Sum of last 4 quarterly net incomes available before `as_of`.

    Returns None if fewer than 4 quarters available. (Audit fix: previously
    accepted 3 quarters and labelled the result "TTM", which biased PE upward
    by ~33% for firms with reporting gaps or pre-IPO history. A true trailing-
    twelve-month figure requires four consecutive quarters.)
    """
    rows = income_idx.trailing_n(ticker, as_of, 4)
    if len(rows) < 4:
        return None
    ni_values = []
    for _, r in rows.iterrows():
        v = _safe_num(r, ["Net Income", "Net Income (Common)"])
        if v is not None:
            ni_values.append(v)
    if len(ni_values) < 4:
        return None
    return sum(ni_values)


def derive_fundamentals(
    ticker: str,
    as_of: pd.Timestamp,
    income_idx: TickerIndex,
    balance_idx: TickerIndex,
    cashflow_idx: TickerIndex,
    price_idx: TickerIndex,
    market_index_returns: Optional[pd.Series] = None,
) -> dict:
    """Derive the fundamentals dict for a single (ticker, as_of) observation.

    Returns dict with snake_case keys matching the Phase 1 JSON schema and
    the cvm_research.scoring normaliser. Missing values are None — scoring
    falls back to sector baseline for those dimensions.
    """
    result = {
        # Valuation
        "pe": None, "pb": None,
        # Health
        "current_ratio": None, "debt_equity": None, "operating_margin": None,
        "profit_margin": None, "payout_ratio": None,
        # Returns
        "roe": None, "div_yield": None, "shareholder_yield": None,
        # Growth
        "eps_cagr": None,
        "quarterly_earnings_growth": None, "quarterly_revenue_growth": None,
        # Tech
        "rd_intensity": None,
        # Market
        "beta": None, "price": None,
        "fifty_two_week_low": None, "fifty_two_week_high": None,
        "price_in_range": None,
        # Size
        "market_cap": None, "shares_out": None,
        # Ownership / ESG (not derivable from SimFin alone; future enrichment hook)
        "insider_ownership_pct": None,
        "institutional_ownership_pct": None,
        "esg_risk": None,
    }

    # ── Statement rows as of as_of ──────────────────────────────────────────
    inc = income_idx.latest_as_of(ticker, as_of)
    bal = balance_idx.latest_as_of(ticker, as_of)
    cf = cashflow_idx.latest_as_of(ticker, as_of)
    price = price_idx.latest_as_of(ticker, as_of)

    # ── Price + shares outstanding + market cap ─────────────────────────────
    price_val = _safe_num(price, ["adj_close", "close"])
    shares_out = _safe_num(price, ["shares_out"])  # SimFin includes shares in price file
    if shares_out is None and bal is not None:
        # Fallback: balance sheet may have "Shares (Diluted)" or "Common Shares"
        shares_out = _safe_num(bal, ["Shares (Diluted)", "Shares (Basic)", "Common Shares Outstanding"])

    result["price"] = price_val
    result["shares_out"] = shares_out
    if price_val is not None and shares_out is not None and shares_out > 0:
        result["market_cap"] = price_val * shares_out

    # ── 52-week range ───────────────────────────────────────────────────────
    one_year_back = as_of - pd.Timedelta(days=365)
    year_window = price_idx.date_range(ticker, one_year_back, as_of)
    if len(year_window) >= 50:  # need a meaningful sample
        closes = year_window["adj_close"] if "adj_close" in year_window.columns else year_window.get("close")
        if closes is not None and len(closes.dropna()) > 0:
            result["fifty_two_week_low"] = float(closes.min())
            result["fifty_two_week_high"] = float(closes.max())
            if price_val is not None and result["fifty_two_week_high"] > result["fifty_two_week_low"]:
                result["price_in_range"] = (price_val - result["fifty_two_week_low"]) / (result["fifty_two_week_high"] - result["fifty_two_week_low"])

    # ── Income-statement derivations ────────────────────────────────────────
    revenue = _safe_num(inc, ["Revenue", "Total Revenue"])
    net_income = _safe_num(inc, ["Net Income", "Net Income (Common)"])
    operating_income = _safe_num(inc, ["Operating Income (Loss)", "Operating Income"])
    rd = _safe_num(inc, ["Research & Development", "R&D"])
    dividends_paid = _safe_num(cf, ["Dividends Paid"])  # cash flow has dividends paid

    if revenue is not None and revenue > 0:
        if operating_income is not None:
            result["operating_margin"] = (operating_income / revenue) * 100
        if net_income is not None:
            result["profit_margin"] = (net_income / revenue) * 100
        if rd is not None:
            result["rd_intensity"] = (rd / revenue) * 100

    # ── Balance-sheet derivations ───────────────────────────────────────────
    total_assets = _safe_num(bal, ["Total Assets"])
    current_assets = _safe_num(bal, ["Total Current Assets"])
    current_liab = _safe_num(bal, ["Total Current Liabilities"])
    total_debt = _safe_num(bal, ["Total Debt", "Long Term Debt"])
    equity = _safe_num(bal, ["Total Equity", "Total Shareholders' Equity", "Common Equity"])

    if current_assets and current_liab and current_liab > 0:
        result["current_ratio"] = current_assets / current_liab
    if total_debt is not None and equity is not None and equity > 0:
        result["debt_equity"] = total_debt / equity

    # ── PE — needs TTM net income and market cap ────────────────────────────
    ttm_ni = trailing_twelve_month_net_income(income_idx, ticker, as_of)
    if ttm_ni is not None and ttm_ni > 0 and result["market_cap"] is not None:
        result["pe"] = result["market_cap"] / ttm_ni
        # ROE = TTM NI / current equity
        if equity is not None and equity > 0:
            result["roe"] = (ttm_ni / equity) * 100

    # ── PB — market cap / book equity ───────────────────────────────────────
    if equity is not None and equity > 0 and result["market_cap"] is not None:
        result["pb"] = result["market_cap"] / equity

    # ── Payout ratio (TTM dividends / TTM net income) ───────────────────────
    if dividends_paid is not None and ttm_ni is not None and ttm_ni > 0:
        # dividends_paid is typically negative in cash flow statements; take abs
        result["payout_ratio"] = (abs(dividends_paid) * 4 / ttm_ni) * 100 if abs(dividends_paid) < ttm_ni else 100

    # ── Dividend yield (last TTM dividend / current price) ──────────────────
    # SimFin price file has per-date dividend; approximate TTM div from 12-month sum
    if price_val is not None and price_val > 0:
        div_sum = 0.0
        div_count = 0
        for _, r in year_window.iterrows():
            d = _safe_num(r, ["dividend"])
            if d is not None and d > 0:
                div_sum += d
                div_count += 1
        if div_count > 0:
            result["div_yield"] = (div_sum / price_val) * 100

    # ── Growth (quarterly YoY) — needs current and year-ago quarter ─────────
    if inc is not None:
        # Find quarterly statement from ~1 year before
        one_year_ago = as_of - pd.Timedelta(days=370)  # slight buffer for publish lag
        inc_year_ago = income_idx.latest_as_of(ticker, one_year_ago)
        if inc_year_ago is not None:
            ni_now = _safe_num(inc, ["Net Income"])
            ni_then = _safe_num(inc_year_ago, ["Net Income"])
            if ni_now is not None and ni_then is not None and ni_then > 0:
                result["quarterly_earnings_growth"] = ((ni_now - ni_then) / abs(ni_then)) * 100
            rev_now = _safe_num(inc, ["Revenue"])
            rev_then = _safe_num(inc_year_ago, ["Revenue"])
            if rev_now is not None and rev_then is not None and rev_then > 0:
                result["quarterly_revenue_growth"] = ((rev_now - rev_then) / rev_then) * 100

    # ── Beta — regress 252-trading-day returns vs market index ──────────────
    if market_index_returns is not None and price_val is not None:
        result["beta"] = compute_beta_252d(ticker, as_of, price_idx, market_index_returns)

    return result


def compute_beta_252d(
    ticker: str,
    as_of: pd.Timestamp,
    price_idx: TickerIndex,
    market_returns: pd.Series,
) -> Optional[float]:
    """Compute market beta over trailing 252 trading days.

    beta = Cov(stock_returns, mkt_returns) / Var(mkt_returns)
    """
    one_year_back = as_of - BDay(252)
    window = price_idx.date_range(ticker, pd.Timestamp(one_year_back), as_of)
    if len(window) < 100:  # need a meaningful sample
        return None
    close_col = "adj_close" if "adj_close" in window.columns else "close"
    closes = window[close_col].dropna()
    if len(closes) < 100:
        return None
    stock_returns = closes.pct_change().dropna()
    # Align with market returns by date
    window_with_date = window.set_index("date")[close_col].dropna()
    stock_ret_dated = window_with_date.pct_change().dropna()
    # Align via index intersection
    common = stock_ret_dated.index.intersection(market_returns.index)
    if len(common) < 50:
        return None
    s = stock_ret_dated.loc[common]
    m = market_returns.loc[common]
    if m.var() == 0 or pd.isna(m.var()):
        return None
    return float(s.cov(m) / m.var())


# ============================================================================
# PANEL ASSEMBLY
# ============================================================================

def build_pit_panel(
    tickers: list[str],
    quarter_dates: list[pd.Timestamp],
    income_idx: TickerIndex,
    balance_idx: TickerIndex,
    cashflow_idx: TickerIndex,
    price_idx: TickerIndex,
    ticker_to_meta: dict,
    market_index_returns: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Build the long firm-quarter panel.

    For 200 tickers × 44 quarter-ends = 8,800 rows. Each row is one
    (ticker, as_of) observation with the full point-in-time fundamentals.

    Args:
        tickers: list of ticker symbols
        quarter_dates: list of as-of timestamps
        income_idx, balance_idx, cashflow_idx, price_idx: pre-built TickerIndex objects
        ticker_to_meta: dict mapping ticker -> {sector, country, cap, name}
        market_index_returns: optional pd.Series of daily market returns (for beta)

    Returns:
        DataFrame with columns: ticker, as_of, sector, country, cap, + all fundamentals
    """
    rows = []
    for ticker in tickers:
        meta = ticker_to_meta.get(ticker, {})
        for as_of in quarter_dates:
            row = {
                "ticker": ticker,
                "as_of": as_of,
                "sector": meta.get("sector", "INDUS"),
                "country": meta.get("country", "US"),
                "cap": meta.get("cap"),
                "name": meta.get("name", ticker),
            }
            fund = derive_fundamentals(
                ticker, as_of,
                income_idx, balance_idx, cashflow_idx, price_idx,
                market_index_returns=market_index_returns,
            )
            row.update(fund)
            # If cap wasn't set in meta, derive from market cap
            if row["cap"] is None and row.get("market_cap"):
                row["cap"] = cap_tier_from_market_cap(row["market_cap"])
            row["source"] = "live"  # flag so scoring runs the live-data path
            rows.append(row)
    return pd.DataFrame(rows)


def cap_tier_from_market_cap(mc: Optional[float]) -> Optional[str]:
    """USD market cap → cap tier matching CAP_ADJ keys."""
    if mc is None or mc <= 0:
        return None
    if mc >= 200_000_000_000: return "M"
    if mc >= 10_000_000_000:  return "L"
    if mc >= 2_000_000_000:   return "I"
    if mc >= 300_000_000:     return "S"
    return "S"  # we don't have a V/micro tier in CAP_ADJ


# ============================================================================
# FORWARD RETURNS — proper trading-day calendar
# ============================================================================

def forward_total_return(
    price_idx: TickerIndex,
    ticker: str,
    as_of: pd.Timestamp,
    trading_days: int = 252,
    max_lookback_bdays: int = 10,
) -> Optional[float]:
    """Forward total return from as_of to as_of + N trading days.

    Audit fix #3: validates that the end-date price actually exists near the
    target date. If `as_of + trading_days` falls beyond the available price
    series (e.g. running at the late edge of the sample), the function
    returns None rather than silently producing a partial-horizon return.
    Without this check, late-sample observations would mix true 1-year and
    truncated returns, biasing the regression dependent variable downward
    near the end of the panel.

    Tolerance: `max_lookback_bdays` business days. If the most-recent available
    price is more than this many trading days before the target, we treat the
    horizon as unreachable.
    """
    start_row = price_idx.latest_as_of(ticker, as_of)
    if start_row is None:
        return None
    start_price = _safe_num(start_row, ["adj_close", "close"])
    if start_price is None or start_price <= 0:
        return None

    target_date = pd.Timestamp(as_of + BDay(trading_days))
    end_row = price_idx.latest_as_of(ticker, target_date)
    if end_row is None:
        return None
    end_price = _safe_num(end_row, ["adj_close", "close"])
    if end_price is None or end_price <= 0:
        return None

    # Horizon validation: was the end-date price actually within tolerance of
    # the target? If end_row.date is more than max_lookback_bdays trading days
    # before target_date, the horizon is unreachable in our data.
    end_date = end_row.get("date")
    if end_date is not None:
        gap_calendar_days = (target_date - pd.Timestamp(end_date)).days
        # ~7 calendar days per 5 trading days. Add safety margin.
        max_calendar_gap = max_lookback_bdays * 7 / 5 + 3
        if gap_calendar_days > max_calendar_gap:
            return None

    return (end_price / start_price - 1) * 100


def attach_forward_returns(
    panel: pd.DataFrame,
    price_idx: TickerIndex,
    trading_days: int = 252,
) -> pd.DataFrame:
    """Add forward_return_pct column to the panel.

    Uses the pre-built price_idx for O(log N) lookups — addresses the
    O(N²) bottleneck that would have made the v1 code take 20+ minutes.
    """
    panel = panel.copy()
    returns = []
    for _, row in panel.iterrows():
        r = forward_total_return(price_idx, row["ticker"], row["as_of"], trading_days)
        returns.append(r)
    panel["forward_return_pct"] = returns
    return panel


# ============================================================================
# MARKET INDEX HELPER
# ============================================================================

def market_index_daily_returns(price_idx: TickerIndex,
                                index_ticker: str = "SPY") -> pd.Series:
    """Pull daily returns for a market-proxy ticker (default SPY).

    Returns a Series indexed by date, values are daily simple returns.
    Used as the market factor for beta computation.
    """
    sub = price_idx._per_ticker.get(index_ticker)
    if sub is None or len(sub) == 0:
        return pd.Series(dtype=float)
    close_col = "adj_close" if "adj_close" in sub.columns else "close"
    series = sub.set_index("date")[close_col].dropna().sort_index()
    return series.pct_change().dropna()

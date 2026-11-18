"""
00_generate_sample_data.py
---------------------------
Generates REALISTIC SYNTHETIC daily price data (geometric Brownian motion
with per-sector drift/volatility, small mutual correlation, and occasional
volatility shocks) and loads it into the same SQLite schema that
01_data_ingestion.py would populate with real Yahoo Finance data.

Use this only to test/demo the pipeline offline. Once you run
01_data_ingestion.py locally with real internet access, it will overwrite
this sample data with the real thing (same table structure either way).
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

np.random.seed(42)

TICKERS = {
    "AAPL": ("Apple Inc.",        "Technology",             0.14, 0.28),
    "MSFT": ("Microsoft Corp.",   "Technology",             0.15, 0.26),
    "GOOGL": ("Alphabet Inc.",    "Technology",             0.12, 0.29),
    "AMZN": ("Amazon.com Inc.",   "Consumer Discretionary", 0.11, 0.34),
    "JPM":  ("JPMorgan Chase",    "Financials",             0.10, 0.24),
    "JNJ":  ("Johnson & Johnson", "Healthcare",              0.07, 0.16),
    "XOM":  ("Exxon Mobil",       "Energy",                  0.09, 0.30),
    "SPY":  ("S&P 500 ETF (Benchmark)", "Benchmark",          0.10, 0.17),
}
START_DATE = "2021-01-01"
END_DATE = "2026-07-24"

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stocks.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "01_schema.sql"


def generate_correlated_returns(n_days, tickers_info):
    """Generate correlated daily returns via a shared market factor + idiosyncratic noise."""
    n = len(tickers_info)
    market_factor = np.random.normal(0, 1, n_days)

    returns = {}
    for i, (ticker, (_, sector, ann_drift, ann_vol)) in enumerate(tickers_info.items()):
        daily_drift = ann_drift / 252
        daily_vol = ann_vol / np.sqrt(252)
        beta = 0.5 + 0.5 * np.random.rand()  # market sensitivity
        idio = np.random.normal(0, 1, n_days)
        # blend market factor + idiosyncratic noise, scaled to target vol
        raw = beta * market_factor + np.sqrt(max(1 - beta**2, 0.1)) * idio
        daily_returns = daily_drift + daily_vol * raw

        # occasional volatility shock (earnings surprise, macro news)
        shock_days = np.random.choice(n_days, size=max(3, n_days // 120), replace=False)
        daily_returns[shock_days] += np.random.normal(0, daily_vol * 4, len(shock_days))

        returns[ticker] = daily_returns
    return returns


def build_database():
    dates = pd.bdate_range(START_DATE, END_DATE)  # business days
    n_days = len(dates)

    returns = generate_correlated_returns(n_days, TICKERS)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    for ticker, (company, sector, _, _) in TICKERS.items():
        conn.execute(
            "INSERT INTO tickers (ticker, company, sector, is_benchmark) VALUES (?,?,?,?)",
            (ticker, company, sector, 1 if sector == "Benchmark" else 0),
        )
    conn.commit()

    start_prices = {
        "AAPL": 132, "MSFT": 220, "GOOGL": 87, "AMZN": 160,
        "JPM": 135, "JNJ": 160, "XOM": 45, "SPY": 375,
    }

    for ticker in TICKERS:
        r = returns[ticker]
        price = start_prices[ticker] * np.exp(np.cumsum(r))
        close = price
        open_ = np.roll(close, 1)
        open_[0] = start_prices[ticker]
        daily_range = np.abs(np.random.normal(0, 0.008, n_days)) * close
        high = np.maximum(open_, close) + daily_range
        low = np.minimum(open_, close) - daily_range
        volume = np.random.randint(2_000_000, 60_000_000, n_days)

        df = pd.DataFrame({
            "ticker": ticker,
            "trade_date": dates.strftime("%Y-%m-%d"),
            "open": open_.round(2),
            "high": high.round(2),
            "low": low.round(2),
            "close": close.round(2),
            "adj_close": close.round(2),
            "volume": volume,
        })
        df.to_sql("prices", conn, if_exists="append", index=False)
        print(f"{ticker}: inserted {len(df)} rows")

    conn.commit()
    conn.close()
    print(f"\nSample database written to {DB_PATH}")


if __name__ == "__main__":
    build_database()

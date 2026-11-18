"""
01_data_ingestion.py
---------------------
Pulls real historical daily price data from Yahoo Finance via yfinance
and loads it into the SQLite database defined in sql/01_schema.sql.

RUN THIS ON YOUR OWN MACHINE (not in a sandboxed/offline environment) --
it needs open internet access to query1/query2.finance.yahoo.com.

Usage:
    pip install yfinance pandas
    python 01_data_ingestion.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

# ------------------------------------------------------------------
# CONFIG -- edit this list to build your own portfolio
# ------------------------------------------------------------------
TICKERS = {
    "AAPL": ("Apple Inc.",        "Technology"),
    "MSFT": ("Microsoft Corp.",   "Technology"),
    "GOOGL": ("Alphabet Inc.",    "Technology"),
    "AMZN": ("Amazon.com Inc.",   "Consumer Discretionary"),
    "JPM":  ("JPMorgan Chase",    "Financials"),
    "JNJ":  ("Johnson & Johnson", "Healthcare"),
    "XOM":  ("Exxon Mobil",       "Energy"),
    "SPY":  ("S&P 500 ETF (Benchmark)", "Benchmark"),
}
START_DATE = "2021-01-01"
END_DATE = None  # None = through today

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stocks.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "01_schema.sql"


def build_database():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    # Populate tickers table
    for ticker, (company, sector) in TICKERS.items():
        conn.execute(
            "INSERT INTO tickers (ticker, company, sector, is_benchmark) VALUES (?,?,?,?)",
            (ticker, company, sector, 1 if sector == "Benchmark" else 0),
        )
    conn.commit()

    # Download and insert price history
    for ticker in TICKERS:
        print(f"Downloading {ticker} ...")
        df = yf.download(ticker, start=START_DATE, end=END_DATE, auto_adjust=False, progress=False)
        if df.empty:
            print(f"  WARNING: no data returned for {ticker}")
            continue

        df = df.reset_index()
        # yfinance sometimes returns MultiIndex columns for single tickers; flatten if needed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df["ticker"] = ticker
        df = df.rename(columns={
            "Date": "trade_date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Adj Close": "adj_close",
            "Volume": "volume",
        })
        df["trade_date"] = df["trade_date"].dt.strftime("%Y-%m-%d")

        df[["ticker", "trade_date", "open", "high", "low", "close", "adj_close", "volume"]].to_sql(
            "prices", conn, if_exists="append", index=False
        )
        print(f"  inserted {len(df)} rows")

    conn.commit()
    conn.close()
    print(f"\nDone. Database written to {DB_PATH}")


if __name__ == "__main__":
    build_database()

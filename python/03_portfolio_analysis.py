"""
03_portfolio_analysis.py
--------------------------
Pulls data OUT of the SQL database (using real SQL queries with window
functions for the return calculations) and performs portfolio / risk
analysis in pandas + numpy:

  - Daily & cumulative TOTAL returns per ticker (from adjusted close, so
    dividends and splits are included)
  - Annualized return, annualized volatility, Sharpe ratio, max drawdown,
    beta vs. the S&P 500 benchmark
  - Correlation matrix across holdings
  - Monte Carlo simulated efficient frontier (random portfolios) +
    the max-Sharpe and min-volatility portfolios

All outputs are written as tidy CSVs to /exports, ready to drop
straight into Tableau (Data > Text File).
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stocks.db"
EXPORT_DIR = ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

RISK_FREE_RATE = 0.045  # annualized; ~short-term T-bill rate assumption
TRADING_DAYS = 252


def load_prices():
    conn = sqlite3.connect(DB_PATH)
    # Real SQL doing the heavy lifting: daily return via window function
    query = """
        SELECT
            p.ticker,
            t.company,
            t.sector,
            t.is_benchmark,
            p.trade_date,
            p.close,
            p.adj_close,
            -- total return: adjusted close includes dividends and splits
            p.adj_close / LAG(p.adj_close) OVER (PARTITION BY p.ticker ORDER BY p.trade_date) - 1 AS daily_return
        FROM prices p
        JOIN tickers t ON t.ticker = p.ticker
        ORDER BY p.ticker, p.trade_date
    """
    df = pd.read_sql(query, conn, parse_dates=["trade_date"])
    conn.close()
    return df


def add_derived_columns(df):
    df = df.sort_values(["ticker", "trade_date"]).copy()
    df["cumulative_return"] = (
        df.groupby("ticker")["daily_return"]
        .apply(lambda s: (1 + s.fillna(0)).cumprod() - 1)
        .reset_index(level=0, drop=True)
    )
    df["rolling_vol_30d"] = (
        df.groupby("ticker")["daily_return"]
        .transform(lambda s: s.rolling(30).std() * np.sqrt(TRADING_DAYS))
    )
    df["sma_20"] = df.groupby("ticker")["close"].transform(lambda s: s.rolling(20).mean())
    df["sma_50"] = df.groupby("ticker")["close"].transform(lambda s: s.rolling(50).mean())

    # running max & drawdown on the total-return series, per ticker
    df["running_max"] = df.groupby("ticker")["adj_close"].cummax()
    df["drawdown"] = df["adj_close"] / df["running_max"] - 1
    return df


def summary_stats(df):
    # beta_i = Cov(r_i, r_SPY) / Var(r_SPY)
    wide = df.pivot(index="trade_date", columns="ticker", values="daily_return").dropna()
    bench = df.loc[df["is_benchmark"] == 1, "ticker"].iloc[0]
    rows = []
    for ticker, g in df.groupby("ticker"):
        r = g["daily_return"].dropna()
        ann_return = r.mean() * TRADING_DAYS
        ann_vol = r.std() * np.sqrt(TRADING_DAYS)
        sharpe = (ann_return - RISK_FREE_RATE) / ann_vol if ann_vol > 0 else np.nan
        max_dd = g["drawdown"].min()
        rows.append({
            "ticker": ticker,
            "company": g["company"].iloc[0],
            "sector": g["sector"].iloc[0],
            "is_benchmark": g["is_benchmark"].iloc[0],
            "annual_return": ann_return,
            "annual_volatility": ann_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "beta_vs_spy": wide[ticker].cov(wide[bench]) / wide[bench].var(),
        })
    return pd.DataFrame(rows).sort_values("sharpe_ratio", ascending=False)


def correlation_matrix(df):
    wide = df.pivot(index="trade_date", columns="ticker", values="daily_return").dropna()
    corr = wide.corr()
    # long format for Tableau heatmap
    long = corr.reset_index().melt(id_vars="ticker", var_name="ticker_2", value_name="correlation")
    long = long.rename(columns={"ticker": "ticker_1"})
    return corr, long, wide


def efficient_frontier(returns_wide, exclude_benchmark, n_portfolios=8000):
    """Monte Carlo simulation of random portfolio weights -> risk/return/Sharpe."""
    tickers = [t for t in returns_wide.columns if t not in exclude_benchmark]
    mean_returns = returns_wide[tickers].mean() * TRADING_DAYS
    cov_matrix = returns_wide[tickers].cov() * TRADING_DAYS

    results = []
    n = len(tickers)
    rng = np.random.default_rng(42)
    for _ in range(n_portfolios):
        w = rng.random(n)
        w /= w.sum()
        port_return = np.dot(w, mean_returns)
        port_vol = np.sqrt(w @ cov_matrix.values @ w)
        sharpe = (port_return - RISK_FREE_RATE) / port_vol if port_vol > 0 else np.nan
        row = {"portfolio_return": port_return, "portfolio_volatility": port_vol, "sharpe_ratio": sharpe}
        row.update({f"weight_{t}": wt for t, wt in zip(tickers, w)})
        results.append(row)

    ef = pd.DataFrame(results)
    max_sharpe = ef.loc[ef["sharpe_ratio"].idxmax()].copy()
    min_vol = ef.loc[ef["portfolio_volatility"].idxmin()].copy()
    max_sharpe["portfolio_type"] = "Max Sharpe"
    min_vol["portfolio_type"] = "Min Volatility"
    highlights = pd.DataFrame([max_sharpe, min_vol])
    return ef, highlights, tickers


def equal_weight_portfolio(returns_wide, exclude_benchmark):
    tickers = [t for t in returns_wide.columns if t not in exclude_benchmark]
    port_returns = returns_wide[tickers].mean(axis=1)
    cum = (1 + port_returns).cumprod() - 1
    out = pd.DataFrame({
        "trade_date": returns_wide.index,
        "daily_return": port_returns.values,
        "cumulative_return": cum.values,
    })
    out["ticker"] = "PORTFOLIO_EQUAL_WEIGHT"
    return out


def main():
    print("Loading prices from SQL database...")
    df = load_prices()
    df = add_derived_columns(df)

    print("Computing summary stats (return, vol, Sharpe, drawdown)...")
    summary = summary_stats(df)

    print("Computing correlation matrix...")
    corr_wide, corr_long, returns_wide = correlation_matrix(df)

    benchmark_tickers = df.loc[df["is_benchmark"] == 1, "ticker"].unique().tolist()

    print("Running Monte Carlo efficient frontier simulation...")
    ef, ef_highlights, portfolio_tickers = efficient_frontier(returns_wide, benchmark_tickers)

    print("Building equal-weight benchmark portfolio series...")
    eq_weight = equal_weight_portfolio(returns_wide, benchmark_tickers)

    # ---------- Exports for Tableau ----------
    price_cols = [
        "ticker", "company", "sector", "trade_date", "close", "adj_close", "daily_return",
        "cumulative_return", "rolling_vol_30d", "sma_20", "sma_50", "drawdown",
    ]
    df[price_cols].to_csv(EXPORT_DIR / "prices_long.csv", index=False)
    summary.to_csv(EXPORT_DIR / "summary_stats.csv", index=False)
    corr_long.to_csv(EXPORT_DIR / "correlation_matrix_long.csv", index=False)
    corr_wide.to_csv(EXPORT_DIR / "correlation_matrix_wide.csv")
    ef.to_csv(EXPORT_DIR / "efficient_frontier.csv", index=False)
    ef_highlights.to_csv(EXPORT_DIR / "efficient_frontier_highlights.csv", index=False)
    eq_weight.to_csv(EXPORT_DIR / "portfolio_equal_weight.csv", index=False)

    print("\n=== Summary Stats (sorted by Sharpe Ratio) ===")
    print(summary.round(3).to_string(index=False))

    print("\n=== Efficient Frontier Highlights ===")
    print(ef_highlights[["portfolio_type", "portfolio_return", "portfolio_volatility", "sharpe_ratio"]].round(3))

    print(f"\nAll exports written to: {EXPORT_DIR}")


if __name__ == "__main__":
    main()

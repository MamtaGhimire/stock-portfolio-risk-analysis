"""
04_optimize_frontier.py
------------------------
Exact (long-only) Markowitz efficient frontier using a convex optimizer,
to check the Monte Carlo approximation in 03_portfolio_analysis.py.

For weights w (sum to 1, each 0 <= w_i <= 1):
    portfolio return      R_p = w . mu
    portfolio volatility  s_p = sqrt(w' Sigma w)
    Sharpe ratio          S   = (R_p - r_f) / s_p

  - Min volatility:  minimize  w' Sigma w
  - Max Sharpe:      minimize  -(w . mu - r_f) / sqrt(w' Sigma w)
  - Frontier:        for each target return R*, minimize w' Sigma w  s.t. w . mu = R*

Run after 03_portfolio_analysis.py:
    python 04_optimize_frontier.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stocks.db"
EXPORT_DIR = ROOT / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

RISK_FREE_RATE = 0.045
TRADING_DAYS = 252


def load_returns():
    conn = sqlite3.connect(DB_PATH)
    q = """
        SELECT p.ticker, p.trade_date, t.is_benchmark,
               p.adj_close / LAG(p.adj_close) OVER (PARTITION BY p.ticker ORDER BY p.trade_date) - 1 AS r
        FROM prices p JOIN tickers t ON t.ticker = p.ticker
    """
    df = pd.read_sql(q, conn)
    conn.close()
    holdings = df.loc[df.is_benchmark == 0, "ticker"].unique()
    wide = df.pivot(index="trade_date", columns="ticker", values="r").dropna()
    return wide[sorted(holdings)]


def solve(objective, n, extra=()):
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}, *extra]
    res = minimize(objective, np.full(n, 1 / n), method="SLSQP",
                   bounds=[(0, 1)] * n, constraints=cons, options={"ftol": 1e-12, "maxiter": 1000})
    if not res.success:
        raise RuntimeError(res.message)
    return res.x


def main():
    wide = load_returns()
    tickers = list(wide.columns)
    mu = wide.mean().values * TRADING_DAYS
    cov = wide.cov().values * TRADING_DAYS
    n = len(tickers)

    vol = lambda w: np.sqrt(w @ cov @ w)
    ret = lambda w: w @ mu

    w_min = solve(lambda w: w @ cov @ w, n)
    w_tan = solve(lambda w: -(ret(w) - RISK_FREE_RATE) / vol(w), n)

    rows = []
    for target in np.linspace(ret(w_min), mu.max(), 60):
        w = solve(lambda w: w @ cov @ w, n, [{"type": "eq", "fun": lambda w, t=target: ret(w) - t}])
        rows.append({"portfolio_return": ret(w), "portfolio_volatility": vol(w),
                     "sharpe_ratio": (ret(w) - RISK_FREE_RATE) / vol(w),
                     **{f"weight_{t}": x for t, x in zip(tickers, w)}})
    frontier = pd.DataFrame(rows)

    opt = []
    for name, w in [("Max Sharpe (optimizer)", w_tan), ("Min Volatility (optimizer)", w_min),
                    ("Equal Weight", np.full(n, 1 / n))]:
        opt.append({"portfolio_type": name, "portfolio_return": ret(w), "portfolio_volatility": vol(w),
                    "sharpe_ratio": (ret(w) - RISK_FREE_RATE) / vol(w),
                    **{f"weight_{t}": round(x, 6) for t, x in zip(tickers, w)}})
    opt = pd.DataFrame(opt)

    frontier.to_csv(EXPORT_DIR / "efficient_frontier_exact.csv", index=False)
    opt.to_csv(EXPORT_DIR / "optimal_portfolios.csv", index=False)

    pd.set_option("display.width", 200)
    print(opt.round(3).to_string(index=False))
    print(f"\nExports: {EXPORT_DIR / 'efficient_frontier_exact.csv'}, {EXPORT_DIR / 'optimal_portfolios.csv'}")


if __name__ == "__main__":
    main()

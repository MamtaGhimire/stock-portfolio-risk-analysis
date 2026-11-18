# Findings Report: Stock Portfolio Risk Analysis

**Data:** Yahoo Finance daily prices, Jan 4, 2021 – Jul 24, 2026 (1,395 trading days)
**Holdings:** AAPL, MSFT, GOOGL, AMZN, JPM, JNJ, XOM
**Benchmark:** SPY (S&P 500 ETF)
**Returns:** total returns from adjusted close (dividends and splits included)

---

## 1. Which stocks were worth their risk?

The Sharpe ratio measures excess return per unit of volatility:

$$S = \frac{\mu - r_f}{\sigma}, \qquad \mu = 252\,\bar r, \quad \sigma = \sqrt{252}\,\text{sd}(r), \quad r_f = 4.5\%$$

| Rank | Ticker | Return | Volatility | Sharpe | Max drawdown | Beta |
|---:|---|---:|---:|---:|---:|---:|
| 1 | XOM | 31.7% | 27.3% | 1.00 | −20.5% | 0.45 |
| 2 | JPM | 24.2% | 24.2% | 0.81 | −38.8% | 0.88 |
| 3 | GOOGL | 28.7% | 31.3% | 0.77 | −44.3% | 1.26 |
| — | **SPY** | 15.3% | 16.8% | 0.64 | −24.5% | 1.00 |
| 4 | AAPL | 21.4% | 27.7% | 0.61 | −33.4% | 1.20 |
| 5 | JNJ | 13.7% | 17.2% | 0.53 | −18.4% | 0.19 |
| 6 | MSFT | 14.5% | 26.6% | 0.38 | −37.1% | 1.11 |
| 7 | AMZN | 12.8% | 34.7% | 0.24 | −56.1% | 1.46 |

- **XOM** delivered the highest return *and* the best Sharpe ratio. With a beta of 0.45, it moved much less with the market than the tech names did.
- **Only XOM, JPM and GOOGL beat SPY on a risk-adjusted basis.** AAPL returned more than SPY in raw terms (21.4% vs 15.3%) but carried 65% more volatility, so its Sharpe ratio is lower.
- **AMZN** is the weakest holding on every measure: the lowest return, the highest volatility, the highest beta (1.46), and a −56% drawdown.

**Why total returns matter:** using closing prices without dividends understates the dividend payers. XOM's Sharpe ratio rises from 0.85 to 1.00 and JNJ's from 0.37 to 0.53 once dividends are included.

## 2. Which stocks diversify the portfolio?

Correlation of daily returns, $\rho_{ij} = \text{Cov}(r_i, r_j) / (\sigma_i \sigma_j)$:

- **The tech cluster moves together:** AAPL, MSFT, GOOGL and AMZN have pairwise correlations of 0.54–0.62, and each has 0.68–0.73 with SPY.
- **JNJ is the strongest diversifier:** 0.00–0.14 with the tech names and 0.18 with SPY.
- **XOM also diversifies:** 0.05–0.15 with the tech names. Combined with its high return, that makes it the most valuable holding in the optimized portfolio.
- **JPM sits in the middle:** 0.27–0.33 with tech, 0.61 with SPY. It behaves much like the broad market.

## 3. What would an optimized portfolio have looked like?

Portfolio return and risk for weights $w$:

$$R_p = w^\top \mu, \qquad \sigma_p = \sqrt{w^\top \Sigma w}$$

Two methods were compared, both long-only with weights summing to 1:

1. **Monte Carlo:** 8,000 random weight vectors (`03_portfolio_analysis.py`)
2. **Convex optimizer:** SciPy SLSQP solving $\max_w (R_p - r_f)/\sigma_p$ exactly (`04_optimize_frontier.py`)

| Portfolio | Return | Volatility | Sharpe | Weights |
|---|---:|---:|---:|---|
| Max Sharpe (optimizer) | 25.4% | 16.0% | **1.31** | XOM 36.5%, JNJ 24.0%, GOOGL 23.4%, JPM 15.6%, AAPL 0.6% |
| Max Sharpe (Monte Carlo) | 24.8% | 15.9% | 1.27 | XOM 30.3%, GOOGL 22.6%, JNJ 20.8%, JPM 13.8%, AAPL 10.0% |
| Min Volatility (optimizer) | 18.2% | 13.2% | 1.04 | JNJ 52.3%, MSFT 16.2%, XOM 14.9%, JPM 10.8% |
| Equal weight | 21.0% | 17.4% | 0.95 | 1/7 each |
| Best single stock (XOM) | 31.7% | 27.3% | 1.00 | — |

- **The optimized blend beat every single stock.** Its Sharpe of 1.31 compares with XOM's 1.00, and its volatility is 41% lower.
- **The optimizer gives AMZN and MSFT zero weight** in the max-Sharpe portfolio. They add risk that the other holdings already cover, without enough return to make up for it.
- **Monte Carlo reached 97% of the optimal Sharpe ratio**, a good approximation. Still, 8,000 random draws never land exactly on the frontier, which is why the exact optimizer is worth running.
- **Even naive diversification helps:** the equal-weight portfolio (Sharpe 0.95) beat SPY (0.64) and 6 of the 7 individual stocks.

Growth of $1 from Jan 2021 to Jul 2026: equal-weight portfolio **$2.94**, SPY **$2.16**, XOM **$4.69**, AMZN **$1.46**.

## Bottom line

1. XOM, JPM and GOOGL were the portfolio's best risk-adjusted holdings. AMZN and MSFT were the weakest.
2. JNJ and XOM are the diversifiers: they have low correlation with tech and low beta.
3. A diversified, optimized portfolio beat every single stock on a risk-adjusted basis.

## Caveats

- The optimal weights are **in-sample**: they are fitted with hindsight on 2021–2026 data and will not necessarily hold going forward. A fair test would optimize on 2021–2023 and evaluate on 2024–2026.
- These figures assume a constant 4.5% risk-free rate, 252 trading days per year, and no costs, taxes or short selling.
- Arithmetic annualization ($252\,\bar r$) is slightly higher than the compound annual growth rate for volatile assets.
- Educational analysis, not investment advice.

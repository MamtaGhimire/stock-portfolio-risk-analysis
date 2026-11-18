# Tableau Dashboard Guide

Connect each CSV in `/exports` as a **Text File** data source (Data > New Data Source > Text File).
You can also join `prices_long.csv` to `summary_stats.csv` on `ticker` in one data source if you
prefer a single connection — Tableau relationships handle this cleanly.

---

## Dashboard 1 — Price Trends & Moving Averages
**Source:** `prices_long.csv`

1. Drag `trade_date` to Columns (set to continuous **Day**).
2. Drag `close` to Rows.
3. Drag `ticker` to **Color** and to **Filter** (so the user can pick 1+ stocks).
4. Add `sma_20` and `sma_50` as additional measures on Rows (dual-axis, synchronized) to show
   moving-average crossovers.
5. Add a reference line or a `daily_return` field mapped to point size for a "return heat" overlay (optional).

**Chart type:** Line chart, dual-axis.

---

## Dashboard 2 — Cumulative Returns Comparison
**Source:** `prices_long.csv` + `portfolio_equal_weight.csv` (union the two, since both have
`ticker`, `trade_date`, `daily_return`, `cumulative_return` columns)

1. `trade_date` → Columns (continuous).
2. `cumulative_return` → Rows.
3. `ticker` → Color (this will show each stock **and** your equal-weight portfolio as its own line —
   a great "did I beat my own portfolio" view).
4. Format Rows axis as percentage.

**Chart type:** Line chart.

---

## Dashboard 3 — Risk / Return Scatter (Bubble Chart)
**Source:** `summary_stats.csv`

1. `annual_volatility` → Columns.
2. `annual_return` → Rows.
3. `ticker` → Label and Color.
4. `sharpe_ratio` → Size (bigger bubble = better risk-adjusted return).
5. Add reference lines at the benchmark's (SPY) return and volatility values so it's obvious
   which stocks beat the market on a risk-adjusted basis.

**Chart type:** Scatter plot / bubble chart. This is the single best "which stock is worth the risk" view.

---

## Dashboard 4 — Correlation Heatmap
**Source:** `correlation_matrix_long.csv`

1. `ticker_1` → Columns.
2. `ticker_2` → Rows.
3. `correlation` → Color (use a diverging color palette, e.g. red–white–blue centered at 0).
4. `correlation` → Label (format as 2 decimals).
5. Change mark type to **Square**.

**Chart type:** Highlight table / heatmap. Low or negative correlations = good diversification candidates.

---

## Dashboard 5 — Efficient Frontier
**Source:** `efficient_frontier.csv` + `efficient_frontier_highlights.csv`

1. From `efficient_frontier.csv`: `portfolio_volatility` → Columns, `portfolio_return` → Rows.
   Set mark type to **Density/Circle**, reduce opacity to ~10-20% (8,000 points — this renders
   the frontier "cloud").
2. `sharpe_ratio` → Color, using a sequential palette.
3. Blend/union in `efficient_frontier_highlights.csv` and add its two points (Max Sharpe, Min
   Volatility) as a second mark layer with `portfolio_type` as Label, larger size, distinct color,
   so they stand out as annotated callouts on top of the cloud.

**Chart type:** Scatter with density coloring. This is the classic Markowitz efficient frontier chart.

---

## Combine into one Dashboard
Put charts 3 and 5 side by side (risk/return of individual stocks vs. optimal portfolios), and
1 + 2 on a second tab for time-series exploration. Add a global `ticker` filter action so
clicking a stock in the scatter plot highlights it in the price/return line charts.

---

## Optional — Exact frontier overlay
**Source:** `efficient_frontier_exact.csv` + `optimal_portfolios.csv` (from `python/04_optimize_frontier.py`)

On Dashboard 5, add `efficient_frontier_exact.csv` as a line layer (`portfolio_volatility` → Columns,
`portfolio_return` → Rows, mark type **Line**). It traces the true efficient frontier along the top-left
edge of the Monte Carlo cloud. Add the rows of `optimal_portfolios.csv` as labeled points to compare the
optimizer's Max Sharpe and Min Volatility portfolios with the Monte Carlo ones.

-- ============================================================
-- Stock Market Analysis: Core SQL Queries
-- These use window functions to compute returns, moving
-- averages, and rolling volatility directly in the database.
-- ============================================================

-- 1) Daily returns per ticker (using LAG window function)
-- ------------------------------------------------------------
SELECT
    ticker,
    trade_date,
    close,
    close / LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) - 1 AS daily_return
FROM prices
ORDER BY ticker, trade_date;


-- 2) 20-day and 50-day simple moving averages
-- ------------------------------------------------------------
SELECT
    ticker,
    trade_date,
    close,
    AVG(close) OVER (
        PARTITION BY ticker ORDER BY trade_date
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) AS sma_20,
    AVG(close) OVER (
        PARTITION BY ticker ORDER BY trade_date
        ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
    ) AS sma_50
FROM prices
ORDER BY ticker, trade_date;


-- 3) 30-day rolling volatility (std dev of daily returns, annualized)
-- ------------------------------------------------------------
WITH returns AS (
    SELECT
        ticker,
        trade_date,
        close / LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) - 1 AS daily_return
    FROM prices
)
SELECT
    ticker,
    trade_date,
    daily_return,
    -- SQLite has no native STDDEV, so the rolling standard deviation is
    -- finished in pandas -- see python/03_portfolio_analysis.py,
    -- add_derived_columns() -> "rolling_vol_30d".
    AVG(daily_return) OVER (
        PARTITION BY ticker ORDER BY trade_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS avg_return_30d
FROM returns
ORDER BY ticker, trade_date;


-- 4) Cumulative return since start of dataset, per ticker
-- ------------------------------------------------------------
WITH returns AS (
    SELECT
        ticker,
        trade_date,
        close,
        close / LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) - 1 AS daily_return
    FROM prices
)
SELECT
    ticker,
    trade_date,
    close,
    EXP(SUM(LN(1 + COALESCE(daily_return, 0))) OVER (
        PARTITION BY ticker ORDER BY trade_date
    )) - 1 AS cumulative_return
FROM returns
ORDER BY ticker, trade_date;
-- NOTE: SQLite's default build lacks EXP()/LN() unless the math
-- extension is loaded. python/03_portfolio_analysis.py computes this
-- in pandas instead so it works everywhere; this query is included
-- as the "correct SQL-native" version for engines like Postgres/MySQL
-- where EXP/LN are always available.


-- 5) Best and worst single trading day per ticker
-- ------------------------------------------------------------
WITH returns AS (
    SELECT
        ticker,
        trade_date,
        close / LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) - 1 AS daily_return
    FROM prices
),
ranked AS (
    SELECT *,
        RANK() OVER (PARTITION BY ticker ORDER BY daily_return DESC) AS best_rank,
        RANK() OVER (PARTITION BY ticker ORDER BY daily_return ASC) AS worst_rank
    FROM returns
    WHERE daily_return IS NOT NULL
)
SELECT ticker, trade_date, daily_return, 'best' AS type FROM ranked WHERE best_rank = 1
UNION ALL
SELECT ticker, trade_date, daily_return, 'worst' AS type FROM ranked WHERE worst_rank = 1
ORDER BY ticker, type;


-- 6) Sector-level average performance (join to tickers table)
-- ------------------------------------------------------------
WITH returns AS (
    SELECT
        ticker,
        trade_date,
        close / LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) - 1 AS daily_return
    FROM prices
)
SELECT
    t.sector,
    COUNT(DISTINCT r.ticker) AS num_stocks,
    AVG(r.daily_return) * 252 AS avg_annualized_return
FROM returns r
JOIN tickers t ON t.ticker = r.ticker
WHERE t.is_benchmark = 0
GROUP BY t.sector
ORDER BY avg_annualized_return DESC;

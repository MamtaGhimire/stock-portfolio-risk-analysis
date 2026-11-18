-- ============================================================
-- Stock Market Analysis: Database Schema
-- Engine: SQLite (portable; same DDL works in Postgres/MySQL
-- with minor type tweaks noted in comments)
-- ============================================================

DROP TABLE IF EXISTS tickers;
DROP TABLE IF EXISTS prices;

-- Reference table: one row per stock we track
CREATE TABLE tickers (
    ticker      TEXT PRIMARY KEY,
    company     TEXT NOT NULL,
    sector      TEXT,
    is_benchmark INTEGER DEFAULT 0   -- 1 = market benchmark (e.g. SPY)
);

-- Fact table: one row per ticker per trading day
CREATE TABLE prices (
    ticker      TEXT NOT NULL,
    trade_date  DATE NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    adj_close   REAL,
    volume      INTEGER,
    PRIMARY KEY (ticker, trade_date),
    FOREIGN KEY (ticker) REFERENCES tickers(ticker)
);

CREATE INDEX idx_prices_date ON prices(trade_date);
CREATE INDEX idx_prices_ticker ON prices(ticker);

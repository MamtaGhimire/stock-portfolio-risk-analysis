"""
05_make_charts.py
------------------
Static PNG charts for the README (docs/figures/). Reads the CSVs that
03_portfolio_analysis.py and 04_optimize_frontier.py write to /exports.
The interactive version of these views lives in Tableau (docs/TABLEAU_GUIDE.md).

    python 05_make_charts.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "exports"
FIG = ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
BLUE, ORANGE, RED, NEUTRAL = "#2a78d6", "#eb6834", "#e34948", "#f0efec"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2,
})
pct = matplotlib.ticker.PercentFormatter(1.0, decimals=0)


def risk_return():
    s = pd.read_csv(EXP / "summary_stats.csv")
    fig, ax = plt.subplots(figsize=(9, 6))
    for _, r in s.iterrows():
        bench = r.is_benchmark == 1
        ax.scatter(r.annual_volatility, r.annual_return, s=120 + 260 * max(r.sharpe_ratio, 0),
                   color=MUTED if bench else BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.annotate(f"{r.ticker}  (Sharpe {r.sharpe_ratio:.2f})", (r.annual_volatility, r.annual_return),
                    xytext=(10, 6), textcoords="offset points", fontsize=10, color=INK)
    spy = s[s.is_benchmark == 1].iloc[0]
    ax.axhline(spy.annual_return, color=MUTED, lw=1, ls="--", zorder=1)
    ax.axvline(spy.annual_volatility, color=MUTED, lw=1, ls="--", zorder=1)
    ax.xaxis.set_major_formatter(pct); ax.yaxis.set_major_formatter(pct)
    ax.set_xlabel("Annualized volatility"); ax.set_ylabel("Annualized total return")
    ax.set_title("Risk vs. return, 2021–2026 (bubble size = Sharpe ratio)")
    ax.text(0.99, 0.97, "dashed lines = S&P 500 (SPY)", transform=ax.transAxes, ha="right", va="top", color=INK2, fontsize=9)
    ax.set_xlim(0.12, 0.40)
    fig.tight_layout(); fig.savefig(FIG / "risk_return.png", dpi=160); plt.close(fig)


def correlation():
    c = pd.read_csv(EXP / "correlation_matrix_wide.csv", index_col=0)
    cmap = LinearSegmentedColormap.from_list("div", [RED, NEUTRAL, BLUE])
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    im = ax.imshow(c.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(c))); ax.set_xticklabels(c.columns)
    ax.set_yticks(range(len(c))); ax.set_yticklabels(c.index)
    ax.grid(False)
    for i in range(len(c)):
        for j in range(len(c)):
            ax.text(j, i, f"{c.values[i, j]:.2f}", ha="center", va="center", fontsize=9,
                    color=SURFACE if abs(c.values[i, j]) > 0.75 else INK)
    ax.set_title("Correlation of daily returns")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04); cb.outline.set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "correlation_heatmap.png", dpi=160); plt.close(fig)


def frontier():
    mc = pd.read_csv(EXP / "efficient_frontier.csv")
    ex = pd.read_csv(EXP / "efficient_frontier_exact.csv")
    op = pd.read_csv(EXP / "optimal_portfolios.csv").set_index("portfolio_type")
    s = pd.read_csv(EXP / "summary_stats.csv")
    s = s[s.is_benchmark == 0]
    fig, ax = plt.subplots(figsize=(9, 6))
    sc = ax.scatter(mc.portfolio_volatility, mc.portfolio_return, c=mc.sharpe_ratio, cmap="Blues",
                    s=6, alpha=0.6, linewidths=0, zorder=2)
    ax.plot(ex.portfolio_volatility, ex.portfolio_return, color=ORANGE, lw=2.5, zorder=3,
            label="Exact frontier (scipy optimizer)")
    for name, mk in [("Max Sharpe (optimizer)", "*"), ("Min Volatility (optimizer)", "D")]:
        r = op.loc[name]
        ax.scatter(r.portfolio_volatility, r.portfolio_return, marker=mk, s=260 if mk == "*" else 110,
                   color=ORANGE, edgecolor=INK, linewidth=1, zorder=5)
        ax.annotate(f"{name.split(' (')[0]}\nSharpe {r.sharpe_ratio:.2f}", (r.portfolio_volatility, r.portfolio_return),
                    xytext=(-14, 10) if mk == "*" else (14, -16), textcoords="offset points",
                    ha="right" if mk == "*" else "left", fontsize=10, color=INK)
    ax.scatter(s.annual_volatility, s.annual_return, color=INK2, s=40, zorder=4)
    for _, r in s.iterrows():
        ax.annotate(r.ticker, (r.annual_volatility, r.annual_return), xytext=(6, -3),
                    textcoords="offset points", fontsize=9, color=INK2)
    ax.xaxis.set_major_formatter(pct); ax.yaxis.set_major_formatter(pct)
    ax.set_xlabel("Annualized volatility"); ax.set_ylabel("Annualized total return")
    ax.set_title("Efficient frontier: 8,000 random portfolios vs. the optimizer")
    cb = fig.colorbar(sc, ax=ax, pad=0.02); cb.set_label("Sharpe ratio (random portfolios)"); cb.outline.set_visible(False)
    ax.legend(loc="lower center", frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "efficient_frontier.png", dpi=160); plt.close(fig)


def cumulative():
    p = pd.read_csv(EXP / "prices_long.csv", parse_dates=["trade_date"])
    eq = pd.read_csv(EXP / "portfolio_equal_weight.csv", parse_dates=["trade_date"])
    fig, ax = plt.subplots(figsize=(10, 6))
    for t, g in p[p.ticker != "SPY"].groupby("ticker"):
        ax.plot(g.trade_date, g.cumulative_return, color="#c9c8c2", lw=1.2, zorder=1)
        ax.annotate(t, (g.trade_date.iloc[-1], g.cumulative_return.iloc[-1]), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=9, color=MUTED)
    spy = p[p.ticker == "SPY"]
    ax.plot(spy.trade_date, spy.cumulative_return, color=INK2, lw=2, zorder=2, label="S&P 500 (SPY)")
    ax.plot(eq.trade_date, eq.cumulative_return, color=BLUE, lw=2.5, zorder=3, label="Equal-weight 7-stock portfolio")
    ax.yaxis.set_major_formatter(pct)
    ax.set_ylabel("Cumulative total return"); ax.set_title("Growth since January 2021")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout(); fig.savefig(FIG / "cumulative_returns.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    risk_return(); correlation(); frontier(); cumulative()
    print(f"Charts written to {FIG}")

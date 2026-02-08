"""
Strategy analysis module for the NBA EV Tracker.

Analyses historical betting data to produce performance metrics, ROI
breakdowns, EV-vs-actual correlation, line movement trends, and
sportsbook-level comparisons.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.config import STARTING_BANKROLL
from src.database import (
    get_all_settled_bets,
    get_bankroll_history,
    get_latest_bankroll,
    get_odds_history,
    insert_bankroll_snapshot,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bet history → DataFrame
# ---------------------------------------------------------------------------


def settled_bets_df() -> pd.DataFrame:
    """
    Load all settled bets into a DataFrame for analysis.

    Columns include: id, game_id, sportsbook, market_type, selection,
    odds_decimal, stake, ev_at_placement, edge_at_placement, placed_at,
    outcome, profit_loss, closing_odds, clv, home_team, away_team.
    """
    rows = get_all_settled_bets()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["placed_at"] = pd.to_datetime(df["placed_at"])
    return df


# ---------------------------------------------------------------------------
# Cumulative statistics
# ---------------------------------------------------------------------------


def compute_cumulative_stats(df: pd.DataFrame | None = None) -> dict[str, Any]:
    """
    Compute cumulative performance metrics from settled bets.

    Returns
    -------
    dict with keys:
        total_bets, wins, losses, pushes, win_rate, total_staked,
        total_profit, roi, avg_odds, avg_ev, avg_clv, bankroll.
    """
    if df is None:
        df = settled_bets_df()

    if df.empty:
        return {
            "total_bets": 0, "wins": 0, "losses": 0, "pushes": 0,
            "win_rate": 0.0, "total_staked": 0.0, "total_profit": 0.0,
            "roi": 0.0, "avg_odds": 0.0, "avg_ev": 0.0, "avg_clv": 0.0,
            "bankroll": STARTING_BANKROLL,
        }

    wins = (df["outcome"] == "win").sum()
    losses = (df["outcome"] == "loss").sum()
    pushes = (df["outcome"] == "push").sum()
    total = len(df)
    decided = wins + losses  # exclude pushes from win-rate calc

    total_staked = df["stake"].sum()
    total_profit = df["profit_loss"].sum()
    roi = (total_profit / total_staked * 100) if total_staked else 0.0
    win_rate = (wins / decided * 100) if decided else 0.0

    avg_odds = df["odds_decimal"].mean()
    avg_ev = df["ev_at_placement"].dropna().mean() if "ev_at_placement" in df else 0.0
    avg_clv = df["clv"].dropna().mean() if "clv" in df else 0.0

    bankroll_row = get_latest_bankroll()
    bankroll = bankroll_row["bankroll"] if bankroll_row else STARTING_BANKROLL + total_profit

    return {
        "total_bets": int(total),
        "wins": int(wins),
        "losses": int(losses),
        "pushes": int(pushes),
        "win_rate": round(win_rate, 2),
        "total_staked": round(total_staked, 2),
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
        "avg_odds": round(avg_odds, 3) if not np.isnan(avg_odds) else 0.0,
        "avg_ev": round(avg_ev, 2) if not np.isnan(avg_ev) else 0.0,
        "avg_clv": round(avg_clv, 2) if not np.isnan(avg_clv) else 0.0,
        "bankroll": round(bankroll, 2),
    }


def update_bankroll_snapshot() -> dict[str, Any]:
    """
    Compute latest cumulative stats and persist a bankroll snapshot.

    Returns the stats dict.
    """
    stats = compute_cumulative_stats()
    insert_bankroll_snapshot(
        bankroll=stats["bankroll"],
        cumulative_profit=stats["total_profit"],
        total_staked=stats["total_staked"],
        roi=stats["roi"],
        win_rate=stats["win_rate"],
        total_bets=stats["total_bets"],
    )
    logger.info("Bankroll snapshot saved — ROI %.2f%%, bankroll $%.2f",
                stats["roi"], stats["bankroll"])
    return stats


# ---------------------------------------------------------------------------
# Breakdown analyses
# ---------------------------------------------------------------------------


def roi_by_sportsbook(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Calculate ROI and record count broken down by sportsbook.

    Returns a DataFrame with columns: sportsbook, bets, staked,
    profit, roi.
    """
    if df is None:
        df = settled_bets_df()
    if df.empty:
        return pd.DataFrame(columns=["sportsbook", "bets", "staked", "profit", "roi"])

    grouped = df.groupby("sportsbook").agg(
        bets=("id", "count"),
        staked=("stake", "sum"),
        profit=("profit_loss", "sum"),
    ).reset_index()
    grouped["roi"] = (grouped["profit"] / grouped["staked"] * 100).round(2)
    return grouped.sort_values("roi", ascending=False)


def roi_by_market(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """ROI breakdown by market type (h2h, spreads, totals)."""
    if df is None:
        df = settled_bets_df()
    if df.empty:
        return pd.DataFrame(columns=["market_type", "bets", "staked", "profit", "roi"])

    grouped = df.groupby("market_type").agg(
        bets=("id", "count"),
        staked=("stake", "sum"),
        profit=("profit_loss", "sum"),
    ).reset_index()
    grouped["roi"] = (grouped["profit"] / grouped["staked"] * 100).round(2)
    return grouped.sort_values("roi", ascending=False)


def ev_vs_actual_correlation(df: pd.DataFrame | None = None) -> dict[str, Any]:
    """
    Measure how well predicted EV correlates with actual profit.

    Returns
    -------
    dict with keys: correlation, ev_buckets (DataFrame with avg EV-bin
    vs avg actual ROI).
    """
    if df is None:
        df = settled_bets_df()
    if df.empty or "ev_at_placement" not in df.columns:
        return {"correlation": 0.0, "ev_buckets": pd.DataFrame()}

    valid = df.dropna(subset=["ev_at_placement", "profit_loss"]).copy()
    if len(valid) < 3:
        return {"correlation": 0.0, "ev_buckets": pd.DataFrame()}

    corr = valid["ev_at_placement"].corr(valid["profit_loss"])

    # Bucket EV into 2% bins
    valid["ev_bin"] = pd.cut(valid["ev_at_placement"], bins=range(0, 30, 2))
    buckets = valid.groupby("ev_bin", observed=True).agg(
        count=("id", "count"),
        avg_ev=("ev_at_placement", "mean"),
        avg_profit=("profit_loss", "mean"),
    ).reset_index()

    return {
        "correlation": round(corr, 4) if not np.isnan(corr) else 0.0,
        "ev_buckets": buckets,
    }


def clv_analysis(df: pd.DataFrame | None = None) -> dict[str, Any]:
    """
    Analyse Closing Line Value across settled bets.

    Returns
    -------
    dict with keys: avg_clv, positive_clv_pct, clv_by_book (DataFrame).
    """
    if df is None:
        df = settled_bets_df()
    if df.empty or "clv" not in df.columns:
        return {"avg_clv": 0.0, "positive_clv_pct": 0.0,
                "clv_by_book": pd.DataFrame()}

    valid = df.dropna(subset=["clv"])
    if valid.empty:
        return {"avg_clv": 0.0, "positive_clv_pct": 0.0,
                "clv_by_book": pd.DataFrame()}

    avg_clv = valid["clv"].mean()
    pos_pct = (valid["clv"] > 0).mean() * 100

    by_book = valid.groupby("sportsbook").agg(
        bets=("id", "count"),
        avg_clv=("clv", "mean"),
    ).reset_index().sort_values("avg_clv", ascending=False)

    return {
        "avg_clv": round(avg_clv, 2),
        "positive_clv_pct": round(pos_pct, 1),
        "clv_by_book": by_book,
    }


# ---------------------------------------------------------------------------
# Line movement analysis
# ---------------------------------------------------------------------------


def line_movement_for_game(
    game_id: str, sportsbook: str | None = None
) -> pd.DataFrame:
    """
    Return a time-series of odds movements for a game.

    Columns: snapshot_time, sportsbook, market_type, selection, point,
    odds_decimal, implied_prob.
    """
    rows = get_odds_history(game_id, sportsbook=sportsbook)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    return df.sort_values("snapshot_time")


def detect_significant_movements(
    game_id: str, threshold_pct: float = 3.0
) -> list[dict[str, Any]]:
    """
    Detect odds movements that exceed a threshold from the first snapshot.

    Parameters
    ----------
    game_id : str
        Game to analyse.
    threshold_pct : float
        Minimum percentage change to flag.

    Returns
    -------
    list[dict]
        Each dict: sportsbook, market_type, selection, opening_odds,
        current_odds, change_pct.
    """
    df = line_movement_for_game(game_id)
    if df.empty:
        return []

    alerts: list[dict[str, Any]] = []
    grouped = df.groupby(["sportsbook", "market_type", "selection"])

    for (book, mtype, sel), group in grouped:
        opening = group.iloc[0]["odds_decimal"]
        latest = group.iloc[-1]["odds_decimal"]
        if opening == 0:
            continue
        change = ((latest - opening) / opening) * 100
        if abs(change) >= threshold_pct:
            alerts.append({
                "sportsbook": book,
                "market_type": mtype,
                "selection": sel,
                "opening_odds": round(opening, 3),
                "current_odds": round(latest, 3),
                "change_pct": round(change, 2),
            })

    return alerts


# ---------------------------------------------------------------------------
# Bankroll / ROI time-series
# ---------------------------------------------------------------------------


def bankroll_time_series() -> pd.DataFrame:
    """
    Load bankroll history as a DataFrame for plotting.

    Columns: snapshot_time, bankroll, cumulative_profit, roi, win_rate,
    total_bets.
    """
    rows = get_bankroll_history()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    return df


def cumulative_pnl_series(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Build a per-bet cumulative P&L series from settled bets.

    Useful for plotting the equity curve.

    Returns DataFrame with columns: placed_at, profit_loss, cumulative_pnl.
    """
    if df is None:
        df = settled_bets_df()
    if df.empty:
        return pd.DataFrame(columns=["placed_at", "profit_loss", "cumulative_pnl"])

    series = df[["placed_at", "profit_loss"]].sort_values("placed_at").copy()
    series["cumulative_pnl"] = series["profit_loss"].cumsum()
    return series


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    stats = compute_cumulative_stats()
    print("=== Cumulative Stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== ROI by Sportsbook ===")
    print(roi_by_sportsbook().to_string(index=False))

    print("\n=== EV vs Actual ===")
    ev_analysis = ev_vs_actual_correlation()
    print(f"  Correlation: {ev_analysis['correlation']}")

    print("\n=== CLV Analysis ===")
    clv_data = clv_analysis()
    print(f"  Avg CLV: {clv_data['avg_clv']}%")
    print(f"  Positive CLV %: {clv_data['positive_clv_pct']}%")

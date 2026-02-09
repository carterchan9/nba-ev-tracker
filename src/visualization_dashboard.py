"""
Streamlit dashboard for the NBA EV Tracker.

Run with:
    streamlit run src/visualization_dashboard.py

Provides:
- Live positive-EV opportunities table
- Line movement charts
- Bankroll / cumulative P&L chart
- ROI breakdowns by sportsbook and market
- EV vs actual profit scatter plot
- CLV distribution heatmap
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src.*` imports work when
# Streamlit runs this file directly.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import numpy as np

from src.config import MIN_EV_THRESHOLD, STARTING_BANKROLL, PREFERRED_REGION


def decimal_to_american(dec: float) -> str:
    """Convert decimal odds to American odds string (e.g. +150 or -110)."""
    if dec is None or np.isnan(dec) or dec <= 1:
        return ""
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    return f"{round(-100 / (dec - 1))}"


def format_commence_time(ts) -> str:
    """Format a timestamp to 'January 1, 2026, 7:30pm' style."""
    if pd.isna(ts):
        return ""
    t = pd.Timestamp(ts)
    return t.strftime("%B %-d, %Y, %-I:%M%p").replace("AM", "am").replace("PM", "pm")


def _prepare_ev_df(df: pd.DataFrame, keep_best_book_only: bool = False) -> pd.DataFrame:
    """
    Common prep for EV opportunity DataFrames: dedup, American odds, date format, benchmark.

    If keep_best_book_only=True, keeps only the best book (highest EV) for each unique
    market/selection/point combination, and adds num_positive_ev_books column.
    """
    # Deduplicate: keep only the latest entry per unique bet
    dedup_cols = ["game_id", "sportsbook", "market_type", "selection", "point", "player_name"]
    dedup_available = [c for c in dedup_cols if c in df.columns]
    df = df.sort_values("found_at", ascending=False).drop_duplicates(
        subset=dedup_available, keep="first"
    )

    # If requested, keep only best book per market/selection/point and add book count
    if keep_best_book_only:
        # Count how many books have positive EV for each market/selection/point combo
        group_cols = [c for c in ["game_id", "market_type", "player_name", "selection", "point"] if c in df.columns]
        df["num_positive_ev_books"] = df.groupby(group_cols)["ev_percent"].transform("count")
        # Keep only the best book (highest EV) for each combo
        df = df.sort_values("ev_percent", ascending=False).drop_duplicates(
            subset=group_cols, keep="first"
        )

    # American odds
    df["book_american"] = df["book_odds"].apply(decimal_to_american)
    df["benchmark_american"] = df["pinnacle_odds"].apply(decimal_to_american)
    # Friendly date format
    if "commence_time" in df.columns:
        df["commence_time"] = df["commence_time"].apply(format_commence_time)
    # Benchmark label — capitalise for display
    if "benchmark" in df.columns:
        df["benchmark"] = df["benchmark"].str.capitalize()
    else:
        df["benchmark"] = "Pinnacle"
    return df


from src.database import (
    get_all_latest_odds_for_game,
    get_ev_opportunities_by_date,
    get_last_scan_time,
    get_live_ev_opportunities,
    get_upcoming_games,
    init_schema,
)
from src.ev_calculation import scan_all_upcoming
from src.strategy_analysis import (
    bankroll_time_series,
    clv_analysis,
    compute_cumulative_stats,
    cumulative_pnl_series,
    ev_vs_actual_correlation,
    line_movement_for_game,
    roi_by_market,
    roi_by_sportsbook,
    settled_bets_df,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="NBA EV Tracker",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

page = st.sidebar.radio(
    "Navigation",
    [
        "Live EV Opportunities",
        "Historical Opportunities",
        "Line Movement",
        "Bankroll & P/L",
        "Performance Analytics",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"**Min EV threshold:** {MIN_EV_THRESHOLD}%\n\n"
    f"**Starting bankroll:** ${STARTING_BANKROLL:,.2f}"
)


# ---------------------------------------------------------------------------
# Display columns shared across Live and Historical pages
# ---------------------------------------------------------------------------

_DISPLAY_COLS = [
    "home_team", "away_team", "commence_time",
    "market_type", "player_name", "selection", "point", "pinnacle_point",
    "sportsbook", "book_odds", "book_american", "pinnacle_odds", "benchmark_american",
    "ev_percent", "edge_percent", "num_positive_ev_books", "benchmark",
]


# ===================================================================
# Page: Live EV Opportunities
# ===================================================================

if page == "Live EV Opportunities":
    st.title("Live Positive-EV Opportunities")

    col1, col2 = st.columns([3, 1])
    with col1:
        last_scan = get_last_scan_time()
        if last_scan:
            st.caption(f"Last refreshed: {format_commence_time(last_scan)}")
        else:
            st.caption("No scans recorded yet.")
    with col2:
        if st.button("Refresh (scan now)"):
            with st.spinner("Scanning upcoming games…"):
                new_opps = scan_all_upcoming()
            st.success(f"Found {len(new_opps)} opportunities.")
            st.rerun()

    # Load live opportunities (most recent scan only)
    opps = get_live_ev_opportunities()

    if opps:
        df = pd.DataFrame(opps)

        # Keep raw data before dedup for expansion view
        df_raw = df.copy()

        # Prepare display df: keep only best book per market/selection/point
        df = _prepare_ev_df(df, keep_best_book_only=True)
        available = [c for c in _DISPLAY_COLS if c in df.columns]

        st.markdown("### Best Book per Market (with Positive EV Book Count)")
        st.dataframe(
            df[available].sort_values("ev_percent", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        # --- Expandable view: all books for a selected market ---
        st.markdown("---")
        st.subheader("View All Books for a Market")

        # Build unique market combinations
        market_options = []
        market_map = {}
        for _, row in df.iterrows():
            game_label = f"{row.get('away_team', '?')} @ {row.get('home_team', '?')} ({row.get('commence_time', '')})"
            market_key = (row["game_id"], row["market_type"], row.get("player_name", ""),
                         row["selection"], row.get("point"))
            point_str = f" ({row['point']})" if pd.notna(row["point"]) else ""
            market_label = f"{game_label} — {row['market_type']} {row.get('player_name', '')} {row['selection']}{point_str}".replace("  ", " ")
            market_options.append(market_label)
            market_map[market_label] = market_key

        if market_options:
            selected_market_label = st.selectbox(
                "Select a market to view all book prices:",
                market_options,
                key="market_selector"
            )
            game_id, market_type, player_name, selection, point = market_map[selected_market_label]

            # Filter raw data for this market
            books_df = df_raw[
                (df_raw["game_id"] == game_id) &
                (df_raw["market_type"] == market_type) &
                ((df_raw["player_name"] == player_name) | (df_raw["player_name"].isna() & (player_name == ""))) &
                (df_raw["selection"] == selection)
            ].copy()
            # Also filter by point (handle NaN values)
            if pd.notna(point):
                books_df = books_df[books_df["point"] == point]
            else:
                books_df = books_df[books_df["point"].isna()]

            if not books_df.empty:
                books_df = _prepare_ev_df(books_df, keep_best_book_only=False)
                books_cols = ["sportsbook", "book_odds", "book_american", "pinnacle_odds",
                             "benchmark_american", "ev_percent", "edge_percent", "benchmark"]
                books_available = [c for c in books_cols if c in books_df.columns]
                st.dataframe(
                    books_df[books_available].sort_values("ev_percent", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No books found for this market.")

        # --- Game detail view ---
        st.markdown("---")
        st.subheader("Game Detail — All Available Markets")

        game_labels = {}
        for _, row in df_raw.drop_duplicates(subset=["game_id"]).iterrows():
            label = f"{row.get('away_team', '?')} @ {row.get('home_team', '?')} ({row.get('commence_time', '')})"
            game_labels[label] = row["game_id"]

        if game_labels:
            selected_label = st.selectbox("Select a game to view all markets", list(game_labels.keys()))
            selected_game_id = game_labels[selected_label]

            all_odds = get_all_latest_odds_for_game(selected_game_id)
            if all_odds:
                odds_df = pd.DataFrame(all_odds)
                odds_df["american"] = odds_df["odds_decimal"].apply(decimal_to_american)
                market_filter = st.multiselect(
                    "Filter by market",
                    odds_df["market_type"].unique().tolist(),
                    default=odds_df["market_type"].unique().tolist(),
                )
                filtered = odds_df[odds_df["market_type"].isin(market_filter)]
                st.dataframe(
                    filtered[["sportsbook", "market_type", "player_name", "selection",
                              "point", "odds_decimal", "american"]].sort_values(
                        ["market_type", "player_name", "selection", "sportsbook"]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No odds data stored for this game yet.")

        # Quick distribution chart
        st.subheader("EV Distribution")
        fig = px.histogram(
            df, x="ev_percent", nbins=20,
            labels={"ev_percent": "EV %"},
            title="Distribution of Positive-EV Opportunities",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No positive-EV opportunities found. Click 'Refresh' to scan for live opportunities.")


# ===================================================================
# Page: Historical Opportunities
# ===================================================================

elif page == "Historical Opportunities":
    st.title("Historical Positive-EV Opportunities")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        start_date = st.date_input("Start date", value=pd.Timestamp.now() - pd.Timedelta(days=7))
    with col2:
        end_date = st.date_input("End date", value=pd.Timestamp.now())
    with col3:
        min_ev = st.number_input("Min EV %", min_value=0.0, max_value=50.0, value=2.0, step=0.5)

    from datetime import datetime as dt, time as dtime
    start_dt = dt.combine(start_date, dtime.min)
    end_dt = dt.combine(end_date, dtime.max)

    opps = get_ev_opportunities_by_date(start_dt, end_dt, min_ev)

    if opps:
        df = pd.DataFrame(opps)
        df = _prepare_ev_df(df)

        st.metric("Total Opportunities", len(df))

        hist_cols = ["found_at"] + _DISPLAY_COLS
        available = [c for c in hist_cols if c in df.columns]
        st.dataframe(
            df[available].sort_values("ev_percent", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        # EV distribution
        st.subheader("EV Distribution")
        fig = px.histogram(
            df, x="ev_percent", nbins=20,
            labels={"ev_percent": "EV %"},
            title=f"Distribution of EV >= {min_ev}% Opportunities",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Breakdown by sportsbook
        st.subheader("Opportunities by Sportsbook")
        book_counts = df.groupby("sportsbook").size().reset_index(name="count")
        fig2 = px.bar(book_counts, x="sportsbook", y="count", labels={"count": "Opportunities"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No opportunities found for the selected date range and EV threshold.")


# ===================================================================
# Page: Line Movement
# ===================================================================

elif page == "Line Movement":
    st.title("Line Movement Tracker")

    games = get_upcoming_games()
    if not games:
        st.info("No upcoming games loaded yet.")
    else:
        game_options = {
            f"{g['away_team']} @ {g['home_team']} ({format_commence_time(g['commence_time'])})": g["game_id"]
            for g in games
        }
        selected_label = st.selectbox("Select a game", list(game_options.keys()))
        selected_game_id = game_options[selected_label]

        df = line_movement_for_game(selected_game_id)
        if df.empty:
            st.warning("No odds history for this game yet.")
        else:
            # Filter by market
            market_filter = st.multiselect(
                "Market type",
                df["market_type"].unique().tolist(),
                default=df["market_type"].unique().tolist(),
            )
            filtered = df[df["market_type"].isin(market_filter)]

            fig = px.line(
                filtered,
                x="snapshot_time",
                y="odds_decimal",
                color="sportsbook",
                line_dash="selection",
                facet_row="market_type",
                title="Odds Over Time",
                labels={
                    "snapshot_time": "Time",
                    "odds_decimal": "Decimal Odds",
                },
                height=600,
            )
            fig.update_layout(legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig, use_container_width=True)


# ===================================================================
# Page: Bankroll & P/L
# ===================================================================

elif page == "Bankroll & P/L":
    st.title("Bankroll & Profit / Loss")

    stats = compute_cumulative_stats()

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Bankroll", f"${stats['bankroll']:,.2f}")
    k2.metric("Total Profit", f"${stats['total_profit']:,.2f}")
    k3.metric("ROI", f"{stats['roi']:.2f}%")
    k4.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    k5.metric("Total Bets", stats["total_bets"])

    st.markdown("---")

    # Cumulative P&L chart
    st.subheader("Cumulative P&L Curve")
    pnl = cumulative_pnl_series()
    if not pnl.empty:
        fig = px.area(
            pnl, x="placed_at", y="cumulative_pnl",
            labels={"placed_at": "Date", "cumulative_pnl": "Cumulative P&L ($)"},
        )
        fig.add_hline(y=0, line_dash="dash", line_color="grey")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No settled bets yet — place and settle bets to see your equity curve.")

    # Bankroll history
    st.subheader("Bankroll History")
    bh = bankroll_time_series()
    if not bh.empty:
        fig2 = px.line(
            bh, x="snapshot_time", y="bankroll",
            labels={"snapshot_time": "Date", "bankroll": "Bankroll ($)"},
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No bankroll snapshots recorded yet.")


# ===================================================================
# Page: Performance Analytics
# ===================================================================

elif page == "Performance Analytics":
    st.title("Performance Analytics")

    df = settled_bets_df()
    if df.empty:
        st.info("No settled bets to analyse. Start placing bets to generate analytics.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "ROI Breakdown", "EV vs Actual", "CLV Analysis", "Heatmap"
        ])

        # --- Tab 1: ROI Breakdown ---
        with tab1:
            st.subheader("ROI by Sportsbook")
            roi_book = roi_by_sportsbook(df)
            if not roi_book.empty:
                fig = px.bar(
                    roi_book, x="sportsbook", y="roi",
                    color="roi",
                    color_continuous_scale=["red", "grey", "green"],
                    labels={"roi": "ROI %"},
                    text="bets",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("ROI by Market Type")
            roi_mkt = roi_by_market(df)
            if not roi_mkt.empty:
                fig2 = px.bar(
                    roi_mkt, x="market_type", y="roi",
                    color="roi",
                    color_continuous_scale=["red", "grey", "green"],
                    labels={"roi": "ROI %"},
                    text="bets",
                )
                st.plotly_chart(fig2, use_container_width=True)

        # --- Tab 2: EV vs Actual ---
        with tab2:
            st.subheader("EV at Placement vs Actual Profit")
            ev_data = ev_vs_actual_correlation(df)
            st.metric("Correlation (EV → Profit)", ev_data["correlation"])

            valid = df.dropna(subset=["ev_at_placement", "profit_loss"])
            if not valid.empty:
                fig = px.scatter(
                    valid, x="ev_at_placement", y="profit_loss",
                    color="outcome",
                    labels={
                        "ev_at_placement": "EV at Placement (%)",
                        "profit_loss": "Profit / Loss ($)",
                    },
                    trendline="ols",
                )
                st.plotly_chart(fig, use_container_width=True)

        # --- Tab 3: CLV Analysis ---
        with tab3:
            st.subheader("Closing Line Value")
            clv_data = clv_analysis(df)
            c1, c2 = st.columns(2)
            c1.metric("Avg CLV", f"{clv_data['avg_clv']:.2f}%")
            c2.metric("Bets Beating Close", f"{clv_data['positive_clv_pct']:.1f}%")

            clv_book = clv_data["clv_by_book"]
            if not clv_book.empty:
                fig = px.bar(
                    clv_book, x="sportsbook", y="avg_clv",
                    text="bets",
                    labels={"avg_clv": "Avg CLV %"},
                    title="Average CLV by Sportsbook",
                )
                st.plotly_chart(fig, use_container_width=True)

            clv_col = df.dropna(subset=["clv"])
            if not clv_col.empty:
                fig2 = px.histogram(
                    clv_col, x="clv", nbins=30,
                    labels={"clv": "CLV %"},
                    title="CLV Distribution",
                )
                st.plotly_chart(fig2, use_container_width=True)

        # --- Tab 4: Heatmap ---
        with tab4:
            st.subheader("Profit Heatmap — Sportsbook × Market")
            pivot = df.groupby(
                ["sportsbook", "market_type"]
            )["profit_loss"].sum().reset_index()
            if not pivot.empty:
                heat = pivot.pivot(
                    index="sportsbook", columns="market_type", values="profit_loss"
                ).fillna(0)
                fig = go.Figure(
                    data=go.Heatmap(
                        z=heat.values,
                        x=heat.columns.tolist(),
                        y=heat.index.tolist(),
                        colorscale="RdYlGn",
                        text=heat.values.round(2),
                        texttemplate="%{text}",
                    )
                )
                fig.update_layout(
                    title="P&L by Sportsbook × Market",
                    xaxis_title="Market",
                    yaxis_title="Sportsbook",
                )
                st.plotly_chart(fig, use_container_width=True)

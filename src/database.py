"""
Database module for the NBA EV Tracker.

Handles PostgreSQL connection pooling, schema initialisation, and all
CRUD operations for games, odds snapshots, Pinnacle odds, EV opportunities,
user bets, and bankroll history.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import psycopg2
import psycopg2.extras
import psycopg2.pool

from src.config import DATABASE_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool (module-level singleton)
# ---------------------------------------------------------------------------
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return (and lazily create) the module-level connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1, maxconn=10, dsn=DATABASE_URL
        )
        logger.info("Database connection pool created.")
    return _pool


@contextmanager
def get_connection() -> Generator:
    """Context manager that checks out / returns a pooled connection."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_pool() -> None:
    """Cleanly shut down the connection pool."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        logger.info("Database connection pool closed.")


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def init_schema() -> None:
    """Execute the SQL schema file to create tables if they don't exist."""
    sql = _SCHEMA_PATH.read_text()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("Database schema initialised.")


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------


def upsert_game(
    game_id: str,
    home_team: str,
    away_team: str,
    commence_time: datetime,
    home_score: int | None = None,
    away_score: int | None = None,
    status: str = "upcoming",
) -> None:
    """Insert a game or update its score / status on conflict."""
    sql = """
        INSERT INTO games (game_id, home_team, away_team, commence_time,
                           home_score, away_score, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (game_id) DO UPDATE SET
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            status     = EXCLUDED.status;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (game_id, home_team, away_team, commence_time,
                 home_score, away_score, status),
            )


def get_game(game_id: str) -> dict[str, Any] | None:
    """Fetch a single game by its ID."""
    sql = "SELECT * FROM games WHERE game_id = %s;"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (game_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def get_upcoming_games() -> list[dict[str, Any]]:
    """Return all games that have not yet completed."""
    sql = "SELECT * FROM games WHERE status != 'completed' ORDER BY commence_time;"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Odds snapshots
# ---------------------------------------------------------------------------


def insert_odds_snapshot(
    game_id: str,
    sportsbook: str,
    market_type: str,
    selection: str,
    odds_decimal: float,
    implied_prob: float,
    point: float | None = None,
    player_name: str | None = None,
    snapshot_time: datetime | None = None,
) -> None:
    """Store a single odds snapshot row."""
    sql = """
        INSERT INTO odds_snapshots
            (game_id, sportsbook, market_type, selection, point,
             player_name, odds_decimal, implied_prob, snapshot_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()));
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (game_id, sportsbook, market_type, selection,
                 point, player_name, odds_decimal, implied_prob, snapshot_time),
            )


def bulk_insert_odds(rows: list[tuple]) -> None:
    """
    Bulk-insert odds snapshot rows.

    Each tuple: (game_id, sportsbook, market_type, selection, point,
                 player_name, odds_decimal, implied_prob, snapshot_time)
    """
    sql = """
        INSERT INTO odds_snapshots
            (game_id, sportsbook, market_type, selection, point,
             player_name, odds_decimal, implied_prob, snapshot_time)
        VALUES %s;
    """
    if not rows:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    logger.info("Bulk-inserted %d odds snapshots.", len(rows))


def get_odds_history(
    game_id: str, sportsbook: str | None = None, market_type: str | None = None
) -> list[dict[str, Any]]:
    """Retrieve odds history for a game, optionally filtered by book / market."""
    clauses = ["game_id = %s"]
    params: list[Any] = [game_id]
    if sportsbook:
        clauses.append("sportsbook = %s")
        params.append(sportsbook)
    if market_type:
        clauses.append("market_type = %s")
        params.append(market_type)
    sql = (
        "SELECT * FROM odds_snapshots WHERE "
        + " AND ".join(clauses)
        + " ORDER BY snapshot_time;"
    )
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def get_latest_odds(game_id: str) -> list[dict[str, Any]]:
    """Get the most recent odds per sportsbook / market / selection / player for a game."""
    sql = """
        SELECT DISTINCT ON (sportsbook, market_type, selection, COALESCE(player_name, ''), COALESCE(point::text, ''))
            *
        FROM odds_snapshots
        WHERE game_id = %s
        ORDER BY sportsbook, market_type, selection, COALESCE(player_name, ''), COALESCE(point::text, ''), snapshot_time DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (game_id,))
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Pinnacle odds
# ---------------------------------------------------------------------------


def insert_pinnacle_odds(
    game_id: str,
    market_type: str,
    selection: str,
    odds_decimal: float,
    implied_prob: float,
    point: float | None = None,
    player_name: str | None = None,
    snapshot_time: datetime | None = None,
    is_closing: bool = False,
) -> None:
    """Store a Pinnacle odds row."""
    sql = """
        INSERT INTO pinnacle_odds
            (game_id, market_type, selection, point, player_name,
             odds_decimal, implied_prob, snapshot_time, is_closing)
        VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), %s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (game_id, market_type, selection, point, player_name,
                 odds_decimal, implied_prob, snapshot_time, is_closing),
            )


def bulk_insert_pinnacle_odds(rows: list[tuple]) -> None:
    """
    Bulk-insert Pinnacle odds rows.

    Each tuple: (game_id, market_type, selection, point, player_name,
                 odds_decimal, implied_prob, snapshot_time, is_closing)
    """
    sql = """
        INSERT INTO pinnacle_odds
            (game_id, market_type, selection, point, player_name,
             odds_decimal, implied_prob, snapshot_time, is_closing)
        VALUES %s;
    """
    if not rows:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    logger.info("Bulk-inserted %d Pinnacle odds rows.", len(rows))


def get_latest_pinnacle_odds(
    game_id: str, market_type: str | None = None
) -> list[dict[str, Any]]:
    """Most recent Pinnacle line per market / selection / player for a game."""
    clauses = ["game_id = %s"]
    params: list[Any] = [game_id]
    if market_type:
        clauses.append("market_type = %s")
        params.append(market_type)
    sql = (
        "SELECT DISTINCT ON (market_type, selection, COALESCE(player_name, ''), COALESCE(point::text, '')) * "
        "FROM pinnacle_odds WHERE "
        + " AND ".join(clauses)
        + " ORDER BY market_type, selection, COALESCE(player_name, ''), COALESCE(point::text, ''), snapshot_time DESC;"
    )
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def get_closing_pinnacle_odds(game_id: str) -> list[dict[str, Any]]:
    """Return Pinnacle closing lines for a game."""
    sql = """
        SELECT * FROM pinnacle_odds
        WHERE game_id = %s AND is_closing = TRUE
        ORDER BY market_type, selection, player_name;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (game_id,))
            return [dict(r) for r in cur.fetchall()]


def mark_pinnacle_closing(game_id: str) -> None:
    """
    Mark the latest Pinnacle odds for a game as the closing line.
    Called when a game transitions to 'live' or 'completed'.
    """
    sql = """
        UPDATE pinnacle_odds
        SET is_closing = TRUE
        WHERE id IN (
            SELECT DISTINCT ON (market_type, selection, COALESCE(player_name, ''), COALESCE(point::text, '')) id
            FROM pinnacle_odds
            WHERE game_id = %s
            ORDER BY market_type, selection, COALESCE(player_name, ''), COALESCE(point::text, ''), snapshot_time DESC
        );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (game_id,))
    logger.info("Marked closing Pinnacle odds for game %s.", game_id)


# ---------------------------------------------------------------------------
# EV opportunities
# ---------------------------------------------------------------------------


def insert_ev_opportunity(
    game_id: str,
    sportsbook: str,
    market_type: str,
    selection: str,
    book_odds: float,
    pinnacle_odds: float,
    ev_percent: float,
    edge_percent: float,
    point: float | None = None,
    player_name: str | None = None,
    benchmark: str = "pinnacle",
) -> int:
    """Insert a positive-EV opportunity; returns the new row id."""
    sql = """
        INSERT INTO ev_opportunities
            (game_id, sportsbook, market_type, selection, point,
             player_name, book_odds, pinnacle_odds, ev_percent, edge_percent,
             benchmark)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (game_id, sportsbook, market_type, selection, point,
                 player_name, book_odds, pinnacle_odds, ev_percent, edge_percent,
                 benchmark),
            )
            row_id: int = cur.fetchone()[0]
    return row_id


def get_recent_ev_opportunities(hours: int = 24) -> list[dict[str, Any]]:
    """Get EV opportunities found in the last N hours."""
    sql = """
        SELECT eo.*, g.home_team, g.away_team, g.commence_time
        FROM ev_opportunities eo
        JOIN games g ON g.game_id = eo.game_id
        WHERE eo.found_at >= NOW() - INTERVAL '%s hours'
        ORDER BY eo.ev_percent DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (hours,))
            return [dict(r) for r in cur.fetchall()]


def get_ev_opportunities_by_date(
    start_date: datetime,
    end_date: datetime,
    min_ev: float = 2.0,
) -> list[dict[str, Any]]:
    """Get historical EV opportunities within a date range, filtered by minimum EV%."""
    sql = """
        SELECT eo.*, g.home_team, g.away_team, g.commence_time
        FROM ev_opportunities eo
        JOIN games g ON g.game_id = eo.game_id
        WHERE eo.found_at >= %s AND eo.found_at <= %s
          AND eo.ev_percent >= %s
        ORDER BY eo.found_at DESC, eo.ev_percent DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (start_date, end_date, min_ev))
            return [dict(r) for r in cur.fetchall()]


def get_all_latest_odds_for_game(game_id: str) -> list[dict[str, Any]]:
    """Get the most recent odds from every sportsbook for a game (all markets)."""
    sql = """
        SELECT DISTINCT ON (sportsbook, market_type, selection,
                            COALESCE(player_name, ''), COALESCE(point::text, ''))
            sportsbook, market_type, selection, point, player_name,
            odds_decimal, implied_prob, snapshot_time
        FROM odds_snapshots
        WHERE game_id = %s
        ORDER BY sportsbook, market_type, selection,
                 COALESCE(player_name, ''), COALESCE(point::text, ''),
                 snapshot_time DESC;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (game_id,))
            return [dict(r) for r in cur.fetchall()]


def get_last_scan_time() -> datetime | None:
    """Return the timestamp of the most recent EV opportunity scan."""
    sql = "SELECT MAX(found_at) AS last_scan FROM ev_opportunities;"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()
    return row["last_scan"] if row and row["last_scan"] else None


# ---------------------------------------------------------------------------
# User bets
# ---------------------------------------------------------------------------


def insert_user_bet(
    game_id: str,
    sportsbook: str,
    market_type: str,
    selection: str,
    odds_decimal: float,
    stake: float,
    ev_at_placement: float | None = None,
    edge_at_placement: float | None = None,
    point: float | None = None,
    player_name: str | None = None,
) -> int:
    """Record a user bet; returns the new row id."""
    sql = """
        INSERT INTO user_bets
            (game_id, sportsbook, market_type, selection, point,
             player_name, odds_decimal, stake, ev_at_placement, edge_at_placement)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (game_id, sportsbook, market_type, selection, point,
                 player_name, odds_decimal, stake, ev_at_placement, edge_at_placement),
            )
            row_id: int = cur.fetchone()[0]
    return row_id


def settle_bet(
    bet_id: int,
    outcome: str,
    profit_loss: float,
    closing_odds: float | None = None,
    clv: float | None = None,
) -> None:
    """Update a bet after the game result is known."""
    sql = """
        UPDATE user_bets
        SET outcome = %s, profit_loss = %s,
            closing_odds = %s, clv = %s
        WHERE id = %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (outcome, profit_loss, closing_odds, clv, bet_id))


def get_pending_bets() -> list[dict[str, Any]]:
    """Return all unsettled bets."""
    sql = """
        SELECT ub.*, g.home_team, g.away_team, g.commence_time,
               g.home_score, g.away_score, g.status AS game_status
        FROM user_bets ub
        JOIN games g ON g.game_id = ub.game_id
        WHERE ub.outcome IS NULL
        ORDER BY g.commence_time;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


def get_all_settled_bets() -> list[dict[str, Any]]:
    """Return all settled bets for analysis."""
    sql = """
        SELECT ub.*, g.home_team, g.away_team
        FROM user_bets ub
        JOIN games g ON g.game_id = ub.game_id
        WHERE ub.outcome IS NOT NULL
        ORDER BY ub.placed_at;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Bankroll history
# ---------------------------------------------------------------------------


def insert_bankroll_snapshot(
    bankroll: float,
    cumulative_profit: float,
    total_staked: float,
    roi: float,
    win_rate: float,
    total_bets: int,
) -> None:
    """Append a bankroll snapshot row."""
    sql = """
        INSERT INTO bankroll_history
            (bankroll, cumulative_profit, total_staked, roi, win_rate, total_bets)
        VALUES (%s, %s, %s, %s, %s, %s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (bankroll, cumulative_profit, total_staked,
                 roi, win_rate, total_bets),
            )


def get_bankroll_history() -> list[dict[str, Any]]:
    """Full bankroll history for charting."""
    sql = "SELECT * FROM bankroll_history ORDER BY snapshot_time;"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


def get_latest_bankroll() -> dict[str, Any] | None:
    """Most recent bankroll snapshot."""
    sql = "SELECT * FROM bankroll_history ORDER BY snapshot_time DESC LIMIT 1;"
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_schema()
    print("Schema initialised successfully.")

"""
Data fetching module for the NBA EV Tracker.

Pulls live NBA odds from The Odds API for all configured sportsbooks
plus Pinnacle, normalises everything to decimal format, and can also
fetch completed-game scores to settle bets.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from src.config import (
    ALL_BOOKMAKERS,
    GAME_MARKETS,
    ODDS_API_BASE_URL,
    ODDS_API_KEY,
    ODDS_API_REGIONS,
    PINNACLE_KEY,
    PROP_MARKETS,
    SPORT_KEY,
    SPORTSBOOKS,
)
from src.database import (
    bulk_insert_odds,
    bulk_insert_pinnacle_odds,
    mark_pinnacle_closing,
    upsert_game,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Odds-format helpers
# ---------------------------------------------------------------------------


def american_to_decimal(american: int | float) -> float:
    """
    Convert American odds to decimal odds.

    >>> american_to_decimal(-110)
    1.909090909090909
    >>> american_to_decimal(150)
    2.5
    """
    if american > 0:
        return 1 + american / 100
    return 1 + 100 / abs(american)


def decimal_to_implied_probability(decimal_odds: float) -> float:
    """
    Convert decimal odds to implied probability (0-1).

    >>> round(decimal_to_implied_probability(2.0), 4)
    0.5
    """
    if decimal_odds <= 0:
        return 0.0
    return 1 / decimal_odds


# ---------------------------------------------------------------------------
# The Odds API — fetch odds
# ---------------------------------------------------------------------------


def fetch_odds_for_market(market: str) -> list[dict[str, Any]]:
    """
    Fetch odds for a single game-level market from The Odds API.

    Parameters
    ----------
    market : str
        One of 'h2h', 'spreads', 'totals'.

    Returns
    -------
    list[dict]
        Raw JSON response — list of event objects.
    """
    url = f"{ODDS_API_BASE_URL}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_API_REGIONS,
        "markets": market,
        "oddsFormat": "decimal",
        "bookmakers": ",".join(ALL_BOOKMAKERS),
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    remaining = resp.headers.get("x-requests-remaining", "?")
    logger.info(
        "Fetched %s odds — %s events — API requests remaining: %s",
        market, len(resp.json()), remaining,
    )
    return resp.json()


def _fetch_event_ids() -> list[str]:
    """Fetch the list of upcoming event IDs for the sport."""
    url = f"{ODDS_API_BASE_URL}/sports/{SPORT_KEY}/events"
    params = {"apiKey": ODDS_API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return [e["id"] for e in resp.json()]


def fetch_props_for_event(event_id: str, markets: list[str]) -> dict[str, Any] | None:
    """
    Fetch player prop odds for a single event using the per-event endpoint.

    Parameters
    ----------
    event_id : str
        The Odds API event ID.
    markets : list[str]
        Prop market keys, e.g. ['player_points', 'player_rebounds', 'player_assists'].

    Returns
    -------
    dict | None
        Single event object with bookmaker/market data, or None on failure.
    """
    url = f"{ODDS_API_BASE_URL}/sports/{SPORT_KEY}/events/{event_id}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_API_REGIONS,
        "markets": ",".join(markets),
        "oddsFormat": "decimal",
        "bookmakers": ",".join(ALL_BOOKMAKERS),
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    remaining = resp.headers.get("x-requests-remaining", "?")
    logger.info(
        "Fetched props for event %s — API requests remaining: %s",
        event_id, remaining,
    )
    return resp.json()


def fetch_all_odds() -> list[dict[str, Any]]:
    """
    Fetch odds for every configured market and return the combined list
    of event objects.

    Game markets (h2h, spreads, totals) use the bulk endpoint.
    Player props use the per-event endpoint.
    """
    all_events: list[dict[str, Any]] = []

    # Game markets — bulk fetch
    for market in GAME_MARKETS:
        try:
            events = fetch_odds_for_market(market)
            all_events.extend(events)
        except requests.RequestException as exc:
            logger.error("Failed to fetch %s odds: %s", market, exc)

    # Player props — per-event fetch
    if PROP_MARKETS:
        try:
            event_ids = _fetch_event_ids()
        except requests.RequestException as exc:
            logger.error("Failed to fetch event list for props: %s", exc)
            event_ids = []

        for i, eid in enumerate(event_ids):
            if i > 0:
                time.sleep(1)  # rate-limit: 1 second between per-event calls
            try:
                event = fetch_props_for_event(eid, PROP_MARKETS)
                if event:
                    all_events.append(event)
            except requests.RequestException as exc:
                logger.error("Failed to fetch props for event %s: %s", eid, exc)

    return all_events


# ---------------------------------------------------------------------------
# Parsing & normalisation
# ---------------------------------------------------------------------------


def _parse_market_type(market_key: str) -> str:
    """Map The Odds API market key to our internal type (identity for all known keys)."""
    return market_key


def parse_and_store_odds(events: list[dict[str, Any]]) -> dict[str, list[dict]]:
    """
    Parse raw API events, upsert games, and store odds in the database.

    Returns a dict with keys ``"sportsbook_rows"`` and ``"pinnacle_rows"``
    containing the structured data that was persisted.
    """
    now = datetime.now(timezone.utc)
    sportsbook_rows: list[tuple] = []
    pinnacle_rows: list[tuple] = []

    for event in events:
        game_id = event["id"]
        home = event["home_team"]
        away = event["away_team"]
        commence = datetime.fromisoformat(event["commence_time"])

        # Upsert the game record
        upsert_game(game_id, home, away, commence)

        for bookmaker in event.get("bookmakers", []):
            book_key = bookmaker["key"]

            for market in bookmaker.get("markets", []):
                market_type = _parse_market_type(market["key"])

                for outcome in market.get("outcomes", []):
                    selection = outcome["name"]
                    odds_dec = float(outcome["price"])
                    point = outcome.get("point")
                    player_name = outcome.get("description")  # player name for props, None for game markets
                    impl_prob = decimal_to_implied_probability(odds_dec)

                    # Sportsbook row: (game_id, book_key, market_type, selection,
                    #   point, player_name, odds_dec, impl_prob, snapshot_time)
                    row = (
                        game_id, book_key, market_type, selection,
                        point, player_name, odds_dec, impl_prob, now,
                    )

                    if book_key == PINNACLE_KEY:
                        # Pinnacle row: (game_id, market_type, selection, point,
                        #   player_name, odds_dec, impl_prob, snapshot_time, is_closing)
                        pin_row = (
                            game_id, market_type, selection, point,
                            player_name, odds_dec, impl_prob, now, False,
                        )
                        pinnacle_rows.append(pin_row)
                    else:
                        sportsbook_rows.append(row)

    # Bulk persist
    bulk_insert_odds(sportsbook_rows)
    bulk_insert_pinnacle_odds(pinnacle_rows)

    logger.info(
        "Stored %d sportsbook odds + %d Pinnacle odds.",
        len(sportsbook_rows), len(pinnacle_rows),
    )
    return {
        "sportsbook_rows": sportsbook_rows,
        "pinnacle_rows": pinnacle_rows,
    }


# ---------------------------------------------------------------------------
# Fetch game results (scores)
# ---------------------------------------------------------------------------


def fetch_scores(days_from: int = 3) -> list[dict[str, Any]]:
    """
    Fetch recently completed NBA game scores from The Odds API.

    Parameters
    ----------
    days_from : int
        Number of days in the past to look for completed games.

    Returns
    -------
    list[dict]
        Raw API response with score data.
    """
    url = f"{ODDS_API_BASE_URL}/sports/{SPORT_KEY}/scores"
    params = {
        "apiKey": ODDS_API_KEY,
        "daysFrom": days_from,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_game_results(scores: list[dict[str, Any]] | None = None) -> list[str]:
    """
    Fetch (or accept pre-fetched) scores and update the games table.
    Also marks Pinnacle closing odds for newly completed games.

    Returns a list of game_ids that transitioned to 'completed'.
    """
    if scores is None:
        scores = fetch_scores()

    newly_completed: list[str] = []

    for event in scores:
        game_id = event["id"]
        completed = event.get("completed", False)

        if not completed:
            continue

        home_team = event["home_team"]
        away_team = event["away_team"]
        commence = datetime.fromisoformat(event["commence_time"])

        home_score = None
        away_score = None
        for score_entry in event.get("scores", []) or []:
            if score_entry["name"] == home_team:
                home_score = int(score_entry["score"])
            elif score_entry["name"] == away_team:
                away_score = int(score_entry["score"])

        upsert_game(
            game_id, home_team, away_team, commence,
            home_score=home_score, away_score=away_score,
            status="completed",
        )

        # Mark Pinnacle closing line
        mark_pinnacle_closing(game_id)
        newly_completed.append(game_id)

    if newly_completed:
        logger.info("Updated %d completed games.", len(newly_completed))
    return newly_completed


# ---------------------------------------------------------------------------
# High-level "pull everything" convenience function
# ---------------------------------------------------------------------------


def pull_and_store_latest() -> dict[str, Any]:
    """
    End-to-end: fetch all odds, store them, fetch scores, update results.
    Returns a summary dict.
    """
    events = fetch_all_odds()
    odds_summary = parse_and_store_odds(events)
    completed_ids = update_game_results()
    return {
        "events_fetched": len(events),
        "sportsbook_odds_stored": len(odds_summary["sportsbook_rows"]),
        "pinnacle_odds_stored": len(odds_summary["pinnacle_rows"]),
        "games_completed": completed_ids,
    }


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Pulling latest odds and scores …")
    summary = pull_and_store_latest()
    print(f"Done — {summary}")

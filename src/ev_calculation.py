"""
EV calculation module for the NBA EV Tracker.

Computes Expected Value, edge, implied probability, and Closing Line
Value (CLV).  Also provides a scanner that compares every sportsbook
line against Pinnacle to surface positive-EV opportunities.
"""

from __future__ import annotations

import logging
from typing import Any

import statistics

from src.config import MIN_EV_THRESHOLD, PINNACLE_KEY, PROP_MARKETS, SPORTSBOOKS
from src.database import (
    get_closing_pinnacle_odds,
    get_latest_odds,
    get_latest_pinnacle_odds,
    get_pending_bets,
    get_upcoming_games,
    insert_ev_opportunity,
    settle_bet,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------


def implied_probability(decimal_odds: float) -> float:
    """
    Convert decimal odds to implied probability.

    Parameters
    ----------
    decimal_odds : float
        Decimal odds (e.g. 1.91 for -110).

    Returns
    -------
    float
        Implied probability between 0 and 1.

    Example
    -------
    >>> round(implied_probability(2.0), 4)
    0.5
    """
    if decimal_odds <= 0:
        return 0.0
    return 1.0 / decimal_odds


def no_vig_probability(odds_side_a: float, odds_side_b: float) -> tuple[float, float]:
    """
    Remove the vig (overround) from a two-way market to get fair probabilities.

    Parameters
    ----------
    odds_side_a : float
        Decimal odds for side A.
    odds_side_b : float
        Decimal odds for side B.

    Returns
    -------
    tuple[float, float]
        (fair_prob_a, fair_prob_b) summing to 1.0.

    Example
    -------
    >>> a, b = no_vig_probability(1.91, 1.91)
    >>> round(a, 4), round(b, 4)
    (0.5, 0.5)
    """
    raw_a = implied_probability(odds_side_a)
    raw_b = implied_probability(odds_side_b)
    total = raw_a + raw_b
    if total == 0:
        return 0.0, 0.0
    return raw_a / total, raw_b / total


def calculate_ev(
    book_odds: float,
    fair_probability: float,
) -> float:
    """
    Calculate Expected Value as a percentage of the stake.

    EV% = (fair_prob * (book_odds - 1) - (1 - fair_prob)) * 100

    Parameters
    ----------
    book_odds : float
        Decimal odds offered by the sportsbook.
    fair_probability : float
        "True" win probability (e.g. from Pinnacle no-vig).

    Returns
    -------
    float
        EV expressed as a percentage (positive means +EV).

    Example
    -------
    >>> round(calculate_ev(2.10, 0.52), 2)
    5.2
    """
    ev = (fair_probability * (book_odds - 1) - (1 - fair_probability)) * 100
    return ev


def calculate_edge(book_odds: float, pinnacle_odds: float) -> float:
    """
    Calculate the edge of a sportsbook line vs Pinnacle.

    Edge% = ((book_odds / pinnacle_odds) - 1) * 100

    A positive edge means the book is offering better odds than Pinnacle.

    Parameters
    ----------
    book_odds : float
        Decimal odds at the sportsbook.
    pinnacle_odds : float
        Decimal odds at Pinnacle.

    Returns
    -------
    float
        Edge as a percentage.

    Example
    -------
    >>> round(calculate_edge(2.10, 2.00), 2)
    5.0
    """
    if pinnacle_odds <= 0:
        return 0.0
    return ((book_odds / pinnacle_odds) - 1) * 100


def calculate_clv(placed_odds: float, closing_odds: float) -> float:
    """
    Calculate Closing Line Value — how much better the placed odds were
    compared to the closing (last pre-game) Pinnacle line.

    CLV% = ((placed_odds / closing_odds) - 1) * 100

    Positive CLV means the bettor beat the closing line.

    Parameters
    ----------
    placed_odds : float
        Decimal odds at time of bet placement.
    closing_odds : float
        Pinnacle closing decimal odds.

    Returns
    -------
    float
        CLV as a percentage.
    """
    if closing_odds <= 0:
        return 0.0
    return ((placed_odds / closing_odds) - 1) * 100


# ---------------------------------------------------------------------------
# Opportunity scanner
# ---------------------------------------------------------------------------


def _build_pinnacle_lookup(
    pinnacle_rows: list[dict[str, Any]],
) -> dict[tuple, dict[str, Any]]:
    """
    Build a lookup dict keyed by (market_type, selection, point, player_name)
    from Pinnacle odds rows so we can quickly match sportsbook lines.
    """
    lookup: dict[tuple, dict[str, Any]] = {}
    for row in pinnacle_rows:
        key = (row["market_type"], row["selection"], row.get("point"), row.get("player_name"))
        lookup[key] = row
    return lookup


MIN_BOOKS_FOR_CONSENSUS = 3  # need at least 3 books to form a reliable consensus


def _build_consensus_benchmark(
    book_odds: list[dict[str, Any]],
) -> dict[tuple, dict[str, Any]]:
    """
    Build a consensus (median) benchmark from sportsbook odds for markets
    that have no Pinnacle line (i.e. player props).

    Groups all sportsbook odds by (market_type, selection, point, player_name),
    computes the median decimal odds across books, and returns a lookup in
    the same format as the Pinnacle lookup.

    Only includes lines where at least MIN_BOOKS_FOR_CONSENSUS sportsbooks
    offer the same market.
    """
    # Collect odds per unique line
    groups: dict[tuple, list[float]] = {}
    for row in book_odds:
        if row["sportsbook"] not in SPORTSBOOKS:
            continue
        key = (row["market_type"], row["selection"], row.get("point"), row.get("player_name"))
        groups.setdefault(key, []).append(row["odds_decimal"])

    lookup: dict[tuple, dict[str, Any]] = {}
    for key, odds_list in groups.items():
        if len(odds_list) < MIN_BOOKS_FOR_CONSENSUS:
            continue
        median_odds = statistics.median(odds_list)
        lookup[key] = {
            "market_type": key[0],
            "selection": key[1],
            "point": key[2],
            "player_name": key[3],
            "odds_decimal": median_odds,
            "implied_prob": implied_probability(median_odds),
            "num_books": len(odds_list),
        }
    return lookup


def scan_ev_opportunities_for_game(
    game_id: str,
) -> list[dict[str, Any]]:
    """
    Compare every sportsbook line for a game against a benchmark to find +EV bets.

    - **Game markets** (h2h, spreads, totals): benchmark is Pinnacle no-vig.
    - **Player props**: benchmark is the consensus (median) line across all
      sportsbooks, since Pinnacle props are unavailable.

    An opportunity is flagged when EV% >= MIN_EV_THRESHOLD.

    Parameters
    ----------
    game_id : str
        The game to scan.

    Returns
    -------
    list[dict]
        List of opportunity dicts.
    """
    book_odds = get_latest_odds(game_id)
    pin_odds = get_latest_pinnacle_odds(game_id)

    # Build Pinnacle lookup for game markets
    pin_lookup = _build_pinnacle_lookup(pin_odds) if pin_odds else {}

    # Group Pinnacle odds by (market, point, player_name) for no-vig calc
    pin_by_market: dict[tuple, list[dict]] = {}
    for row in (pin_odds or []):
        mkt_key = (row["market_type"], row.get("point"), row.get("player_name"))
        pin_by_market.setdefault(mkt_key, []).append(row)

    # Build consensus benchmark for props (and any market missing Pinnacle)
    consensus_lookup = _build_consensus_benchmark(book_odds)

    # Group consensus by (market, point, player_name) for no-vig calc
    consensus_by_market: dict[tuple, list[dict]] = {}
    for key, row in consensus_lookup.items():
        mkt_key = (row["market_type"], row.get("point"), row.get("player_name"))
        consensus_by_market.setdefault(mkt_key, []).append(row)

    opportunities: list[dict[str, Any]] = []

    for odds_row in book_odds:
        book_key = odds_row["sportsbook"]
        if book_key not in SPORTSBOOKS:
            continue

        mtype = odds_row["market_type"]
        selection = odds_row["selection"]
        point = odds_row.get("point")
        player_name = odds_row.get("player_name")
        book_dec = odds_row["odds_decimal"]

        lookup_key = (mtype, selection, point, player_name)
        is_prop = mtype in PROP_MARKETS

        # Choose benchmark: Pinnacle for game markets, consensus for props
        if not is_prop and lookup_key in pin_lookup:
            bench_row = pin_lookup[lookup_key]
            bench_dec = bench_row["odds_decimal"]
            bench_label = "pinnacle"

            # No-vig fair prob from Pinnacle two-way market
            fair_prob = implied_probability(bench_dec)
            market_group_key = (mtype, point, player_name)
            group = pin_by_market.get(market_group_key, [])
            if len(group) == 2:
                sides = sorted(group, key=lambda r: r["selection"])
                prob_a, prob_b = no_vig_probability(
                    sides[0]["odds_decimal"], sides[1]["odds_decimal"]
                )
                fair_prob = prob_a if selection == sides[0]["selection"] else prob_b

        elif lookup_key in consensus_lookup:
            bench_row = consensus_lookup[lookup_key]
            bench_dec = bench_row["odds_decimal"]
            bench_label = "consensus"

            # No-vig fair prob from consensus two-way market
            fair_prob = implied_probability(bench_dec)
            market_group_key = (mtype, point, player_name)
            group = consensus_by_market.get(market_group_key, [])
            if len(group) == 2:
                sides = sorted(group, key=lambda r: r["selection"])
                prob_a, prob_b = no_vig_probability(
                    sides[0]["odds_decimal"], sides[1]["odds_decimal"]
                )
                fair_prob = prob_a if selection == sides[0]["selection"] else prob_b
        else:
            continue

        ev_pct = calculate_ev(book_dec, fair_prob)
        edge_pct = calculate_edge(book_dec, bench_dec)

        if ev_pct >= MIN_EV_THRESHOLD:
            opp = {
                "game_id": game_id,
                "sportsbook": book_key,
                "market_type": mtype,
                "selection": selection,
                "point": point,
                "player_name": player_name,
                "book_odds": book_dec,
                "pinnacle_odds": bench_dec,
                "benchmark": bench_label,
                "ev_percent": round(ev_pct, 2),
                "edge_percent": round(edge_pct, 2),
                "fair_probability": round(fair_prob, 4),
            }
            opportunities.append(opp)

            insert_ev_opportunity(
                game_id=game_id,
                sportsbook=book_key,
                market_type=mtype,
                selection=selection,
                book_odds=book_dec,
                pinnacle_odds=bench_dec,
                ev_percent=round(ev_pct, 2),
                edge_percent=round(edge_pct, 2),
                point=point,
                player_name=player_name,
                benchmark=bench_label,
            )

    return opportunities


def scan_all_upcoming() -> list[dict[str, Any]]:
    """
    Scan every upcoming game and return all positive-EV opportunities.

    Returns
    -------
    list[dict]
        Combined list of opportunities across all upcoming games.
    """
    games = get_upcoming_games()
    all_opps: list[dict[str, Any]] = []
    for game in games:
        opps = scan_ev_opportunities_for_game(game["game_id"])
        all_opps.extend(opps)
    logger.info("Found %d positive-EV opportunities across %d games.",
                len(all_opps), len(games))
    return all_opps


# ---------------------------------------------------------------------------
# Bet settlement helpers
# ---------------------------------------------------------------------------


def _determine_outcome(
    bet: dict[str, Any],
) -> tuple[str, float]:
    """
    Determine outcome (win/loss/push) and profit/loss for a settled bet.

    Returns
    -------
    tuple[str, float]
        (outcome, profit_loss) where profit_loss is positive on a win.
    """
    market = bet["market_type"]
    selection = bet["selection"]
    home_score = bet["home_score"]
    away_score = bet["away_score"]
    odds = bet["odds_decimal"]
    stake = bet["stake"]
    point = bet.get("point")

    if home_score is None or away_score is None:
        return "pending", 0.0

    # Player props cannot be auto-settled from box scores
    if market in PROP_MARKETS:
        return "pending", 0.0

    home_team = bet["home_team"]
    away_team = bet["away_team"]

    if market == "h2h":
        # Moneyline
        if home_score > away_score:
            winner = home_team
        elif away_score > home_score:
            winner = away_team
        else:
            return "push", 0.0

        if selection == winner:
            return "win", stake * (odds - 1)
        return "loss", -stake

    elif market == "spreads":
        # Selection is the team; point is the spread for that team
        if selection == home_team:
            adjusted = home_score + (point or 0)
            opponent = away_score
        else:
            adjusted = away_score + (point or 0)
            opponent = home_score

        if adjusted > opponent:
            return "win", stake * (odds - 1)
        elif adjusted == opponent:
            return "push", 0.0
        return "loss", -stake

    elif market == "totals":
        total = home_score + away_score
        if point is None:
            return "pending", 0.0
        if selection == "Over":
            if total > point:
                return "win", stake * (odds - 1)
            elif total == point:
                return "push", 0.0
            return "loss", -stake
        else:  # Under
            if total < point:
                return "win", stake * (odds - 1)
            elif total == point:
                return "push", 0.0
            return "loss", -stake

    return "pending", 0.0


def settle_pending_bets() -> list[dict[str, Any]]:
    """
    Check all pending bets against completed game results.
    Settle each one, computing CLV from Pinnacle closing odds.

    Returns
    -------
    list[dict]
        List of dicts describing each settled bet.
    """
    pending = get_pending_bets()
    settled: list[dict[str, Any]] = []

    for bet in pending:
        if bet["game_status"] != "completed":
            continue

        outcome, pnl = _determine_outcome(bet)
        if outcome == "pending":
            continue

        # CLV: compare placed odds to Pinnacle closing odds
        closing = get_closing_pinnacle_odds(bet["game_id"])
        closing_odds = None
        clv = None
        for cl in closing:
            if (cl["market_type"] == bet["market_type"]
                    and cl["selection"] == bet["selection"]
                    and cl.get("point") == bet.get("point")
                    and cl.get("player_name") == bet.get("player_name")):
                closing_odds = cl["odds_decimal"]
                clv = calculate_clv(bet["odds_decimal"], closing_odds)
                break

        settle_bet(
            bet_id=bet["id"],
            outcome=outcome,
            profit_loss=round(pnl, 2),
            closing_odds=closing_odds,
            clv=round(clv, 2) if clv is not None else None,
        )

        settled.append({
            "bet_id": bet["id"],
            "outcome": outcome,
            "profit_loss": round(pnl, 2),
            "closing_odds": closing_odds,
            "clv": round(clv, 2) if clv is not None else None,
        })

    if settled:
        logger.info("Settled %d bets.", len(settled))
    return settled


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Quick demo of the math
    print("=== EV Calculation Demo ===")
    fair_p = 0.52
    book = 2.10
    ev = calculate_ev(book, fair_p)
    print(f"Book odds: {book}, Fair prob: {fair_p}")
    print(f"EV: {ev:.2f}%")

    edge = calculate_edge(2.10, 2.00)
    print(f"Edge vs Pinnacle: {edge:.2f}%")

    clv = calculate_clv(2.10, 1.95)
    print(f"CLV: {clv:.2f}%")

    print("\n=== Scanning upcoming games ===")
    opps = scan_all_upcoming()
    for opp in opps:
        print(
            f"  {opp['sportsbook']:20s} | {opp['selection']:25s} | "
            f"EV {opp['ev_percent']:+.2f}% | Edge {opp['edge_percent']:+.2f}%"
        )

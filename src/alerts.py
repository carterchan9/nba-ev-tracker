"""
Alert module for the NBA EV Tracker.

Generates notifications for:
- New positive-EV opportunities
- Significant line movements
- Bet settlement outcomes

Alerts are printed to the console and logged.  The interface is designed
to be extended to email, Slack, or push-notification backends.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert backend protocol — swap in email / Slack / etc.
# ---------------------------------------------------------------------------


class AlertBackend(Protocol):
    """Interface for pluggable alert destinations."""

    def send(self, title: str, body: str, level: str) -> None: ...


class ConsoleAlertBackend:
    """Default backend that prints to stdout and logs."""

    def send(self, title: str, body: str, level: str = "INFO") -> None:
        """Print and log the alert."""
        prefix = {"INFO": "ℹ️ ", "WARNING": "⚠️ ", "SUCCESS": "✅ "}.get(level, "")
        message = f"{prefix}[{title}] {body}"
        print(message)
        logger.info(message)


# Module-level default backend
_backend: AlertBackend = ConsoleAlertBackend()


def set_alert_backend(backend: AlertBackend) -> None:
    """Replace the default console backend with a custom one."""
    global _backend
    _backend = backend


# ---------------------------------------------------------------------------
# Alert generators
# ---------------------------------------------------------------------------


def alert_new_ev_opportunity(opp: dict[str, Any]) -> None:
    """
    Fire an alert for a newly discovered positive-EV bet.

    Parameters
    ----------
    opp : dict
        Opportunity dict with keys: sportsbook, selection, market_type,
        book_odds, ev_percent, edge_percent, game_id.
    """
    title = "New +EV Opportunity"
    player = opp.get("player_name")
    label = f"{player} " if player else ""
    body = (
        f"{opp['sportsbook'].upper()} | {label}{opp['selection']} "
        f"({opp['market_type']}) @ {opp['book_odds']:.3f}  —  "
        f"EV {opp['ev_percent']:+.2f}%  Edge {opp['edge_percent']:+.2f}%"
    )
    _backend.send(title, body, "SUCCESS")


def alert_line_movement(movement: dict[str, Any], game_label: str = "") -> None:
    """
    Fire an alert for a significant line movement.

    Parameters
    ----------
    movement : dict
        Dict with keys: sportsbook, selection, market_type,
        opening_odds, current_odds, change_pct.
    game_label : str
        Human-readable game description.
    """
    title = "Line Movement"
    direction = "up" if movement["change_pct"] > 0 else "down"
    body = (
        f"{game_label} | {movement['sportsbook'].upper()} | "
        f"{movement['selection']} ({movement['market_type']}) "
        f"moved {direction} {abs(movement['change_pct']):.1f}%  "
        f"({movement['opening_odds']:.3f} → {movement['current_odds']:.3f})"
    )
    _backend.send(title, body, "WARNING")


def alert_bet_settled(result: dict[str, Any]) -> None:
    """
    Fire an alert when a user bet is settled.

    Parameters
    ----------
    result : dict
        Dict with keys: bet_id, outcome, profit_loss, clv.
    """
    title = "Bet Settled"
    outcome = result["outcome"].upper()
    pnl = result["profit_loss"]
    sign = "+" if pnl >= 0 else ""
    clv_str = f"  CLV {result['clv']:+.2f}%" if result.get("clv") is not None else ""
    body = f"Bet #{result['bet_id']} → {outcome}  {sign}${pnl:.2f}{clv_str}"
    level = "SUCCESS" if pnl >= 0 else "INFO"
    _backend.send(title, body, level)


def alert_batch_ev_opportunities(opportunities: list[dict[str, Any]]) -> None:
    """Fire individual alerts for a list of new +EV opportunities."""
    for opp in opportunities:
        alert_new_ev_opportunity(opp)


def alert_batch_settlements(settlements: list[dict[str, Any]]) -> None:
    """Fire individual alerts for a list of settled bets."""
    for result in settlements:
        alert_bet_settled(result)

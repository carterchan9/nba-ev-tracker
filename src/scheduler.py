"""
Scheduler module for the NBA EV Tracker.

Uses APScheduler to run periodic jobs:
1. Pull latest odds & scores from The Odds API.
2. Scan for positive-EV opportunities.
3. Settle completed bets and update bankroll.
4. Detect significant line movements and fire alerts.

Start the scheduler with ``start_scheduler()`` or run this file directly.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.alerts import (
    alert_batch_ev_opportunities,
    alert_batch_settlements,
    alert_line_movement,
)
from src.config import LINE_MOVEMENT_THRESHOLD, POLL_INTERVAL_MINUTES
from src.data_fetching import pull_and_store_latest
from src.database import get_upcoming_games
from src.ev_calculation import scan_all_upcoming, settle_pending_bets
from src.strategy_analysis import (
    detect_significant_movements,
    update_bankroll_snapshot,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ---------------------------------------------------------------------------
# Job functions
# ---------------------------------------------------------------------------


def job_pull_odds() -> None:
    """Scheduled job: pull latest odds and scores."""
    try:
        summary = pull_and_store_latest()
        logger.info("Scheduled pull complete — %s", summary)
    except Exception:
        logger.exception("Error in scheduled odds pull.")


def job_scan_ev() -> None:
    """Scheduled job: scan for +EV opportunities and alert."""
    try:
        opps = scan_all_upcoming()
        if opps:
            alert_batch_ev_opportunities(opps)
    except Exception:
        logger.exception("Error in EV scan job.")


def job_settle_and_update() -> None:
    """Scheduled job: settle bets, update bankroll, alert on settlements."""
    try:
        settlements = settle_pending_bets()
        if settlements:
            alert_batch_settlements(settlements)
            update_bankroll_snapshot()
    except Exception:
        logger.exception("Error in settle/update job.")


def job_line_movement_alerts() -> None:
    """Scheduled job: detect big line moves and alert."""
    try:
        games = get_upcoming_games()
        for game in games:
            movements = detect_significant_movements(
                game["game_id"], threshold_pct=LINE_MOVEMENT_THRESHOLD
            )
            label = f"{game['away_team']} @ {game['home_team']}"
            for mv in movements:
                alert_line_movement(mv, game_label=label)
    except Exception:
        logger.exception("Error in line movement job.")


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------


def start_scheduler() -> BackgroundScheduler:
    """
    Create and start the background scheduler with all recurring jobs.

    Returns the scheduler instance (call ``.shutdown()`` to stop).
    """
    global _scheduler

    _scheduler = BackgroundScheduler()
    interval = POLL_INTERVAL_MINUTES

    _scheduler.add_job(
        job_pull_odds,
        trigger=IntervalTrigger(minutes=interval),
        id="pull_odds",
        name="Pull odds & scores",
        replace_existing=True,
    )

    # Scan EV 1 minute after each pull
    _scheduler.add_job(
        job_scan_ev,
        trigger=IntervalTrigger(minutes=interval),
        id="scan_ev",
        name="Scan EV opportunities",
        replace_existing=True,
    )

    # Settle bets every 15 minutes
    _scheduler.add_job(
        job_settle_and_update,
        trigger=IntervalTrigger(minutes=max(interval, 15)),
        id="settle_bets",
        name="Settle bets & update bankroll",
        replace_existing=True,
    )

    # Line movement checks at the same cadence as odds pulls
    _scheduler.add_job(
        job_line_movement_alerts,
        trigger=IntervalTrigger(minutes=interval),
        id="line_movements",
        name="Line movement alerts",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started — polling every %d min.", interval
    )
    return _scheduler


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)
    sched = start_scheduler()

    # Run an immediate pull on startup
    job_pull_odds()
    job_scan_ev()

    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_scheduler()
        print("Stopped.")

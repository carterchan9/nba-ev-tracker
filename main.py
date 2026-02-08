"""
NBA EV Tracker — main entry point.

Usage
-----
    # Initialise the database schema
    python main.py init

    # Pull latest odds + scores, scan EV, settle bets (one-shot)
    python main.py run-once

    # Start the background scheduler (runs continuously)
    python main.py scheduler

    # Launch the Streamlit dashboard
    python main.py dashboard

    # Record a manual bet
    python main.py place-bet --game <GAME_ID> --book draftkings \\
           --market h2h --selection "Boston Celtics" --odds 2.10 --stake 50
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time

from src.config import LOG_LEVEL


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_init(_args: argparse.Namespace) -> None:
    """Create / update the database schema."""
    from src.database import init_schema
    init_schema()
    print("Database schema initialised.")


def cmd_run_once(_args: argparse.Namespace) -> None:
    """One-shot: pull odds, scan EV, settle bets, update bankroll."""
    from src.alerts import alert_batch_ev_opportunities, alert_batch_settlements
    from src.data_fetching import pull_and_store_latest
    from src.ev_calculation import scan_all_upcoming, settle_pending_bets
    from src.strategy_analysis import update_bankroll_snapshot

    print("Pulling latest odds and scores …")
    summary = pull_and_store_latest()
    print(f"  Events fetched: {summary['events_fetched']}")
    print(f"  Sportsbook odds stored: {summary['sportsbook_odds_stored']}")
    print(f"  Pinnacle odds stored: {summary['pinnacle_odds_stored']}")
    print(f"  Games completed: {len(summary['games_completed'])}")

    print("\nScanning for +EV opportunities …")
    opps = scan_all_upcoming()
    print(f"  Found {len(opps)} opportunities.")
    alert_batch_ev_opportunities(opps)

    print("\nSettling pending bets …")
    settled = settle_pending_bets()
    print(f"  Settled {len(settled)} bets.")
    alert_batch_settlements(settled)

    if settled:
        stats = update_bankroll_snapshot()
        print(f"\nBankroll: ${stats['bankroll']:,.2f}  ROI: {stats['roi']:.2f}%")


def cmd_scheduler(_args: argparse.Namespace) -> None:
    """Start the background scheduler that polls continuously."""
    from src.scheduler import job_pull_odds, job_scan_ev, start_scheduler, stop_scheduler

    sched = start_scheduler()

    # Immediate pull on startup
    job_pull_odds()
    job_scan_ev()

    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_scheduler()
        print("Stopped.")


def cmd_dashboard(_args: argparse.Namespace) -> None:
    """Launch the Streamlit dashboard."""
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run",
         "src/visualization_dashboard.py"],
        check=True,
    )


def cmd_place_bet(args: argparse.Namespace) -> None:
    """Record a user bet from the CLI."""
    from src.database import insert_user_bet
    from src.ev_calculation import calculate_edge, calculate_ev, implied_probability
    from src.database import get_latest_pinnacle_odds

    # Try to look up Pinnacle odds for EV/edge
    ev = None
    edge = None
    pin_lines = get_latest_pinnacle_odds(args.game, market_type=args.market)
    for pl in pin_lines:
        if pl["selection"] == args.selection and pl.get("point") == args.point:
            fair_p = implied_probability(pl["odds_decimal"])
            ev = round(calculate_ev(args.odds, fair_p), 2)
            edge = round(calculate_edge(args.odds, pl["odds_decimal"]), 2)
            break

    bet_id = insert_user_bet(
        game_id=args.game,
        sportsbook=args.book,
        market_type=args.market,
        selection=args.selection,
        odds_decimal=args.odds,
        stake=args.stake,
        ev_at_placement=ev,
        edge_at_placement=edge,
        point=args.point,
    )
    print(f"Bet #{bet_id} recorded.")
    if ev is not None:
        print(f"  EV at placement: {ev:+.2f}%")
        print(f"  Edge vs Pinnacle: {edge:+.2f}%")


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(
        description="NBA EV Tracker — betting EV analysis tool"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialise the database schema")
    sub.add_parser("run-once", help="One-shot pull + scan + settle")
    sub.add_parser("scheduler", help="Start background scheduler")
    sub.add_parser("dashboard", help="Launch Streamlit dashboard")

    bet_parser = sub.add_parser("place-bet", help="Record a bet")
    bet_parser.add_argument("--game", required=True, help="Game ID")
    bet_parser.add_argument("--book", required=True, help="Sportsbook key")
    bet_parser.add_argument("--market", required=True,
                            choices=["h2h", "spreads", "totals"])
    bet_parser.add_argument("--selection", required=True,
                            help="Team name or Over/Under")
    bet_parser.add_argument("--odds", required=True, type=float,
                            help="Decimal odds")
    bet_parser.add_argument("--stake", required=True, type=float,
                            help="Stake amount ($)")
    bet_parser.add_argument("--point", type=float, default=None,
                            help="Spread / total line (for spreads or totals)")

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "run-once": cmd_run_once,
        "scheduler": cmd_scheduler,
        "dashboard": cmd_dashboard,
        "place-bet": cmd_place_bet,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

# NBA EV Tracker

A positive Expected Value (EV) betting tool for the NBA. Compares sportsbook odds against Pinnacle's sharp line to surface +EV opportunities, tracks your bets, and provides analytics on your betting performance.

## Features

- **Live odds pulling** from Bet365, FanDuel, DraftKings, BetMGM, SportsInteraction, Bet99, Betway, Caesars (William Hill US), and Proline via [The Odds API](https://the-odds-api.com/).
- **Pinnacle benchmark** — uses Pinnacle's no-vig line as the "true" probability.
- **EV & Edge calculation** — flags bets where sportsbook odds exceed fair value.
- **Closing Line Value (CLV)** — measures how often you beat the closing line.
- **Line movement tracking** — time-series odds history with movement alerts.
- **Bet tracking** — record bets, auto-settle from game results, track P&L.
- **Analytics dashboard** — Streamlit UI with live EV table, line charts, scatter plots, heatmaps, and cumulative ROI.
- **Scheduled polling** — APScheduler pulls odds on a configurable interval.
- **Extensible** — modular design ready for multi-league, additional bet types, or alternative alert backends (Slack, email, etc.).

## Project Structure

```
bettingTool/
├── main.py                         # CLI entry point
├── requirements.txt
├── .env                            # Configuration (copy from .env.example)
├── README.md                       # This file (setup & usage)
├── sql/
│   └── schema.sql                  # PostgreSQL schema
├── src/
│   ├── config.py                   # Central configuration
│   ├── data_fetching.py            # Odds API + scores
│   ├── ev_calculation.py           # EV, edge, CLV, scanner
│   ├── database.py                 # PostgreSQL CRUD
│   ├── strategy_analysis.py        # ROI, correlation, line movement
│   ├── visualization_dashboard.py  # Streamlit dashboard
│   ├── scheduler.py                # APScheduler jobs
│   └── alerts.py                   # Alert system
└── info/                           # 📚 Project documentation
    ├── INDEX.md                    # Documentation guide (start here)
    ├── STATUS.md                   # Current project status
    ├── SESSIONS.md                 # Development session history
    ├── OUTLINE.md                  # Architecture overview
    └── NOTES.md                    # Technical details & gotchas
```

## 📚 Documentation

All project documentation is in the `info/` directory:

- **Start here:** [`info/INDEX.md`](info/INDEX.md) — Guide to the documentation
- **Current status:** [`info/STATUS.md`](info/STATUS.md) — What's working, what's not, action items
- **Session history:** [`info/SESSIONS.md`](info/SESSIONS.md) — Running log of development sessions
- **Architecture:** [`info/OUTLINE.md`](info/OUTLINE.md) — High-level overview
- **Technical notes:** [`info/NOTES.md`](info/NOTES.md) — Implementation details and gotchas

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** running locally (or remote — update `.env`)
- **The Odds API key** — free tier gives 500 requests/month: https://the-odds-api.com/

## Setup

```bash
# 1. Clone / navigate to the project
cd bettingTool

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment — create a .env file with:
#    ODDS_API_KEY, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
#    See info/STATUS.md or info/NOTES.md for all config values

# 5. Create the database
createdb nba_ev_tracker   # or via psql: CREATE DATABASE nba_ev_tracker;

# 6. Initialise the schema
python main.py init
```

## Usage

### One-shot pull + scan

```bash
python main.py run-once
```

Fetches the latest odds, scans for +EV opportunities, settles any completed bets, and prints results.

### Start the scheduler

```bash
python main.py scheduler
```

Runs in the foreground, pulling odds every N minutes (default 5, configurable via `POLL_INTERVAL_MINUTES`). Alerts print to the console.

### Launch the dashboard

```bash
python main.py dashboard
# or directly:
streamlit run src/visualization_dashboard.py
```

Opens a browser with four pages:

| Page | What it shows |
|------|---------------|
| **Live EV Opportunities** | Table of current +EV bets, EV distribution histogram |
| **Line Movement** | Per-game odds time-series by sportsbook |
| **Bankroll & P/L** | KPIs, cumulative equity curve, bankroll history |
| **Performance Analytics** | ROI breakdown, EV-vs-actual scatter, CLV analysis, profit heatmap |

### Record a bet

```bash
python main.py place-bet \
  --game abc123 \
  --book draftkings \
  --market h2h \
  --selection "Boston Celtics" \
  --odds 2.10 \
  --stake 50
```

The tool automatically computes EV and edge at the time of placement using the current Pinnacle line.

## Configuration

All settings live in `.env` (loaded by `src/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ODDS_API_KEY` | — | Your The Odds API key |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `nba_ev_tracker` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | — | Database password |
| `POLL_INTERVAL_MINUTES` | `5` | How often to pull odds |
| `MIN_EV_THRESHOLD` | `1.0` | Minimum EV% to flag as +EV |
| `LINE_MOVEMENT_THRESHOLD` | `3.0` | % change to trigger a line-movement alert |
| `STARTING_BANKROLL` | `1000.00` | Initial bankroll |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Extending

- **Multi-league:** Change `SPORT_KEY` in config or extend to accept multiple sport keys.
- **Additional markets:** Add to `MARKETS` list (e.g. player props when supported by the API).
- **Alert backends:** Implement the `AlertBackend` protocol in `src/alerts.py` and call `set_alert_backend()`.
- **Kelly criterion sizing:** Add a function in `ev_calculation.py` that returns optimal stake given edge and bankroll.

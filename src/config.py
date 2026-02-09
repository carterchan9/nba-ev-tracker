"""
Centralized configuration for the NBA EV Tracker.

Loads settings from environment variables / .env file and exposes them
as module-level constants so every other module can simply
``from src.config import …``.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# The Odds API
# ---------------------------------------------------------------------------
ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE_URL: str = "https://api.the-odds-api.com/v4"
SPORT_KEY: str = "basketball_nba"

# API regions — pull from all regions to get comprehensive coverage
# ca: Canada (Ontario), us/us2: USA, uk/eu/au: International (Pinnacle)
ODDS_API_REGIONS: str = "ca,us,us2,uk,eu,au"

# Preferred region for display (user can override in .env)
PREFERRED_REGION: str = os.getenv("PREFERRED_REGION", "ca")

# Sportsbook keys as used by The Odds API
SPORTSBOOKS: list[str] = [
    "bet365",
    "fanduel",
    "draftkings",
    "betmgm",
    "betway",
    "williamhill_us",   # Caesars
    "sportsinteraction",
    "bet99",
    "proline",
    "espnbet",
    "hardrockbet",
    "fliff",
    "betrivers",
    "bovada",
]

PINNACLE_KEY: str = "pinnacle"

# All bookmakers we request in a single API call
ALL_BOOKMAKERS: list[str] = SPORTSBOOKS + [PINNACLE_KEY]

# Standard game markets
GAME_MARKETS: list[str] = ["h2h", "spreads", "totals"]

# Player prop markets
PROP_MARKETS: list[str] = [
    "player_points",
    "player_rebounds",
    "player_assists",
    "player_threes",
    "player_blocks",
    "player_steals",
    "player_points_rebounds_assists",
    "player_points_rebounds",
    "player_points_assists",
    "player_rebounds_assists",
]

# All markets to fetch
MARKETS: list[str] = GAME_MARKETS + PROP_MARKETS

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
DB_NAME: str = os.getenv("DB_NAME", "nba_ev_tracker")
DB_USER: str = os.getenv("DB_USER", "postgres")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

DATABASE_URL: str = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------------------------------------------------------------------------
# Scheduler / polling
# ---------------------------------------------------------------------------
POLL_INTERVAL_MINUTES: int = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))

# ---------------------------------------------------------------------------
# EV / alert thresholds
# ---------------------------------------------------------------------------
MIN_EV_THRESHOLD: float = float(os.getenv("MIN_EV_THRESHOLD", "1.0"))
LINE_MOVEMENT_THRESHOLD: float = float(os.getenv("LINE_MOVEMENT_THRESHOLD", "3.0"))

# ---------------------------------------------------------------------------
# Bankroll
# ---------------------------------------------------------------------------
STARTING_BANKROLL: float = float(os.getenv("STARTING_BANKROLL", "1000.00"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

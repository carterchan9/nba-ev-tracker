-- ============================================================
-- NBA EV Tracker — PostgreSQL Schema
-- ============================================================

-- Games table — one row per NBA game
CREATE TABLE IF NOT EXISTS games (
    game_id         TEXT PRIMARY KEY,           -- external id from the odds API
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    commence_time   TIMESTAMPTZ NOT NULL,
    home_score      INTEGER,
    away_score      INTEGER,
    status          TEXT NOT NULL DEFAULT 'upcoming'  -- upcoming | live | completed
);

CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
CREATE INDEX IF NOT EXISTS idx_games_commence ON games(commence_time);

-- Odds snapshots — every poll stores one row per book / market / selection
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(game_id),
    sportsbook      TEXT NOT NULL,
    market_type     TEXT NOT NULL,              -- h2h | spreads | totals | player_points | etc.
    selection       TEXT NOT NULL,              -- team name, Over/Under, etc.
    point           REAL,                       -- spread / total / prop line (NULL for h2h)
    player_name     TEXT,                       -- player name for props (NULL for game markets)
    odds_decimal    REAL NOT NULL,
    implied_prob    REAL NOT NULL,
    snapshot_time   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_odds_game ON odds_snapshots(game_id);
CREATE INDEX IF NOT EXISTS idx_odds_book ON odds_snapshots(sportsbook);
CREATE INDEX IF NOT EXISTS idx_odds_time ON odds_snapshots(snapshot_time);

-- Pinnacle odds stored separately for easy closing-line queries
CREATE TABLE IF NOT EXISTS pinnacle_odds (
    id              BIGSERIAL PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(game_id),
    market_type     TEXT NOT NULL,
    selection       TEXT NOT NULL,
    point           REAL,
    player_name     TEXT,                       -- player name for props (NULL for game markets)
    odds_decimal    REAL NOT NULL,
    implied_prob    REAL NOT NULL,
    snapshot_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_closing      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_pin_game ON pinnacle_odds(game_id);
CREATE INDEX IF NOT EXISTS idx_pin_closing ON pinnacle_odds(is_closing);

-- Positive-EV opportunities found by the scanner
CREATE TABLE IF NOT EXISTS ev_opportunities (
    id              BIGSERIAL PRIMARY KEY,
    game_id         TEXT NOT NULL REFERENCES games(game_id),
    sportsbook      TEXT NOT NULL,
    market_type     TEXT NOT NULL,
    selection       TEXT NOT NULL,
    point           REAL,
    player_name     TEXT,                       -- player name for props (NULL for game markets)
    book_odds       REAL NOT NULL,
    pinnacle_odds   REAL NOT NULL,
    ev_percent      REAL NOT NULL,
    edge_percent    REAL NOT NULL,
    benchmark       TEXT NOT NULL DEFAULT 'pinnacle',  -- pinnacle | consensus
    found_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ev_game ON ev_opportunities(game_id);
CREATE INDEX IF NOT EXISTS idx_ev_found ON ev_opportunities(found_at);

-- User-placed bets
CREATE TABLE IF NOT EXISTS user_bets (
    id                  BIGSERIAL PRIMARY KEY,
    game_id             TEXT NOT NULL REFERENCES games(game_id),
    sportsbook          TEXT NOT NULL,
    market_type         TEXT NOT NULL,
    selection           TEXT NOT NULL,
    point               REAL,
    player_name         TEXT,                       -- player name for props (NULL for game markets)
    odds_decimal        REAL NOT NULL,
    stake               REAL NOT NULL,
    ev_at_placement     REAL,
    edge_at_placement   REAL,
    placed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    outcome             TEXT,                   -- win | loss | push | NULL (pending)
    profit_loss         REAL,
    closing_odds        REAL,
    clv                 REAL                    -- closing line value
);

CREATE INDEX IF NOT EXISTS idx_bets_game ON user_bets(game_id);
CREATE INDEX IF NOT EXISTS idx_bets_outcome ON user_bets(outcome);

-- Bankroll history — one row per snapshot (after each bet settles or manual update)
CREATE TABLE IF NOT EXISTS bankroll_history (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bankroll            REAL NOT NULL,
    cumulative_profit   REAL NOT NULL DEFAULT 0,
    total_staked        REAL NOT NULL DEFAULT 0,
    roi                 REAL NOT NULL DEFAULT 0,
    win_rate            REAL NOT NULL DEFAULT 0,
    total_bets          INTEGER NOT NULL DEFAULT 0
);

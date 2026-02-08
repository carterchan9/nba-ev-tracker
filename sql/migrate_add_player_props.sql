-- Migration: add player_name column for player props support
ALTER TABLE odds_snapshots ADD COLUMN IF NOT EXISTS player_name TEXT;
ALTER TABLE pinnacle_odds ADD COLUMN IF NOT EXISTS player_name TEXT;
ALTER TABLE ev_opportunities ADD COLUMN IF NOT EXISTS player_name TEXT;
ALTER TABLE user_bets ADD COLUMN IF NOT EXISTS player_name TEXT;

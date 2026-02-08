# NBA EV Tracker — Project Outline

## Overview
A positive Expected Value (EV) betting tool for the NBA. Compares sportsbook odds against Pinnacle's sharp line (game markets) or consensus median (player props fallback) to surface +EV opportunities, tracks bets, and provides analytics on betting performance.

## Sportsbooks (14 configured)
### Returning NBA data
FanDuel, DraftKings, BetMGM, Betway, ESPN BET, Hard Rock Bet, Fliff, BetRivers, Bovada

### Configured but not returning data
Bet365 (not available via The Odds API for NBA), SportsInteraction, Bet99, Caesars (williamhill_us), Proline

## Benchmarks
- **Game markets:** Pinnacle — used as the sharp/efficient market to derive "true" probabilities via no-vig calculation
- **Player props:** Pinnacle (available with expanded regions `us,us2,uk,eu,au`); consensus line (median across 3+ books) as fallback when Pinnacle line is missing

## Markets
### Game Markets (bulk endpoint — 1 API call each)
- **h2h** — Moneyline
- **spreads** — Point spreads
- **totals** — Over/Under

### Player Props (per-event endpoint — each market counts as 1 API request)
- **player_points** — Points Over/Under
- **player_rebounds** — Rebounds Over/Under
- **player_assists** — Assists Over/Under
- **player_threes** — Three-Pointers Over/Under
- **player_blocks** — Blocks Over/Under
- **player_steals** — Steals Over/Under
- **player_points_rebounds_assists** — PRA Combo Over/Under
- **player_points_rebounds** — Points+Rebounds Over/Under
- **player_points_assists** — Points+Assists Over/Under
- **player_rebounds_assists** — Rebounds+Assists Over/Under

### Removed Markets (not worth the API cost)
- ~~player_double_double~~ — removed
- ~~player_triple_double~~ — removed
- ~~player_turnovers~~ — API doesn't return data
- ~~player_blocks_steals~~ — API doesn't return data

## Core Features
1. Pull NBA betting lines from all sportsbooks + Pinnacle via The Odds API (v4)
2. Normalize odds to decimal format and calculate implied probabilities
3. Calculate Expected Value (EV) and Edge vs benchmark (Pinnacle or consensus)
4. Display both decimal and American odds on dashboard
5. Show benchmark source (Pinnacle or Consensus) for each opportunity
6. Track Closing Line Value (CLV) — how placed odds compare to Pinnacle's closing line
7. Track line movement over time
8. Store odds snapshots and historical bets in PostgreSQL
9. Track user bets with stake, EV, edge, outcome, and profit/loss
10. Update cumulative stats: ROI, win rate, bankroll
11. Schedule automatic data pulls (every 15 min)
12. Generate alerts for new +EV bets, significant line changes, and finalized outcomes
13. Visualize live EV opportunities with last-refresh timestamp
14. Historical opportunities archive with date range and min EV% filters
15. Game detail view — drill into any game to see all available markets from every sportsbook

## Modules
| File | Responsibility |
|------|---------------|
| `src/config.py` | Central configuration loaded from `.env`; 14 sportsbooks; 10 prop markets; `ODDS_API_REGIONS` |
| `src/data_fetching.py` | Fetch odds & scores from The Odds API (bulk for games, per-event for props); uses `ODDS_API_REGIONS` |
| `src/ev_calculation.py` | EV, edge, CLV math + Pinnacle/consensus opportunity scanner; stores benchmark label |
| `src/database.py` | PostgreSQL connection pool, CRUD, game detail query, historical query helpers |
| `src/strategy_analysis.py` | ROI, correlation, line movement, bankroll analysis |
| `src/visualization_dashboard.py` | Streamlit + Plotly dashboard (5 pages); `sys.path` fix; game detail view |
| `src/scheduler.py` | APScheduler background jobs |
| `src/alerts.py` | Pluggable alert system |
| `main.py` | CLI entry point |

## Database Tables
- `games` — NBA games with scores and status
- `odds_snapshots` — Sportsbook odds at each poll (includes `player_name` for props)
- `pinnacle_odds` — Pinnacle odds (separate for closing-line queries, includes `player_name`)
- `ev_opportunities` — Flagged +EV bets (includes `player_name`, `benchmark` column)
- `user_bets` — User-placed bets with outcomes (includes `player_name`)
- `bankroll_history` — Bankroll snapshots over time

## Dashboard Pages
1. **Live EV Opportunities** — last-refresh timestamp, current scan results only, table with decimal + American odds + benchmark source, EV distribution histogram, game detail view with all markets
2. **Historical Opportunities** — date range picker, adjustable min EV% (default 2%), deduplicated table, EV distribution chart, opportunities-by-sportsbook breakdown
3. **Line Movement** — per-game odds time-series by sportsbook, market type filter
4. **Bankroll & P/L** — KPIs (bankroll, profit, ROI, win rate, total bets), equity curve, bankroll history
5. **Performance Analytics** — ROI by sportsbook/market, EV-vs-actual scatter, CLV analysis, profit heatmap

## EV Math
- **EV%** = `(fair_prob * (book_odds - 1) - (1 - fair_prob)) * 100`
- **Edge%** = `((book_odds / benchmark_odds) - 1) * 100`
- **CLV%** = `((placed_odds / closing_odds) - 1) * 100`
- **No-vig probability:** remove overround from two-way market: `raw_prob / (raw_prob_a + raw_prob_b)`

## API Cost
- ~120-140 API requests per scan (each prop market per event = 1 request)
- ~2-3 scans/day sustainable on 500/mo free tier
- Game markets: 3 requests (1 per market)
- Props: ~10 events × 10 markets = ~100 requests
- Events list + scores: 2 requests

## Future Extensions
- Multi-league support (change/add `SPORT_KEY`)
- Kelly criterion bet sizing
- Alternative alert backends (Slack, email, push)
- Bet365 data via alternative API (SportsGameOdds free tier)

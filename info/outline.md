# NBA EV Tracker — Project Outline

## Overview
A positive Expected Value (EV) betting tool for the NBA. Compares sportsbook odds against Pinnacle's sharp line to surface +EV opportunities, tracks bets, and provides analytics on betting performance.

**Status:** Feature-complete with regional support in progress. API quota: 1/500 requests remaining.

## Sportsbooks (14 configured)
### Returning NBA data
FanDuel, DraftKings, BetMGM, Betway, ESPN BET, Hard Rock Bet, Fliff, BetRivers, Bovada

### Configured but not returning data
Bet365 (not available via The Odds API for NBA), SportsInteraction, Bet99, Caesars (williamhill_us), Proline

## Benchmarks
- **All markets (game + props):** Pinnacle first if available (available with expanded regions `ca,us,us2,uk,eu,au` — ⚠️ "ca" not yet verified); consensus line (median across 3+ books) as fallback when Pinnacle line is missing
- Uses no-vig calculation to derive "true" probabilities from two-way markets
- Comparisons ONLY match same point totals (e.g., 20.5 vs 20.5) — verified with `pinnacle_point` column

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
2. Multi-region support (ca, us, us2, uk, eu, au) with preferred region filtering
3. Normalize odds to decimal format and calculate implied probabilities
4. Calculate Expected Value (EV) and Edge vs benchmark (Pinnacle or consensus)
5. Display both decimal and American odds on dashboard
6. Show benchmark source (Pinnacle or Consensus) + point totals for transparency
7. **Best book display:** Show only highest EV book per market with count of positive EV books
8. **Click-to-expand:** View all competing book prices for any market
9. **Separate live/historical tables:** Live shows current scan only, historical retains all data
10. Track Closing Line Value (CLV) — how placed odds compare to Pinnacle's closing line
11. Track line movement over time
12. Store odds snapshots and historical bets in PostgreSQL with region tracking
13. Track user bets with stake, EV, edge, outcome, and profit/loss
14. Update cumulative stats: ROI, win rate, bankroll
15. Schedule automatic data pulls (every 15 min)
16. Generate alerts for new +EV bets, significant line changes, and finalized outcomes
17. Visualize live EV opportunities with last-refresh timestamp
18. Historical opportunities archive with date range and min EV% filters
19. Game detail view — drill into any game to see all available markets from every sportsbook

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
- `odds_snapshots` — Sportsbook odds at each poll (includes `player_name`, `region`)
- `pinnacle_odds` — Pinnacle odds (separate for closing-line queries, includes `player_name`, `region`)
- `ev_opportunities` — Full historical +EV bets (includes `player_name`, `benchmark`, `pinnacle_point`)
- `ev_opportunities_live` — Current scan only, cleared on each refresh (same schema as above)
- `user_bets` — User-placed bets with outcomes (includes `player_name`)
- `bankroll_history` — Bankroll snapshots over time

## Dashboard Pages
1. **Live EV Opportunities** — Shows only current scan (from `ev_opportunities_live`):
   - Best book per market with `num_positive_ev_books` count
   - Point totals for transparency (sportsbook line + Pinnacle line)
   - Click-to-expand: select market to view all competing books
   - EV distribution histogram
   - Game detail view with all markets
2. **Historical Opportunities** — Full historical record (from `ev_opportunities`):
   - Date range picker, adjustable min EV% (default 2%)
   - Deduplicated table, EV distribution chart
   - Opportunities-by-sportsbook breakdown
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

## Known Issues & Next Steps

### Critical: Regional Support Verification Needed
⚠️ **Before next scan (when quota resets):**
1. Verify "ca" is a valid Odds API region code
2. Find correct sportsbook key for betriver.ca (might not be "betrivers")
3. Check if Canadian sportsbooks are even supported
4. Test with 1 request before running full scan

### Current Issue
- betriver.ca shows -107 odds live, but API returns +114 (2.14 decimal)
- Added "ca" to regions WITHOUT verification — might cause scan to fail or return wrong data
- Region filtering function created but not yet active (waiting for region data population)

## Future Extensions
- Multi-league support (change/add `SPORT_KEY`)
- Kelly criterion bet sizing
- Alternative alert backends (Slack, email, push)
- Bet365 data via alternative API (SportsGameOdds free tier)
- Activate region filtering once Canadian sportsbook keys verified

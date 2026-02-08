# Conversation Context & Project Notes

## Project Status
- **Phase:** Feature-complete, runtime-tested
- **Last updated:** 2026-02-07

## What's Been Done
1. Full project scaffolded with 8 source modules + CLI entry point
2. PostgreSQL schema defined in `sql/schema.sql` (6 tables)
3. The Odds API integration for odds + scores
4. EV/edge/CLV calculation engine with Pinnacle no-vig fair probability
5. Opportunity scanner comparing all sportsbook lines vs Pinnacle (game markets) or consensus (props)
6. Bet tracking with auto-settlement from game results (props require manual settlement)
7. Strategy analysis: ROI breakdowns, EV correlation, CLV, line movement
8. Streamlit dashboard with 5 pages (Live EV, Historical, Line Movement, Bankroll, Analytics)
9. APScheduler for background polling (15 min interval)
10. Alert system with pluggable backend (console default)
11. README with setup/usage docs
12. 10 NBA player prop markets supported (removed double_double, triple_double, turnovers, blocks_steals)
13. Pinnacle props available via expanded API regions (`us,us2,uk,eu,au`)
14. Consensus-line benchmark as fallback when Pinnacle line is missing
15. American odds displayed alongside decimal odds on dashboard
16. Dashboard deduplication to avoid repeat entries across scans
17. Live EV page shows last refresh timestamp, only shows latest scan batch
18. Historical Opportunities page with date range filter and adjustable min EV% threshold
19. Benchmark column (Pinnacle/Consensus) on EV tables
20. Commence time formatted as "February 7, 2026, 7:30pm"
21. Game detail view — select a game to see all available odds from every sportsbook
22. `sys.path` fix in dashboard for Streamlit direct execution

## Runtime Test Results (2026-02-07)
- `python main.py init` — schema created successfully
- `python main.py run-once` — with expanded regions: 13,082 sportsbook + 506 Pinnacle odds stored
- 289 +EV opportunities found across 12 games
- Pinnacle props now available (506 Pinnacle rows including props)
- Streamlit dashboard launched successfully on http://localhost:8501

## API Call Budget
- **~120-140 calls per scan cycle** (NOT 15 — each prop market counts as a separate API request):
  - 3 bulk game market calls (h2h, spreads, totals)
  - 1 events list call
  - ~10 per-event prop calls × 10 prop markets = **~100 API requests consumed**
  - 1 scores endpoint call
- **WARNING:** Each prop market in a per-event call counts as a separate API request
- **Rate limiting:** 1-second delay between per-event prop calls to avoid 429 errors
- Monthly quota tracked in API response headers (`x-requests-remaining`)
- At current usage: ~2-3 full scans per day with 500/mo free tier

## Sportsbook Availability (verified 2026-02-07)
- **Returning NBA data:** fanduel, draftkings, betmgm, betway, espnbet, hardrockbet, fliff, betrivers, bovada, pinnacle
- **NOT returning data:** bet365 (API only has `bet365_au` for AFL/NRL, paid tier only), sportsinteraction, bet99, williamhill_us, proline
- All 14 books are in the config (harmless if not available — API ignores unknown keys)
- Bet365 NBA odds are not available via The Odds API at any tier

## Bet365 Research (2026-02-07)
- **The Odds API:** Only `bet365_au` exists (paid, AFL/NRL only — no NBA)
- **365 Odds API:** Has bet365, starts at $5,000/mo
- **OpticOdds:** Enterprise pricing, contact form required
- **SportsGameOdds:** Free tier, has bet365, updates every 5 min, requires credit card

## Environment Notes
- PostgreSQL 17 installed at `/Library/PostgreSQL/17` (EnterpriseDB installer, NOT Homebrew)
- `psql` not on PATH — use `/Library/PostgreSQL/17/bin/psql` directly
- DB password: in `.env` (use `PGPASSWORD='...' /Library/PostgreSQL/17/bin/psql -U postgres -d nba_ev_tracker`)
- Python 3.11 via Anaconda at `/Users/carterchan/anaconda3`
- Use `/Users/carterchan/anaconda3/bin/python` for CLI scripts (has all dependencies)
- Minor warning: `bottleneck` 1.3.5 installed, pandas wants 1.3.6 (cosmetic only)
- Streamlit config at `~/.streamlit/credentials.toml` (email set to empty, headless mode)
- Launch dashboard with: `streamlit run src/visualization_dashboard.py --server.headless true`

## Configuration
- **API:** The Odds API v4 (key in `.env`)
- **API regions:** `us,us2,uk,eu,au` (defined in `config.py` as `ODDS_API_REGIONS`)
- **DB:** PostgreSQL `nba_ev_tracker` on localhost (credentials in `.env`)
- **Poll interval:** 15 minutes
- **Min EV threshold:** 1.0% (for live scanner)
- **Historical EV threshold:** 2.0% (default on Historical page, adjustable)
- **Line movement alert threshold:** 3.0%
- **Starting bankroll:** $1,000
- **Min books for consensus:** 3 (configurable in `ev_calculation.py`)

## Key Design Decisions
- **Game markets benchmark:** Pinnacle no-vig two-way market as "true" probability
- **Player props benchmark:** Pinnacle when available (now works with expanded regions); consensus (median across 3+ books) as fallback
- **Benchmark column** in `ev_opportunities` table tracks which benchmark was used (pinnacle or consensus)
- Sportsbook keys match The Odds API naming
- Pinnacle odds stored in a separate table so closing-line queries are fast
- `bulk_insert` with `execute_values` for performance on each poll cycle
- Dashboard is Streamlit (not Dash) for simplicity
- Player props use the `description` field from The Odds API as `player_name`
- Props are two-way Over/Under markets — same no-vig logic applies
- Player props cannot be auto-settled (no box score data from API); require manual settlement
- DB migration for player_name in `sql/migrate_add_player_props.sql` (already applied)
- Props require per-event endpoint (`/events/{eventId}/odds`), NOT the bulk odds endpoint
- 1-second delay between per-event prop calls to avoid 429 rate limits
- `MIN_BOOKS_FOR_CONSENSUS = 3` in `ev_calculation.py` — configurable
- Live EV page filters to latest scan batch (within 2-minute window of most recent `found_at`)
- `sys.path` fix at top of `visualization_dashboard.py` for Streamlit compatibility
- Commence time displayed in "January 1, 2026, 7:30pm" format throughout dashboard
- Game detail view on Live EV page shows all odds from all sportsbooks for a selected game

## Not Yet Done / Next Steps
- [x] Runtime test: `python main.py init` -> `python main.py run-once`
- [x] Add `.env` to `.gitignore` before any git push
- [x] Add player props (10 NBA prop markets)
- [x] Pinnacle props via expanded regions
- [x] Consensus-line benchmark as fallback
- [x] American odds on dashboard
- [x] Dashboard deduplication
- [x] Last refresh timestamp on Live EV page
- [x] Historical Opportunities page with date range + min EV filter
- [x] Benchmark column (Pinnacle/Consensus) on EV tables
- [x] Commence time formatted nicely
- [x] Game detail view (all markets for a selected game)
- [x] Verified sportsbook availability — bet365 not available via The Odds API
- [ ] Consider Kelly criterion sizing in `ev_calculation.py`
- [ ] Consider Slack/email alert backend
- [ ] Multi-league extension (NHL, MLB, etc.)
- [ ] Git init + first commit
- [ ] Consider alternative bet365 data source (SportsGameOdds free tier)

## File Quick Reference
```
bettingTool/
├── main.py                          # CLI: init, run-once, scheduler, dashboard, place-bet
├── requirements.txt                 # python-dotenv, requests, psycopg2-binary, apscheduler, streamlit, plotly, pandas, numpy
├── .env                             # API key + DB creds (DO NOT commit)
├── .gitignore
├── README.md
├── info/
│   ├── outline.md                   # Project spec / feature outline
│   └── context.md                   # This file — conversation context
├── sql/
│   ├── schema.sql                   # PostgreSQL DDL (6 tables, benchmark column on ev_opportunities)
│   └── migrate_add_player_props.sql # Migration: add player_name column (already applied)
└── src/
    ├── __init__.py
    ├── config.py                    # Central config, 14 sportsbooks, 10 prop markets, ODDS_API_REGIONS
    ├── data_fetching.py             # Odds API: bulk for games, per-event for props, uses ODDS_API_REGIONS
    ├── database.py                  # PostgreSQL pool, CRUD, game detail query, historical helpers
    ├── ev_calculation.py            # EV/edge/CLV math, Pinnacle + consensus scanner, benchmark label
    ├── strategy_analysis.py         # pandas ROI/CLV/correlation analysis
    ├── visualization_dashboard.py   # Streamlit dashboard (5 pages), sys.path fix, game detail view
    ├── scheduler.py                 # APScheduler background jobs
    └── alerts.py                    # Pluggable alert system
```

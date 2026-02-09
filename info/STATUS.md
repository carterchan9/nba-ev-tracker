# Project Status — Current Snapshot

**Last Updated:** 2026-02-09
**Phase:** Feature-complete, regional optimization in progress
**Dashboard:** Running on http://localhost:8502 (PID: 10988)

---

## 🚨 Critical Alerts

### API Quota
- **Remaining:** 1/500 requests
- **Resets:** Monthly
- **Impact:** Cannot run scans until reset

### Known Issues
1. **Odds accuracy:** betriver.ca shows -107, API returns +114
2. **Regional support incomplete:** "ca" region not verified
3. **Risk:** Next scan might fail or return wrong data if "ca" invalid

---

## ✅ Working Features

### Dashboard (5 Pages)
1. **Live EV Opportunities**
   - Shows only current scan (ev_opportunities_live)
   - Best book per market with positive EV count
   - Click-to-expand to view all books
   - Line transparency (sportsbook + Pinnacle points displayed)

2. **Historical Opportunities**
   - Full historical record (ev_opportunities)
   - Date range filter, adjustable min EV%
   - EV distribution charts

3. **Line Movement**
   - Per-game odds time-series
   - Market type filtering

4. **Bankroll & P/L**
   - KPIs (bankroll, profit, ROI, win rate)
   - Equity curve, bankroll history

5. **Performance Analytics**
   - ROI by sportsbook/market
   - EV vs actual correlation
   - CLV analysis, profit heatmap

### Data Pipeline
- ✅ The Odds API integration (v4)
- ✅ EV/edge/CLV calculations
- ✅ Pinnacle benchmark (all markets)
- ✅ Consensus fallback
- ✅ Line matching verification
- ✅ Auto-settlement for game markets
- ⚠️ Regional support (needs verification)

### Database
- 7 tables (added ev_opportunities_live)
- PostgreSQL 17
- Connection pooling
- Separate live/historical data

---

## ⚠️ Action Items Before Next Scan

### Pre-Flight Checklist
- [ ] Verify "ca" is valid Odds API region code
- [ ] Find correct sportsbook key for betriver.ca
- [ ] Check if Canadian sportsbooks supported
- [ ] Test with 1 request first
- [ ] If "ca" invalid: revert to `us,us2,uk,eu,au`

### Why This Matters
If "ca" is not valid:
- Scan will clear live table
- API might return wrong US data
- OR scan fails and nothing displays

---

## 📊 Configuration

### API
- **Source:** The Odds API v4
- **Key:** Stored in .env
- **Regions:** `ca,us,us2,uk,eu,au` (⚠️ "ca" unverified)
- **Preferred Region:** `ca` (Ontario)

### Markets (10 props + 3 game)
**Game:** h2h, spreads, totals
**Props:** points, rebounds, assists, threes, blocks, steals, PRA, P+R, P+A, R+A

### Sportsbooks (14 configured)
**Active:** fanduel, draftkings, betmgm, betway, espnbet, hardrockbet, fliff, betrivers, bovada, pinnacle
**Inactive:** bet365, sportsinteraction, bet99, williamhill_us, proline

### Thresholds
- **Min EV:** 1.0% (live scanner)
- **Historical EV:** 2.0% (default, adjustable)
- **Line movement alert:** 3.0%
- **Poll interval:** 15 minutes
- **Starting bankroll:** $1,000

---

## 📈 API Usage

### Cost per Scan
- **Game markets:** 3 requests (h2h, spreads, totals)
- **Player props:** ~100 requests (~10 events × 10 markets)
- **Other:** 5 requests (events list, scores)
- **Total:** ~120-140 requests per scan

### Free Tier Limits
- **Monthly quota:** 500 requests
- **Scans possible:** ~3-4 per month
- **Current status:** 1/500 remaining

---

## 🗂️ Database Schema

### Tables
1. `games` — NBA games with scores and status
2. `odds_snapshots` — Sportsbook odds (includes `region`, `player_name`)
3. `pinnacle_odds` — Pinnacle odds (includes `region`, `player_name`)
4. `ev_opportunities` — Historical +EV bets (includes `pinnacle_point`, `benchmark`)
5. `ev_opportunities_live` — Current scan only (same schema as above)
6. `user_bets` — User-placed bets with outcomes
7. `bankroll_history` — Bankroll snapshots

### Recent Schema Changes
- Added `ev_opportunities_live` table
- Added `pinnacle_point` columns (verify line matching)
- Added `region` columns (track data source)

---

## 🛠️ Environment

### System
- **OS:** macOS (Darwin 25.2.0)
- **Python:** 3.11 via Anaconda (`/Users/carterchan/anaconda3/bin/python`)
- **Database:** PostgreSQL 17 at `/Library/PostgreSQL/17`
- **Dashboard:** Streamlit (headless mode)

### Paths
- **Project:** `/Users/carterchan/Documents/self-projects/bettingTool`
- **Config:** `.env` (credentials, API key, thresholds)
- **psql:** Use full path with PGPASSWORD (not on PATH)

### GitHub
- **Repo:** https://github.com/carterchan9/nba-ev-tracker
- **Status:** Public

---

## 📝 Next Session Priorities

1. **Verify Canadian API support** (before wasting quota)
2. **Test regional implementation** (1 request test)
3. **Activate region filtering** (if verified)
4. **Consider API plan upgrade** (if free tier insufficient)

---

*Update this file after each session to reflect current status*

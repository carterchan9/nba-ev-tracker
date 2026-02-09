# Session History — Running Log

This file tracks all development sessions in chronological order (newest first).

---

## Session 2026-02-09 — Dashboard UX + Regional Support

### Goals
1. Improve dashboard UX (best book display, line transparency)
2. Add regional support for Ontario (Canada) betting odds

### Completed ✅
1. **Best book display with multi-book counting**
   - Show only highest EV book per market
   - Added `num_positive_ev_books` column
   - Click-to-expand to view all competing books

2. **Line matching transparency**
   - Added `pinnacle_point` column to verify comparisons use same line
   - Display shows both sportsbook point and Pinnacle point side-by-side

3. **Separate historical/live tables**
   - Created `ev_opportunities_live` (cleared on each scan)
   - Keep `ev_opportunities` for historical record
   - No more stale data in Live view

4. **Pinnacle preference for all markets**
   - Changed to prefer Pinnacle for ALL markets (including props)
   - Consensus only as fallback

### In Progress ⚠️
5. **Regional support (INCOMPLETE)**
   - Added "ca" to `ODDS_API_REGIONS` WITHOUT verification
   - Added `PREFERRED_REGION` config (default: "ca")
   - Added `region` columns to odds tables
   - Created region filtering function (not yet active)

### Critical Issues Discovered 🚨
- **API quota exhausted:** 1/500 requests remaining
- **Odds accuracy issue:** betriver.ca shows -107, API returns +114
- **Root cause unknown:** Might be invalid region code or wrong sportsbook key

### Files Modified
**Source Code:**
- `src/config.py` - Added PREFERRED_REGION, updated ODDS_API_REGIONS
- `src/database.py` - Live table functions, region filtering, pinnacle_point
- `src/ev_calculation.py` - Updated benchmark logic, live table inserts
- `src/visualization_dashboard.py` - Best book display, click-to-expand

**Schema:**
- `sql/schema.sql` - Added ev_opportunities_live, pinnacle_point, region columns
- `.env` - Added PREFERRED_REGION=ca

**Database Migrations:**
```sql
CREATE TABLE ev_opportunities_live (...);
ALTER TABLE ev_opportunities ADD COLUMN pinnacle_point REAL;
ALTER TABLE ev_opportunities_live ADD COLUMN pinnacle_point REAL;
ALTER TABLE odds_snapshots ADD COLUMN region TEXT DEFAULT 'us';
ALTER TABLE pinnacle_odds ADD COLUMN region TEXT DEFAULT 'us';
```

### Action Items Before Next Scan
- [ ] Verify "ca" is valid Odds API region code
- [ ] Find correct sportsbook key for betriver.ca
- [ ] Test with 1 request before full scan
- [ ] Check if Canadian sportsbooks supported by API

### Lessons Learned
1. Always verify API parameters before implementation
2. API quota management is critical (exhausted faster than expected)
3. Test assumptions with minimal requests first

---

## Session 2026-02-07 — Initial Build

### Completed ✅
- Full project scaffold with 8 source modules + CLI
- PostgreSQL schema (6 tables)
- The Odds API integration for odds + scores
- EV/edge/CLV calculation engine
- Opportunity scanner (Pinnacle benchmark)
- Streamlit dashboard (5 pages)
- 10 NBA player prop markets
- Pinnacle props via expanded API regions
- Consensus-line fallback
- American odds display

### Runtime Test Results
- Schema created successfully
- 13,082 sportsbook + 506 Pinnacle odds stored
- 289 +EV opportunities found across 12 games
- Dashboard launched on http://localhost:8501

---

*Note: Add new sessions at the top of this file (reverse chronological order)*

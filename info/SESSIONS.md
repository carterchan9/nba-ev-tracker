# Session History — Running Log

This file tracks all development sessions in chronological order (newest first).

---

## Session 2026-02-09b — Educational Mode + Terminal Documentation

### Session Context
**Duration:** ~30 minutes
**Starting point:** User requested educational explanations when using terminal commands
**Goal:** Enable learning mode for all future projects

### Completed ✅
1. **Global Educational Mode**
   - Added "GLOBAL PREFERENCES" section to MEMORY.md
   - Now explains all terminal commands with plain English descriptions
   - Defines terminology and flags as they're used
   - Applies to ALL future projects

2. **Comprehensive Terminal Guide**
   - Created `info/TERMINAL_GUIDE.md` (300+ lines)
   - Covers: navigation, file ops, searching, git, postgres, python
   - Includes pro tips, shortcuts, dangerous commands warnings
   - Beginner-friendly with tables and examples

3. **Documentation Updates**
   - Updated INDEX.md to include terminal guide
   - Updated README.md to link to new docs
   - Added quick reference entries

### Files Created
- `info/TERMINAL_GUIDE.md` — Terminal command reference guide
- `info/GIT_WORKFLOW.md` — Already existed, now referenced in global memory

### Files Modified
- `MEMORY.md` — Added global preferences (educational mode + git workflow)
- `info/INDEX.md` — Added terminal guide entry
- `info/README.md` — Added terminal guide and git workflow links
- `info/SESSIONS.md` — This file (added session entry)

### Key Changes
**MEMORY.md - Global Preferences Section:**
```markdown
## 🎓 GLOBAL PREFERENCES — Apply to ALL Projects

### Educational Mode: Terminal Command Explanations
**ALWAYS provide short educational descriptions when using terminal commands:**
- Explain what the command does in plain English
- Define terminology and flags (e.g., `-d` flag, `&&` operator)
- Describe the expected output
- Teach filesystem navigation concepts as they come up
```

### Impact
- All future terminal commands will include educational explanations
- User can reference TERMINAL_GUIDE.md for comprehensive learning
- Consistent experience across all projects

---

## Session 2026-02-09 — Dashboard UX + Regional Support + Documentation

### Session Context
**Duration:** ~3 hours
**Starting point:** Dashboard showing all books for same market, unclear line comparisons
**User location:** Ontario, Canada
**Pain point:** betriver.ca odds not matching API data (-107 actual vs +114 from API)

### Goals
1. Improve dashboard UX (best book display, line transparency)
2. Add regional support for Ontario (Canada) betting odds
3. Fix data accuracy issues
4. Reorganize project documentation

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

### Conversation Flow & Technical Details

**Phase 1: Dashboard UX Improvements**
- **User request:** "Show point totals for transparency, show only best book per market with count, enable click-to-expand"
- **Implementation:** Modified `_prepare_ev_df()` in visualization_dashboard.py to group by market and keep highest EV book
- **Key code change:** Added `num_positive_ev_books` column using pandas transform:
  ```python
  df["num_positive_ev_books"] = df.groupby(group_cols)["ev_percent"].transform("count")
  df = df.sort_values("ev_percent", ascending=False).drop_duplicates(subset=group_cols, keep="first")
  ```
- **Result:** Dashboard now shows best book + count, with market selector dropdown for viewing all books

**Phase 2: Data Freshness Issues**
- **Problem 1:** Dashboard showing nothing (data was 2 days old, hours=1 filter returned 0 results)
- **Solution:** Ran fresh scan with `python main.py run-once`, found 175 new opportunities
- **Problem 2:** User feedback: "when I press refresh, I need old data to no longer appear"
- **Root cause:** Same opportunities legitimately reappeared if still +EV (e.g., Jaime Jaquez)
- **Solution:** Created separate `ev_opportunities_live` table that clears on each scan
- **Key code change:** Added `clear_live_ev_opportunities()` at start of `scan_all_upcoming()`:
  ```python
  def scan_all_upcoming() -> list[dict[str, Any]]:
      clear_live_ev_opportunities()  # Clear before fresh scan
      games = get_upcoming_games()
      # ... rest of scan logic
  ```
- **Result:** Live view now only shows current scan data, historical table preserves all records

**Phase 3: Benchmark Logic & Line Matching**
- **User question:** "Why does my benchmark say consensus when I have pinnacle_odds?"
- **Issue:** Code restricted Pinnacle to game markets only: `if not is_prop and lookup_key in pin_lookup`
- **Solution:** Removed restriction to prefer Pinnacle for ALL markets (props included)
- **Key code change in ev_calculation.py:**
  ```python
  # Before: if not is_prop and lookup_key in pin_lookup:
  # After:  if lookup_key in pin_lookup:
  pinnacle_point = None
  if lookup_key in pin_lookup:
      bench_row = pin_lookup[lookup_key]
      bench_dec = bench_row["odds_decimal"]
      pinnacle_point = bench_row.get("point")
      bench_label = "pinnacle"
  ```
- **User verification request:** "Are comparisons using same point totals? (e.g., Bam Adebayo Over 20.5 vs Pinnacle at 20.5?)"
- **Solution:** Added `pinnacle_point` column to verify point matching
- **Schema changes:**
  ```sql
  ALTER TABLE ev_opportunities ADD COLUMN pinnacle_point REAL;
  ALTER TABLE ev_opportunities_live ADD COLUMN pinnacle_point REAL;
  ```
- **Result:** Dashboard now displays both sportsbook point and Pinnacle point side-by-side for transparency

**Phase 4: Odds Accuracy Crisis**
- **User observation:** "I see Bam over 20.5 at -107 on betriver.ca, API shows +114"
- **Analysis:** -107 = 1.935 decimal, +114 = 2.14 decimal (significant discrepancy)
- **Hypothesis:** "betrivers" sportsbook key might be US-only, not betriver.ca
- **User decision:** "Add Canada region, I'm in Ontario"
- **Implementation:** Added "ca" to ODDS_API_REGIONS WITHOUT verification (CRITICAL ERROR)
- **Key config changes:**
  ```python
  # src/config.py
  ODDS_API_REGIONS: str = "ca,us,us2,uk,eu,au"  # Added "ca"
  PREFERRED_REGION: str = os.getenv("PREFERRED_REGION", "ca")
  ```
- **Schema changes:** Added `region` columns to odds_snapshots and pinnacle_odds
- **User catch (excellent):** "If it doesn't recognize 'ca', won't live table be empty?"
- **Status:** UNFIXED - API quota exhausted (1/500 remaining), can't test until monthly reset
- **Risk:** If "ca" invalid, next scan will clear live table and fail or return wrong data

**Phase 5: Documentation Reorganization**
- **User request:** "Update project info, save current progress"
- **Then:** "I wish to have session summary as a running list, rename and re-arrange"
- **Created new structure:**
  - `info/INDEX.md` - Documentation navigation guide (start here)
  - `info/STATUS.md` - Current project status snapshot with alerts
  - `info/SESSIONS.md` - Running session history (this file)
  - `info/OUTLINE.md` - High-level architecture overview
  - `info/NOTES.md` - Technical implementation details (renamed from context.md)
  - `info/GIT_WORKFLOW.md` - Feature branch workflow guide
- **Updated root README.md** to point to info/ documentation structure
- **Result:** Clear, organized documentation that separates concerns

**Phase 6: Git Workflow Establishment**
- **User request 1:** "Commit these changes, update my GitHub"
- **User request 2:** "I wish to maintain GitHub repo best practices, ensure changes go through short-lived branch creation"
- **Implementation:** Created comprehensive GIT_WORKFLOW.md with:
  - Feature branch naming conventions (feature/, fix/, docs/, refactor/)
  - Standard workflow (create → commit → push → merge → delete)
  - Commit message format with examples
  - Quick reference commands
  - Emergency undo procedures
- **Committed changes:**
  ```bash
  git add [files]
  git commit -m "Add dashboard UX improvements and regional support..."
  git push origin main
  ```
- **Memory update:** Added "Git Workflow — ALWAYS USE FEATURE BRANCHES" section to MEMORY.md
- **Result:** All future changes will use feature branch workflow

**Key Technical Decisions:**
1. **Separate live/historical tables** - Prevents old data confusion, live table clears on each scan
2. **Pinnacle for ALL markets** - More consistent benchmark, consensus only as fallback
3. **Point matching transparency** - pinnacle_point column verifies same-line comparisons
4. **Best book display** - Reduces clutter, shows count of competing +EV books
5. **Region tracking** - Prepare for multi-region support (implementation incomplete)

**User Feedback Highlights:**
- "If 'ca' invalid, won't live table be empty?" - Correctly identified critical risk
- "Old data should not appear after refresh" - Led to separate tables solution
- "Same opportunity appearing is old data" - Clarified freshness requirement
- "Running list, not separate session files" - Led to SESSIONS.md structure
- "I see -107 on betriver.ca, API shows +114" - Discovered accuracy issue

**Errors Encountered:**
1. **Stale data (hours=1 filter)** → Ran fresh scan to populate recent data
2. **Old opportunities reappearing** → Created separate ev_opportunities_live table
3. **Region filtering showing nothing** → Reverted to non-filtered query until next scan
4. **Multiple Streamlit instances** → Killed old process (PID 97704)
5. **Missing region columns** → Ran ALTER TABLE migrations manually
6. **Added "ca" without verification** → CRITICAL UNRESOLVED RISK

**API Quota Status:**
- Used: 499/500 requests (exhausted in session)
- Remaining: 1 request
- Next scan: Wait for monthly reset or upgrade plan
- Pre-scan checklist: Verify "ca" region code, test with 1 request first

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

# Git Workflow — Feature Branch Best Practices

This project follows GitHub best practices using short-lived feature branches.

---

## 🚫 Never Commit Directly to Main

All changes must go through a feature branch, even for solo development. This maintains:
- Clean commit history
- Easy rollback capability
- CI/CD compatibility
- Professional workflow habits

---

## ✅ Standard Workflow

### 1. Create Feature Branch
```bash
# Start from updated main
git checkout main
git pull origin main

# Create feature branch with descriptive name
git checkout -b feature/add-region-filtering

# Alternative: create and switch in one command
git switch -c feature/add-region-filtering
```

### 2. Make Changes & Commit
```bash
# Make your changes...

# Check status
git status

# Stage specific files (avoid `git add .`)
git add src/database.py src/config.py

# Commit with descriptive message
git commit -m "$(cat <<'EOF'
Add region filtering for Ontario sportsbooks

- Create get_odds_by_region() function
- Add PREFERRED_REGION config
- Update dashboard to filter by region

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

### 3. Push Feature Branch
```bash
# Push to GitHub
git push origin feature/add-region-filtering

# Or set upstream and push
git push -u origin feature/add-region-filtering
```

### 4. Merge to Main
```bash
# Switch to main
git checkout main

# Pull latest (in case of remote changes)
git pull origin main

# Merge feature branch
git merge feature/add-region-filtering

# Push to GitHub
git push origin main
```

### 5. Clean Up Branch
```bash
# Delete local branch
git branch -d feature/add-region-filtering

# Delete remote branch
git push origin --delete feature/add-region-filtering
```

---

## 📝 Branch Naming Conventions

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New features or enhancements | `feature/add-kelly-criterion` |
| `fix/` | Bug fixes | `fix/odds-decimal-conversion` |
| `docs/` | Documentation only | `docs/update-setup-guide` |
| `refactor/` | Code refactoring | `refactor/database-queries` |
| `hotfix/` | Urgent production fixes | `hotfix/api-key-leak` |

**Format:** `prefix/short-kebab-case-description`

**Examples:**
- ✅ `feature/add-region-support`
- ✅ `fix/dashboard-refresh-bug`
- ✅ `docs/session-history`
- ❌ `my-changes` (no prefix)
- ❌ `feature/AddRegionSupport` (use kebab-case, not PascalCase)

---

## 🔄 Quick Reference Commands

### Create & Switch to Branch
```bash
git checkout -b feature/my-feature
# or
git switch -c feature/my-feature
```

### List Branches
```bash
git branch              # local branches
git branch -r           # remote branches
git branch -a           # all branches
```

### Delete Branch
```bash
git branch -d feature/my-feature           # local (safe delete)
git branch -D feature/my-feature           # local (force delete)
git push origin --delete feature/my-feature  # remote
```

### Check Current Branch
```bash
git branch --show-current
# or
git status
```

---

## 🎯 Commit Message Format

Follow this template for consistency:

```
[Short imperative summary - max 70 chars]

[Optional detailed description]
- Bullet points for key changes
- Keep it concise but informative
- Explain WHY, not just WHAT

[Optional: breaking changes, migration notes, etc.]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Good examples:**
- "Add region filtering for Ontario sportsbooks"
- "Fix dashboard refresh clearing live table prematurely"
- "Refactor EV calculation to prefer Pinnacle for all markets"

**Bad examples:**
- ❌ "updates" (too vague)
- ❌ "Fixed bug" (which bug?)
- ❌ "asdf" (not descriptive)

---

## 🚨 Emergency: Need to Undo?

### Undo Last Commit (Not Pushed)
```bash
git reset --soft HEAD~1    # Keep changes staged
# or
git reset --mixed HEAD~1   # Keep changes unstaged
# or
git reset --hard HEAD~1    # Discard changes (DANGEROUS)
```

### Undo Pushed Commit
```bash
# Create revert commit (safe)
git revert HEAD
git push origin main
```

### Abandon Feature Branch
```bash
git checkout main
git branch -D feature/bad-idea
```

---

## 📊 Example Session Workflow

```bash
# --- Start of session ---

# 1. Update main
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/add-clv-dashboard

# 3. Make changes, test, verify
# ... edit files ...

# 4. Stage and commit
git add src/visualization_dashboard.py src/strategy_analysis.py
git status
git commit -m "Add CLV analysis page to dashboard"

# 5. Push feature branch
git push origin feature/add-clv-dashboard

# 6. Merge to main
git checkout main
git merge feature/add-clv-dashboard
git push origin main

# 7. Clean up
git branch -d feature/add-clv-dashboard
git push origin --delete feature/add-clv-dashboard

# --- End of session ---
```

---

## 🔍 Verification Checklist

Before merging to main:
- [ ] Changes tested locally
- [ ] Dashboard runs without errors
- [ ] Database migrations documented
- [ ] No sensitive data committed (.env excluded)
- [ ] Commit message is descriptive
- [ ] All files staged intentionally (not `git add .`)
- [ ] Claude co-author attribution added

---

## 📚 Additional Resources

- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project)

---

*This workflow is enforced via memory notes. Claude will always create feature branches.*

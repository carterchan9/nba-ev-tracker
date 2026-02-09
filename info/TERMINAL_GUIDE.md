# Terminal Guide — Command Line Essentials

A beginner-friendly guide to understanding terminal commands and concepts.

---

## 📍 What is the Terminal?

The **terminal** (also called command line, shell, or CLI) is a text-based interface for interacting with your computer. Instead of clicking icons, you type commands.

**Why use it?**
- Faster for repetitive tasks
- More powerful than GUI tools
- Required for development tools (git, python, databases)
- Can automate workflows with scripts

---

## 🧭 Navigation Basics

### Understanding Paths

**Absolute path:** Full path from root of filesystem
```bash
/Users/carterchan/Documents/self-projects/bettingTool
```
- Starts with `/` (root directory on macOS/Linux)
- Always specifies exact location regardless of where you are

**Relative path:** Path relative to your current location
```bash
./info/STATUS.md          # Current directory (./)
../other-project/file.py  # Parent directory (../)
```
- `.` means "current directory"
- `..` means "parent directory"
- `~` means "home directory" (e.g., `/Users/carterchan`)

### Core Navigation Commands

| Command | What it does | Example |
|---------|-------------|---------|
| `pwd` | **P**rint **W**orking **D**irectory - shows where you are | `pwd` → `/Users/carterchan/Documents` |
| `ls` | **L**i**s**t files in current directory | `ls` → shows files and folders |
| `cd` | **C**hange **D**irectory - move to another folder | `cd ~/Documents` → go to Documents |
| `cd ..` | Go up one directory level (to parent) | If in `/Users/carterchan/Documents`, go to `/Users/carterchan` |
| `cd ~` | Go to home directory | Always takes you to `/Users/carterchan` |
| `cd -` | Go back to previous directory | Toggle between two locations |

**Common `ls` flags:**
- `ls -l` → Long format (shows permissions, size, date)
- `ls -a` → Show **a**ll files (including hidden files starting with `.`)
- `ls -la` → Combine both (long format + all files)
- `ls -lh` → **H**uman-readable file sizes (1.2M instead of 1234567)

---

## 📂 File Operations

### Viewing Files

| Command | What it does | Example |
|---------|-------------|---------|
| `cat filename` | Display entire file contents | `cat README.md` |
| `head -n 10 file` | Show first 10 lines | `head -n 20 data.csv` |
| `tail -n 10 file` | Show last 10 lines | `tail -n 50 logs.txt` |
| `less filename` | View file with scrolling (press `q` to quit) | `less large-file.log` |

### Creating & Modifying

| Command | What it does | Example |
|---------|-------------|---------|
| `touch filename` | Create empty file or update timestamp | `touch new-file.txt` |
| `mkdir dirname` | **M**a**k**e **dir**ectory (create folder) | `mkdir my-folder` |
| `mkdir -p a/b/c` | Create nested directories (including parents) | Creates `a/`, `a/b/`, `a/b/c/` |
| `cp source dest` | **C**o**p**y file | `cp file.txt backup.txt` |
| `mv source dest` | **M**o**v**e or rename file | `mv old.txt new.txt` |
| `rm filename` | **R**e**m**ove (delete) file | `rm temp.txt` |
| `rm -r dirname` | Remove directory **r**ecursively | `rm -r old-folder/` |
| `rm -rf dirname` | **F**orce remove without confirmation (DANGEROUS) | `rm -rf node_modules/` |

**⚠️ Warning:** `rm` is permanent - no trash/recycle bin!

---

## 🔍 Searching

### Finding Files

```bash
# Find files by name pattern
find . -name "*.py"           # All Python files in current dir
find /path -name "config*"    # Files starting with "config"
find . -type f -name "*.txt"  # Only files (not directories)
find . -type d -name "test*"  # Only directories
```

**Better alternative:** `glob` patterns (what I use in the Glob tool)
```bash
**/*.py        # All .py files in all subdirectories
src/**/*.js    # All .js files under src/
*.{md,txt}     # All .md and .txt files in current dir
```

### Searching File Contents

```bash
# grep = Global Regular Expression Print
grep "pattern" file.txt               # Search for pattern in file
grep -r "pattern" .                   # Search recursively in all files
grep -i "pattern" file.txt            # Case-insensitive search
grep -n "pattern" file.txt            # Show line numbers
grep -v "pattern" file.txt            # Show lines that DON'T match (invert)

# Combining with pipes
cat file.txt | grep "error"           # Filter file contents
ls -l | grep ".py"                    # Filter ls output
```

**Better alternative:** `rg` (ripgrep) - faster modern version
```bash
rg "pattern"              # Smart search (ignores .gitignore)
rg -i "pattern"           # Case-insensitive
rg --type py "pattern"    # Only search Python files
```

---

## 🔗 Command Operators

### Chaining Commands

| Operator | What it does | Example |
|----------|-------------|---------|
| `;` | Run commands sequentially (even if previous fails) | `cd /tmp ; ls` |
| `&&` | Run next command ONLY if previous succeeds | `mkdir test && cd test` |
| `\|\|` | Run next command ONLY if previous fails | `command \|\| echo "Failed"` |
| `\|` | **Pipe** - send output of first command to second | `cat file \| grep "error"` |

**Examples:**
```bash
# Good: Create directory AND move into it (only if mkdir succeeds)
mkdir my-project && cd my-project

# Bad: Could end up in wrong directory if mkdir fails
mkdir my-project ; cd my-project

# Pipe example: Count lines containing "error"
cat logfile.txt | grep "error" | wc -l
```

### Redirection

| Operator | What it does | Example |
|----------|-------------|---------|
| `>` | Redirect output to file (overwrites) | `echo "hello" > file.txt` |
| `>>` | Redirect output to file (appends) | `echo "world" >> file.txt` |
| `<` | Read input from file | `python script.py < input.txt` |
| `2>` | Redirect errors to file | `command 2> errors.log` |
| `&>` | Redirect both output and errors | `command &> all-output.log` |

---

## 🐍 Python Commands

### Running Python

```bash
# Run Python script
python script.py                    # Use default python
python3 script.py                   # Use Python 3 specifically
/path/to/anaconda3/bin/python       # Use specific Python installation

# Python REPL (interactive shell)
python                              # Enter interactive mode
exit()                              # Exit REPL

# Python one-liners
python -c "print('hello')"          # Execute Python code directly
python -m pip install package       # Run module as script
```

### Virtual Environments

```bash
# Create virtual environment
python -m venv .venv                # Create .venv folder

# Activate virtual environment
source .venv/bin/activate           # macOS/Linux
.venv\Scripts\activate              # Windows

# Install packages
pip install package-name
pip install -r requirements.txt     # Install from file

# Deactivate
deactivate
```

---

## 🗄️ Database Commands (PostgreSQL)

### Using psql

```bash
# Connect to database
psql -U username -d database_name
PGPASSWORD='password' psql -U postgres -d nba_ev_tracker

# Common psql meta-commands (inside psql)
\l                    # List all databases
\c database_name      # Connect to database
\dt                   # List all tables
\d table_name         # Describe table structure
\q                    # Quit psql

# Run SQL from command line
psql -U user -d db -c "SELECT * FROM table;"

# Run SQL file
psql -U user -d db -f schema.sql
```

---

## 🌿 Git Commands

### Basic Workflow

```bash
# Check status
git status                          # Show changed files, current branch

# Stage changes
git add file.txt                    # Stage specific file
git add src/                        # Stage entire directory
git add -A                          # Stage all changes (use cautiously)

# Commit changes
git commit -m "Commit message"      # Commit with message
git commit -m "$(cat <<'EOF'        # Multi-line commit message
Summary line

- Detail 1
- Detail 2
EOF
)"

# Push/Pull
git push origin main                # Upload commits to GitHub
git pull origin main                # Download commits from GitHub

# Branches
git branch                          # List local branches
git branch -a                       # List all branches (including remote)
git checkout -b feature/new         # Create and switch to new branch
git checkout main                   # Switch to main branch
git merge feature/new               # Merge feature into current branch
git branch -d feature/new           # Delete branch (safe)
git branch -D feature/new           # Force delete branch
```

### Inspection

```bash
git log                             # Show commit history
git log --oneline                   # Compact history
git log --oneline -n 5              # Last 5 commits
git diff                            # Show unstaged changes
git diff --staged                   # Show staged changes
git show HEAD                       # Show last commit
```

---

## 🎭 Process Management

### Running Commands

```bash
# Foreground (normal)
python script.py                    # Runs, blocks terminal until done

# Background
python script.py &                  # Runs in background, returns control

# Check running processes
ps aux | grep python                # Find Python processes
ps aux | grep streamlit             # Find Streamlit processes

# Kill process
kill PID                            # Graceful shutdown (send SIGTERM)
kill -9 PID                         # Force kill (send SIGKILL)
killall python                      # Kill all Python processes
```

---

## 🔧 Common Flags

**What are flags?** Optional arguments that modify command behavior, usually start with `-` or `--`

| Flag | Meaning | Example Command |
|------|---------|-----------------|
| `-a` | **A**ll | `ls -a` (show hidden files) |
| `-r` | **R**ecursive | `grep -r "pattern"` (search subdirs) |
| `-f` | **F**orce | `rm -rf folder/` (force delete) |
| `-v` | **V**erbose or in**v**ert | `rm -v file` (show what's deleted) OR `grep -v` (invert match) |
| `-h` | **H**uman-readable or **h**elp | `ls -lh` (readable sizes) OR `command -h` (show help) |
| `-n` | **N**umber | `head -n 10` (show 10 lines) |
| `-i` | **I**nteractive or case-**i**nsensitive | `rm -i file` (confirm) OR `grep -i` (ignore case) |
| `-u` | **U**pstream | `git push -u origin branch` (set tracking) |
| `-d` | **D**elete or **d**irectory | `git branch -d name` OR `mkdir -p dir/subdir` |
| `-p` | **P**arent or **p**ort | `mkdir -p a/b/c` OR `psql -p 5432` |

**Combining flags:**
```bash
ls -l -a -h         # Long format, all files, human sizes
ls -lah             # Same thing (combined)
```

---

## 💡 Pro Tips

### Tab Completion
Press `Tab` to auto-complete file names, commands, and paths. Press `Tab` twice to see all options.

```bash
cd Doc[Tab]        # Completes to "Documents/"
python scr[Tab]    # Completes to "script.py"
```

### Command History
```bash
↑ / ↓ arrows       # Navigate through previous commands
Ctrl + R           # Search command history (type to filter)
history            # Show all recent commands
!!                 # Repeat last command
!$                 # Last argument of previous command
```

### Keyboard Shortcuts
```bash
Ctrl + C           # Cancel current command
Ctrl + D           # Exit shell or REPL
Ctrl + L           # Clear screen (same as `clear`)
Ctrl + A           # Jump to start of line
Ctrl + E           # Jump to end of line
Ctrl + U           # Delete from cursor to start
Ctrl + K           # Delete from cursor to end
```

### Getting Help
```bash
man command        # Show manual page (press q to quit)
command --help     # Show command help
command -h         # Short help (if available)
```

---

## 🚨 Dangerous Commands (Be Careful!)

| Command | Why dangerous | Alternative |
|---------|--------------|-------------|
| `rm -rf /` | Deletes everything on system | NEVER run this |
| `rm -rf *` | Deletes everything in current dir | `rm -i` (interactive) |
| `chmod 777 file` | Makes file world-writable (security risk) | Use specific permissions |
| `sudo command` | Runs with admin privileges | Only use when necessary |
| `git push --force` | Overwrites remote history | `--force-with-lease` |
| `git reset --hard` | Discards all local changes | Commit or stash first |

---

## 📚 Quick Reference

### Most Common Commands
```bash
pwd                    # Where am I?
ls -la                 # What's here?
cd ~/path              # Go somewhere
mkdir folder           # Create folder
touch file.txt         # Create file
cat file.txt           # View file
rm file.txt            # Delete file
git status             # Git status
git add file           # Stage file
git commit -m "msg"    # Commit
git push origin main   # Push to GitHub
python script.py       # Run Python
```

### When I Use These Commands
- `ls -la` → Verify directory contents before creating files
- `pwd` → Confirm I'm in the right location
- `cat file` → Check file contents before editing
- `git status` → See what changed before committing
- `ps aux | grep name` → Find process ID before killing
- `kill -9 PID` → Stop stuck processes

---

## 🎯 Next Steps

1. **Practice navigation:** Try `cd`, `ls`, `pwd` in your terminal
2. **Explore files:** Use `cat`, `head`, `less` to view files
3. **Learn git basics:** `git status`, `git add`, `git commit`
4. **Read man pages:** Try `man ls` to learn more about commands
5. **Use tab completion:** It will save you tons of typing!

**Remember:** You can't break anything by reading (`ls`, `cat`, `pwd`), so explore freely!

---

*For more details on this project's workflow, see: GIT_WORKFLOW.md*

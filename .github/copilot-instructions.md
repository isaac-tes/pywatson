---
description: AI rules derived by SpecStory from the project AI interaction history
applyTo: *
---

## PROJECT OVERVIEW
This file defines the project rules, coding standards, workflow guidelines, references, documentation structure, and best practices for the AI coding assistant. It is a living document that evolves with the project.

## CODE STYLE
*   Follow PEP 8 guidelines for Python code.
*   Use descriptive names for variables and functions.
*   Keep functions short and focused.
*   Add docstrings to all functions and classes.
*   Use type hints.

## FOLDER ORGANIZATION
*   `src/`: Source code for the project.
*   `scripts/`: Standalone scripts and utilities.
*   `notebooks/`: Jupyter notebooks for analysis and examples.
*   `tests/`: Unit tests.
*   `plots/`: Generated plots and figures.
*   `data/`: Data files (raw and processed).
*   `docs/`: Documentation.
*   `_research/`: WIP scripts, code, notes, comments, to-dos and anything in an alpha state
*   `_research/tmp/`: Temporary data folder.

## TECH STACK
*   Python 3.12+
*   Click >=8.3.0
*   h5py >=3.14.0
*   Jinja2 >=3.1.6
*   PyYAML >=6.0.3
*   Rich >=14.1.0
*   uv >=0.8.11,<0.9.0 (for build system)
*   pytest >=8.4.2 (for testing)
*   pandas (for csv data loading)

## PROJECT-SPECIFIC STANDARDS
*   Project scaffolding uses the `ProjectScaffolder` class in `core.py`.
*   Templates are located in the `src/pywatson/templates/` directory as `.jinja2` files.
*   Use Jinja2 templates for generating project files.
*   `utils.py` is copied directly and not templated.

## WORKFLOW & RELEASE RULES
*   Create a new branch for each feature or bug fix.
*   Write unit tests for all new code.
*   Run all tests before committing changes.
*   Use uv for dependency management.

## REFERENCE EXAMPLES
*   See `src/pywatson/core.py` for examples of project scaffolding.
*   See `src/pywatson/templates/` for Jinja2 template examples.

## PROJECT DOCUMENTATION & CONTEXT SYSTEM
*   Use README.md to document the project.
*   Use docstrings to document all functions and classes.
*   Project structure should follow the DrWatson.jl-inspired layout.
*   `docs/index.md` is **auto-generated** from `README.md` — run `python scripts/generate_readme.py` before every `mkdocs build`.
*   Always build docs with `--strict`: `python scripts/generate_readme.py && uv run mkdocs build --strict`.

## DEBUGGING
N/A

## FINAL DOs AND DON'Ts
*   **DO** edit templates like normal Python files. They ARE Python files.
*   **DO** use `{{ variable_name }}` for dynamic content. These get replaced.
*   **DO** test after changes. Run `uv run pytest` or create a test project.
*   **DO** check syntax. Your editor will highlight Python syntax errors.
*   **DO** commit template changes. They're source code.
*   **DO** check CI pipelines after every push: run `gh run list` and wait for all runs to show `completed / success` before considering work done. Fix any failures immediately.
*   **DON'T** escape `{}` in templates. Not needed (that was the old problem!).
*   **DON'T** edit generated projects. Edit the template instead.
*   **DON'T** forget to update tests if you change templates significantly.
*   **DON'T** declare a task complete if any CI pipeline (Tests, Build & Deploy Docs) is still running or has failed.


<!-- BEGIN BEADS INTEGRATION -->
## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Dolt-powered version control with native sync
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**

```bash
bd ready --json
```

**Create new issues:**

```bash
bd create "Issue title" --description="Detailed context" -t bug|feature|task -p 0-4 --json
bd create "Issue title" --description="What this issue is about" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**

```bash
bd update <id> --claim --json
bd update bd-42 --priority 1 --json
```

**Complete work:**

```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task atomically**: `bd update <id> --claim`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" --description="Details about what was found" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds AND all CI pipelines pass
- After every push, run `gh run list` and wait for all pipeline runs to complete successfully
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails or CI fails, resolve and retry until everything is green
- Always verify CI status: `gh run list --limit 5` after pushing

<!-- END BEADS INTEGRATION -->

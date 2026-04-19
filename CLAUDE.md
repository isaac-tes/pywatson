# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyWatson is a Python scientific project management tool inspired by
[DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/).
It scaffolds reproducible scientific computing projects with modern Python
tooling (uv, pytest, ruff) and provides utilities for path management, HDF5
data handling, parameter-based filenames, and smart caching.

- **Language**: Python 3.12+
- **Package manager**: [uv](https://docs.astral.sh/uv/) (not pip, not conda)
- **Build backend**: `uv_build`
- **Layout**: `src/` layout — the package lives at `src/pywatson/`
- **Entry point**: `pywatson` CLI via Click → `pywatson.core:cli`

## Build / Lint / Test Commands

All commands use `uv run` to execute inside the project's virtual environment.

```bash
# Setup
uv sync                        # Install all deps including dev group

# Run ALL tests
uv run pytest

# Run a SINGLE test file / class / method
uv run pytest tests/test_scaffolder.py
uv run pytest tests/test_scaffolder.py::TestProjectScaffolder
uv run pytest tests/test_scaffolder.py::TestProjectScaffolder::test_scaffolder_initialization

# Run tests matching a keyword expression
uv run pytest -k "template"

# Verbose output with print capture disabled
uv run pytest -v -s

# Docker-tagged tests (require Docker daemon)
uv run pytest -m docker

# Lint + format (ruff)
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
uv run ruff format --check src/ tests/

# Type check
uv run mypy src/pywatson/

# Build
uv build

# Docs — sync README first, then build with --strict
python scripts/generate_readme.py
uv run mkdocs build --strict

# CLI
uv run pywatson --help
```

## Architecture

| Component | Description |
|-----------|-------------|
| `src/pywatson/core.py` | `ProjectScaffolder` class + Click CLI (`init`, `adopt`, `status`, `sweep`, `summary`) |
| `src/pywatson/utils.py` | PyWatson utilities — copied **verbatim** into generated projects as `pywatson_utils.py` (not templated) |
| `src/pywatson/__init__.py` | Public API re-exports from core + utils |
| `src/pywatson/templates/` | Jinja2 `.jinja2` templates for generated project files |
| `tests/test_scaffolder.py` | Integration tests for ProjectScaffolder |
| `tests/test_templates.py` | Template rendering tests |

### Key Design Decisions

- `utils.py` is copied verbatim — generated projects are fully self-contained and do not depend on pywatson at runtime
- `_PROJECT_ROOT` global caches the project root to avoid repeated filesystem walks
- HDF5 is the default data format (via h5py); metadata stored as JSON in HDF5 attributes
- `save_data` has `include_git=False` by default; `tagsave` always captures git state
- `produce_or_load()` implements DrWatson.jl-style smart caching
- `savename()` creates deterministic filenames from parameter dictionaries
- Three project types: `default`, `minimal`, `full`

## Code Style

- **Line length**: 99 characters (configured in pyproject.toml)
- **Imports**: stdlib > third-party > local; use relative imports (`from .module import ...`)
- **Type annotations**: required on public function signatures; use Python 3.12+ builtins (`list[str]`, `X | None`)
- **Docstrings**: Google style (`Args:`, `Returns:`, `Raises:`)
- **Naming**: PascalCase classes, snake_case functions/variables, UPPER_SNAKE_CASE constants
- **Quotes**: double quotes; trailing commas in multi-line structures

## Testing Conventions

- pytest, organized into `TestXxx` classes within test files
- Fixtures: defined as methods within test classes using `@pytest.fixture` with `yield` + cleanup
- Assertions: plain `assert` (pytest-style), never `unittest` assertions
- No conftest.py — fixtures live inside the test classes that use them
- Generated Python templates validated with `compile()` to verify syntax

## Template Development

- Templates live in `src/pywatson/templates/` as `.jinja2` files
- Common context variables: `project_name`, `package_name`, `author_name`, `author_email`, `project_name_title`, `description`
- After adding a new template, add a rendering test in `tests/test_templates.py`

<!-- BEGIN BEADS INTEGRATION v:1 profile:full hash:f65d5d33 -->
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

### Quality
- Use `--acceptance` and `--design` fields when creating issues
- Use `--validate` to check description completeness

### Lifecycle
- `bd defer <id>` / `bd supersede <id>` for issue management
- `bd stale` / `bd orphans` / `bd lint` for hygiene
- `bd human <id>` to flag for human decisions
- `bd formula list` / `bd mol pour <name>` for structured workflows

### Auto-Sync

bd automatically syncs via Dolt:

- Each write auto-commits to Dolt history
- Use `bd dolt push`/`bd dolt pull` for remote sync
- No manual export/import needed!

### Important Rules

- Use bd for ALL task tracking
- Always use `--json` flag for programmatic use
- Link discovered work with `discovered-from` dependencies
- Check `bd ready` before asking "what should I work on?"
- Do NOT create markdown TODO lists
- Do NOT use external issue trackers
- Do NOT duplicate tracking systems

For more details, see README.md and docs/QUICKSTART.md.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

<!-- END BEADS INTEGRATION -->

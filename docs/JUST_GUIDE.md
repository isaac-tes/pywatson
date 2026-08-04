# Just Guide

Projects created with `pywatson init --project-type full` include a `justfile`
with pre-configured recipes for all common development tasks, run via
[`just`](https://github.com/casey/just). Run `just` or `just --list` at any
time to see a summary of available recipes.

> **Note**: The `justfile` is only generated for `--project-type full`.
> `default` and `minimal` projects do not include one.

---

## Installing just

`just` is not preinstalled on most systems. Install it via your package
manager or [the official install instructions](https://github.com/casey/just#installation):

```bash
# macOS
brew install just

# Ubuntu / Debian
sudo apt-get install just

# Any platform, via cargo
cargo install just
```

---

## Quick reference

| Recipe | What it does |
|--------|-------------|
| `just` / `just --list` | List all recipes with descriptions |
| `just setup` | Install all dependencies (runs `uv sync`) |
| `just test` | Run the test suite |
| `just test-cov` | Run tests and show a coverage report |
| `just lint` | Check code with ruff |
| `just lint-fix` | Auto-fix ruff lint issues |
| `just format` | Format code with ruff |
| `just format-check` | Check formatting without modifying files |
| `just typecheck` | Run the configured type checker |
| `just check` | Run all quality gates (lint + format + typecheck + test) |
| `just data` | Execute `scripts/generate_data.py` |
| `just analyze` | Execute `scripts/analyze_data.py` |
| `just docs` | Build documentation (configure as needed) |
| `just build` | Build the distribution package |
| `just clean` | Remove build artefacts |

---

## Type checker integration

The `typecheck` recipe adapts to whichever type checker you chose when
creating the project:

```bash
# If you chose --type-checker ty (default):
just typecheck   # runs: uv run ty check src/<package>/

# If you chose --type-checker mypy:
just typecheck   # runs: uv run mypy src/<package>/

# If you chose --type-checker none:
just typecheck   # prints a notice and exits successfully
```

Similarly, `just check` omits the typecheck step when no type checker was
configured.

---

## Common workflows

### First-time setup

```bash
just setup       # creates .venv and installs all deps via uv sync
```

### Before committing

```bash
just check       # lint + format-check + typecheck + tests in one shot
```

### Run only tests

```bash
just test        # fast, no coverage
just test-cov    # with coverage report
```

### Fix formatting / lint issues

```bash
just format      # auto-format with ruff
just lint-fix    # auto-fix lint violations
```

### Run data pipeline

```bash
just data        # generate raw / simulated data
just analyze     # run analysis scripts
```

---

## Customising recipes

The `justfile` is plain `just` syntax — edit it freely. Add project-specific
recipes at the end:

```just
# Run the long simulation (high resolution)
sim-long:
    uv run python scripts/generate_data.py --resolution high
```

Unlike Make, `just` needs no `.PHONY` declarations, and `just --list`
auto-generates its summary from the recipe names and the `#` doc-comment
directly above each recipe — no separate `help` target to maintain.

---

## Troubleshooting

**`just: command not found`**
Install `just` (see [Installing just](#installing-just) above).

**`uv: command not found`**
Install uv first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**`Error: No module named pytest`**
Run `just setup` to install dependencies before running tests.

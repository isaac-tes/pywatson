# Makefile Guide

Projects created with `pywatson init --project-type full` include a `Makefile`
with pre-configured targets for all common development tasks.
Run `make help` at any time to see a summary of available targets.

> **Note**: The `Makefile` is only generated for `--project-type full`.
> `default` and `minimal` projects do not include one.

---

## Quick reference

| Target | What it does |
|--------|-------------|
| `make help` | List all targets with descriptions |
| `make setup` | Install all dependencies (runs `uv sync`) |
| `make test` | Run the test suite |
| `make test-cov` | Run tests and show a coverage report |
| `make lint` | Check code with ruff |
| `make lint-fix` | Auto-fix ruff lint issues |
| `make format` | Format code with ruff |
| `make format-check` | Check formatting without modifying files |
| `make typecheck` | Run the configured type checker |
| `make check` | Run all quality gates (lint + format + typecheck + test) |
| `make data` | Execute `scripts/generate_data.py` |
| `make analyze` | Execute `scripts/analyze_data.py` |
| `make docs` | Build documentation (configure as needed) |
| `make build` | Build the distribution package |
| `make clean` | Remove build artefacts |

---

## Type checker integration

The `typecheck` target adapts to whichever type checker you chose when
creating the project:

```bash
# If you chose --type-checker ty (default):
make typecheck   # runs: uv run ty check src/<package>/

# If you chose --type-checker mypy:
make typecheck   # runs: uv run mypy src/<package>/

# If you chose --type-checker none:
make typecheck   # prints a notice and exits successfully
```

Similarly, `make check` omits the typecheck step when no type checker was
configured.

---

## Common workflows

### First-time setup

```bash
make setup       # creates .venv and installs all deps via uv sync
```

### Before committing

```bash
make check       # lint + format-check + typecheck + tests in one shot
```

### Run only tests

```bash
make test        # fast, no coverage
make test-cov    # with coverage report
```

### Fix formatting / lint issues

```bash
make format      # auto-format with ruff
make lint-fix    # auto-fix lint violations
```

### Run data pipeline

```bash
make data        # generate raw / simulated data
make analyze     # run analysis scripts
```

---

## Customising targets

The `Makefile` is plain GNU Make — edit it freely.  Add project-specific
targets at the end:

```makefile
# Example: run a specific simulation
sim-long: ## Run the long simulation (high resolution)
    uv run python scripts/generate_data.py --resolution high

.PHONY: sim-long
```

The `make help` output is generated automatically from `## comment` markers,
so any target with a `## description` will appear there.

---

## Troubleshooting

**`make: command not found`**  
Install GNU Make via your package manager:

```bash
# macOS
brew install make

# Ubuntu / Debian
sudo apt-get install make
```

**`uv: command not found`**  
Install uv first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**`Error: No module named pytest`**  
Run `make setup` to install dependencies before running tests.

# PyWatson CLI Reference

Complete reference for the `pywatson` command-line interface.

```
pywatson [--version] [--help] [--project-name NAME] [OPTIONS]
pywatson init
```

---

## `pywatson --project-name NAME` — scaffold a new project (non-interactive)

Creates a new Python scientific project non-interactively.
All parameters are passed as flags; if `--project-name` is omitted the help
text is shown.

```
pywatson --project-name NAME [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--project-name TEXT` | — | Name of the new project (required) |
| `--path`, `-p PATH` | `.` | Parent directory for the new project |
| `--author-name TEXT` | `git config user.name` | Author name (auto-filled from git) |
| `--author-email TEXT` | `git config user.email` | Author email (auto-filled from git) |
| `--description TEXT` | _(empty)_ | One-line project description |
| `--project-type`, `-t` | `default` | `default`, `minimal`, or `full` |
| `--license` | `MIT` | `MIT`, `BSD-3-Clause`, `Apache-2.0`, or `ISC` |
| `--python-version TEXT` | `3.12` | Target Python version |
| `--linting` | `minimal` | Ruff ruleset: `minimal` or `strict` |
| `--type-checker` | `ty` | Type checker: `ty`, `mypy`, or `none` |
| `--env-file PATH` | — | Import deps from a conda `environment.yml` |
| `--docker` | _(flag)_ | Add Docker + Zenodo reproducibility scaffolding |
| `--force` | _(flag)_ | Overwrite existing project directory |

### Project types

| Type | Use case | Extras |
|------|----------|--------|
| `default` | Standard scientific project | `data/{sims,exp_raw,exp_pro}`, `_research/`, `notebooks/`, `plots/` |
| `minimal` | Lightweight / tooling-only | `src/`, `data/`, `scripts/`, `tests/`, `docs/` |
| `full` | Publication-ready | Everything in `default` + `config/`, `Makefile`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`, `CHANGELOG.md` |

### Examples

```bash
# Minimal — git config auto-fills author info
pywatson --project-name my-analysis

# All flags up front
pywatson --project-name my-analysis \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Ising model Monte Carlo" \
  --project-type full \
  --license BSD-3-Clause \
  --linting strict

# Import conda dependencies
pywatson --project-name my-analysis --env-file environment.yml

# With Docker reproducibility scaffolding
pywatson --project-name my-analysis \
  --project-type full \
  --docker
```

### What gets created

A `pywatson` run creates a ready-to-use project:

```
my-analysis/
├── src/my_analysis/
│   ├── __init__.py          # Public API — all PyWatson helpers re-exported
│   └── core.py              # Your project-specific analysis code
├── scripts/
│   ├── generate_data.py
│   ├── analyze_data.py
│   └── pywatson_showcase.py # Interactive API demo
├── notebooks/
├── tests/
│   └── test_core.py
├── data/
│   ├── sims/
│   ├── exp_raw/
│   └── exp_pro/
├── plots/
├── _research/tmp/
├── pywatson_utils.py        # PyWatson utilities (fully self-contained copy)
├── pyproject.toml
├── ruff.toml
└── README.md
```

After scaffolding:

```bash
cd my-analysis
uv sync        # creates .venv and installs all deps
uv run pytest  # 2 tests should pass
```

---

## `pywatson status` — project dashboard

Shows an overview of the current project: root path, name, directory file
counts, data format totals, and git state.

```
pywatson status
```

No options.  Must be run from inside a PyWatson project (directory containing
`pyproject.toml` or `.git`).

### Example output

```
PyWatson project: /home/jane/my-analysis
  Name       : my-analysis

Directories:
  ✓ data           (12 files)
  ✓ plots          (3 files)
  ✓ scripts        (3 files)
  ✓ notebooks      (1 files)
  ✓ tests          (2 files)
  – _research

Data files:
  HDF5  (.h5) : 9
  NumPy (.npz): 2
  Zarr  (.zarr): 1

Git:
  Branch  : main
  Commit  : a3f9c1e
  Clean   : yes
```

---

## `pywatson sweep` — parameter-sweep filenames

Prints the `savename()`-generated filename for every combination of parameter
values (Cartesian product).  No files are written.

```
pywatson sweep [OPTIONS] KEY=VAL[,VAL...] ...
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--suffix TEXT` | `.h5` | File extension appended to each filename |
| `--connector TEXT` | `_` | Separator between `key=value` pairs |

### Examples

```bash
# Single parameter sweep
pywatson sweep N=100,500,1000
# 3 combinations:
#   N=100.h5
#   N=500.h5
#   N=1000.h5

# Two-parameter grid (6 combinations)
pywatson sweep alpha=0.1,0.5,1.0 N=100,1000 --suffix .h5
# 6 combinations:
#   N=100_alpha=0.1.h5
#   N=100_alpha=0.5.h5
#   N=100_alpha=1.0.h5
#   N=1000_alpha=0.1.h5
#   N=1000_alpha=0.5.h5
#   N=1000_alpha=1.0.h5

# Custom suffix and connector
pywatson sweep model=euler,rk4 dt=0.01,0.001 --suffix .npz --connector -
# 4 combinations:
#   dt=0.001-model=euler.npz
#   ...

# String values (no quoting needed)
pywatson sweep method=euler,rk4 N=100
```

The output matches exactly what `savename()` and `dict_list()` produce in
Python, making it easy to preview a parameter sweep before writing scripts.

---

## `pywatson summary` — data file overview

Lists all HDF5 files in the project's `data/` directory with their dataset
keys and creation timestamps.

```
pywatson summary [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--subdir TEXT` | — | Limit to `data/<subdir>/` |
| `--recursive` | `True` | Search subdirectories recursively |

### Examples

```bash
# Summarise all HDF5 files in data/
pywatson summary

# Only files in data/sims/
pywatson summary --subdir sims

# Top-level files only (no recursion)
pywatson summary --no-recursive
```

### Example output

```
3 file(s) found:
  data/sims/N=100_beta=0.44.h5
    created : 2025-03-09T10:12:34
    datasets: energy, magnetisation
  data/sims/N=1000_beta=0.44.h5
    created : 2025-03-09T10:12:37
    datasets: energy, magnetisation
  data/sims/N=10000_beta=0.44.h5
    created : 2025-03-09T10:12:51
    datasets: energy, magnetisation
```

---

*See also: [UTILITIES.md](UTILITIES.md) · [QUICKSTART.md](QUICKSTART.md) ·
[DOCKER_GUIDE.md](DOCKER_GUIDE.md) · [ZENODO.md](ZENODO.md)*

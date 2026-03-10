# PyWatson Quickstart Guide

This guide walks you through everything you need to go from zero to a fully
working reproducible scientific Python project in minutes.

> **See also**: [UTILITIES.md](UTILITIES.md) for the full API reference and
> [CLI.md](CLI.md) for the complete CLI reference.

---

## Table of Contents

1. [Installation](#installation)
2. [Creating Your First Project](#creating-your-first-project)
3. [Project Types](#project-types)
4. [Generated Project Structure](#generated-project-structure)
5. [Using the DrWatson Utilities](#using-the-drwatson-utilities)
   - [Path Management](#path-management)
   - [Parameter-Based Filenames](#parameter-based-filenames)
   - [Parameter Grid Expansion](#parameter-grid-expansion)
   - [Saving and Loading Data](#saving-and-loading-data)
   - [Smart Caching with `produce_or_load`](#smart-caching-with-produce_or_load)
   - [Git-Tagged Saves with `tagsave`](#git-tagged-saves-with-tagsave)
   - [Atomic and Temporary Saves](#atomic-and-temporary-saves)
   - [Collecting Results](#collecting-results)
   - [Reproducibility Helpers](#reproducibility-helpers)
6. [Typical Scientific Workflow](#typical-scientific-workflow)
7. [CLI Quick Reference](#cli-quick-reference)

---

## Installation

### Option A — Install as a global tool (no clone required, recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pywatson as a global tool from GitHub
uv tool install git+https://github.com/isaac-tes/pywatson.git

# Verify
pywatson --version
```

The `pywatson` command is now available everywhere on your machine.

### Option B — Install from PyPI (once published)

```bash
uv tool install pywatson
# or
pip install pywatson
```

### Option C — Developer / contributor clone

```bash
git clone https://github.com/isaac-tes/pywatson.git
cd pywatson
uv sync          # creates .venv and installs all deps including dev tools

# Now use the in-repo command
uv run pywatson --version
# or activate the venv
source .venv/bin/activate && pywatson --version
```

---

## Creating Your First Project

```bash
# Simplest invocation — prompts for author info and description
pywatson init my-analysis

# One-liner with all info up front
pywatson init my-analysis \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Spin-chain Monte Carlo study"

# Full project (adds CI, Makefile, CONTRIBUTING, CHANGELOG)
pywatson init my-analysis \
  --project-type full \
  --license BSD-3-Clause \
  --python-version 3.12 \
  --linting strict \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Spin-chain Monte Carlo study"

# Import dependencies from an existing conda environment.yml
pywatson init my-analysis --env-file environment.yml
```

After scaffolding, enter the project and finish setup:

```bash
cd my-analysis
uv sync          # install all dependencies into .venv
uv run pytest    # confirm tests pass (should be 2/2 green)
```

### Legacy / backward-compatible alias

`pywatson-init` is still fully supported as a drop-in alias:

```bash
pywatson-init my-analysis --author-name "Jane" --author-email "jane@uni.edu"
```

---

## Project Types

| Type | Use case | Extras |
|------|----------|--------|
| `default` | Standard scientific project | `data/{sims,exp_raw,exp_pro}`, `_research/`, `notebooks/`, `plots/` |
| `minimal` | Lightweight / tooling-only | `src/`, `data/`, `scripts/`, `tests/`, `docs/` (no notebooks, no _research) |
| `full` | Publication-ready repository | Everything in `default` + `config/`, `Makefile`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`, `CHANGELOG.md` |

---

## Generated Project Structure

```
my-analysis/
├── src/my_analysis/
│   ├── __init__.py         # Public API — re-exports DrWatson utilities
│   └── core.py             # Your project-specific analysis functions
├── scripts/
│   ├── generate_data.py    # Example data generation script
│   ├── analyze_data.py     # Example analysis workflow
│   └── pywatson_showcase.py  # Interactive API demo
├── notebooks/              # Jupyter notebooks
├── tests/
│   └── test_core.py        # pytest test suite
├── data/
│   ├── sims/               # Simulation outputs (HDF5 by default)
│   ├── exp_raw/            # Raw experimental data  [default type]
│   └── exp_pro/            # Processed data         [default type]
├── plots/                  # Generated figures
├── _research/              # WIP scripts & scratch work (not committed by default)
│   └── tmp/                # Temporary files (git-ignored)
├── docs/                   # Documentation
├── pywatson_utils.py       # Copied DrWatson utilities (editable in-project)
├── pyproject.toml
├── ruff.toml
├── LICENSE
└── README.md
```

> **Note**: The file `pywatson_utils.py` is copied verbatim from pywatson's
> `src/pywatson/utils.py` into each generated project, so projects are
> fully self-contained and do not depend on pywatson at runtime.

---

## Using the DrWatson Utilities

All generated projects expose the DrWatson utilities through the package
`__init__.py`. Import them as:

```python
from my_analysis import (
    datadir, plotsdir, scriptsdir, notebooksdir,
    savename, save_data, load_data, load_selective,
    tagsave, produce_or_load, collect_results,
)
```

### Path Management

PyWatson functions find the project root automatically by walking up the
directory tree until they find `pyproject.toml` (or `.git`). This means
they work correctly regardless of which subdirectory your script runs in.

```python
from my_analysis import datadir, plotsdir, scriptsdir, notebooksdir, srcdir

# Always returns the absolute path — works from any subdirectory
datadir()                      # Path(".../my-analysis/data")
datadir("sims")                # Path(".../my-analysis/data/sims")
datadir("sims/run_001")        # Path(".../my-analysis/data/sims/run_001")

plotsdir()                     # Path(".../my-analysis/plots")
plotsdir("figures", "final")   # Path(".../my-analysis/plots/figures/final")

scriptsdir()                   # Path(".../my-analysis/scripts")
notebooksdir()                 # Path(".../my-analysis/notebooks")
srcdir()                       # Path(".../my-analysis/src")

# Convenience file helpers
from my_analysis import datafile, plotfile
datafile("results", "experiment.h5")  # Path(".../data/results/experiment.h5")
plotfile("figure1.pdf")               # Path(".../plots/figure1.pdf")
```

### Parameter-Based Filenames

`savename` creates deterministic, human-readable filenames from a dictionary
of parameters. Keys are sorted alphabetically, so the filename is stable
across runs.

```python
from my_analysis import savename, parse_savename

params = {"alpha": 0.5, "N": 100, "method": "rk4", "dt": 0.01}
savename(params)              # "N=100_alpha=0.5_dt=0.01_method=rk4"
savename(params, "h5")        # "N=100_alpha=0.5_dt=0.01_method=rk4.h5"
savename(params, "h5", prefix="run")  # "run_N=100_alpha=0.5_dt=0.01_method=rk4.h5"

# Combine with datadir for a full path
filepath = datadir("sims") / savename(params, "h5")

# Parse a filename back to a parameter dict
parse_savename("N=100_alpha=0.5_method=rk4.h5")
# -> {"N": 100, "alpha": 0.5, "method": "rk4"}
```

---

### Parameter Grid Expansion

`dict_list` expands a dictionary of parameter lists into all Cartesian-product
combinations — equivalent to DrWatson.jl's `dict_list`.

```python
from my_analysis import dict_list, savename

all_params = dict_list({"alpha": [0.1, 0.5, 1.0], "N": [100, 1000]})
# -> 6 dicts: {"alpha": 0.1, "N": 100}, {"alpha": 0.1, "N": 1000}, ...

for p in all_params:
    data = run_simulation(p)
    save_data(data, savename(p), subdir="sims")
```

From the command line, `pywatson sweep` prints the same filenames without
writing any code:

```bash
pywatson sweep alpha=0.1,0.5,1.0 N=100,1000 --suffix .h5
# 6 combinations:
#   N=100_alpha=0.1.h5
#   N=100_alpha=0.5.h5
#   ...
```

### Saving and Loading Data

```python
import numpy as np
from my_analysis import save_data, load_data, load_selective, list_data_files
from my_analysis import save_npz, load_npz

# --- HDF5 Save ---
data = {
    "time": np.linspace(0, 10, 1000),
    "signal": np.sin(np.linspace(0, 10, 1000)),
}
metadata = {"sensor": "A", "gain": 2.0, "notes": "baseline run"}

save_data(data, "experiment_001", metadata=metadata)
# Saves to: data/experiment_001.h5

# Save into a subdirectory
save_data(data, "baseline", subdir="sims/run_001", metadata=metadata)
# Saves to: data/sims/run_001/baseline.h5

# --- NumPy NPZ ---
save_npz(data, "experiment_001", metadata=metadata)
# Saves to: data/experiment_001.npz
npz_result = load_npz("experiment_001")

# --- HDF5 Load ---
result = load_data("experiment_001")
result["time"]        # numpy array
result["signal"]      # numpy array
result["_metadata"]   # dict: {"sensor": "A", "gain": 2.0, ..., "timestamp": ...}

# Load only specific datasets (efficient for large files)
partial = load_selective("experiment_001", keys=["signal"])

# List all .h5 files in data/
for path in list_data_files():
    print(path)
```

### Smart Caching with `produce_or_load`

`produce_or_load` is the centrepiece of reproducible workflows.  It calls
your function **the first time** and saves the result; on subsequent calls
with the **same parameters** it skips the computation and loads from disk.

```python
import numpy as np
from my_analysis import produce_or_load, savename

def run_simulation(params: dict) -> dict:
    """Expensive Monte Carlo simulation."""
    N = params["N"]
    beta = params["beta"]
    # ... thousands of iterations ...
    energy = np.random.randn(N)   # placeholder
    return {"energy": energy, "magnetisation": energy.mean()}

params = {"N": 10_000, "beta": 0.44, "seed": 42}
filename = savename(params)   # "N=10000_beta=0.44_seed=42.h5"

# First call: runs simulation, saves result automatically
data, filepath = produce_or_load(filename, run_simulation, params)
print(f"Saved to: {filepath}")

# Second call: loads from disk — simulation is NOT re-run
data, filepath = produce_or_load(filename, run_simulation, params)
print(f"Loaded from: {filepath}")   # same path

# Use a custom subfolder
data, filepath = produce_or_load(filename, run_simulation, params,
                                  subdir="sims/ising")

# The file path will be: data/sims/ising/N=10000_beta=0.44_seed=42.h5
```

### Git-Tagged Saves with `tagsave`

`tagsave` wraps `save_data` and automatically embeds the current git commit
hash, branch, and dirty status into the saved metadata. Use it for any data
you want to be able to trace back to a specific version of your code.

```python
from my_analysis import tagsave

data = {"result": computed_array}
tagsave("final_result", data, tags={"run_id": "exp_42"})

# Metadata will include:
# {
#   "gitcommit": "a3f9c1e",
#   "gitbranch": "main",
#   "gitpatch": False,
#   "run_id": "exp_42",
#   "created_at": "2025-03-09T10:00:00"
# }
```

### Atomic and Temporary Saves

`safesave` writes atomically: it creates a `.tmp.h5` sibling first, then
renames it into place. Your data is never half-written on disk.

```python
from my_analysis import safesave, tmpsave

# Atomic save — safe on crash/power failure
safesave("run_001", data, metadata={"run": 1}, subdir="sims")

# Temporary file — deleted automatically when the block exits
with tmpsave(data) as tmp_path:
    process_file(tmp_path)   # file exists only inside this block
```

---

### Collecting Results

`collect_results` loads all HDF5 files from a directory into a list of dicts
or a pandas DataFrame — one row per file.

```python
from my_analysis import collect_results

# List of dicts (default)
rows = collect_results(subdir="sims")

# pandas DataFrame (one row per file, metadata columns prefixed _meta_)
df = collect_results(subdir="sims", as_dataframe=True)
print(df.head())
#     N  beta  seed  energy_mean  ...  _filepath
# 0  1000  0.3  42   -0.152  ...  data/sims/...

# Filter by parameter values
high_beta = df[df["beta"] > 0.4]
```

---

### Reproducibility Helpers

```python
from my_analysis import snapshot_environment, set_random_seed

# Capture full environment (Python version + all installed packages)
env = snapshot_environment()
# -> {"python_version": "3.12.9", "platform": "...", "packages": [...], "captured_at": "..."}

# Set seeds for numpy, random, and torch (if available) — returns metadata dict
seed_meta = set_random_seed(42)
# -> {"random_seed": 42}

# Embed both in your saved data
save_data(
    data,
    "reproducible_run",
    metadata={**seed_meta, "environment": env},
)
```

---

## Typical Scientific Workflow

Below is an end-to-end example that strings everything together.

### 1 — Generate and save raw data

```python
# scripts/generate_data.py
import numpy as np
from my_analysis import savename, save_data

PARAMS = [
    {"N": 1000, "beta": 0.3, "seed": 0},
    {"N": 1000, "beta": 0.44, "seed": 0},
    {"N": 1000, "beta": 0.6, "seed": 0},
]

for p in PARAMS:
    rng = np.random.default_rng(p["seed"])
    energy = rng.normal(loc=-p["beta"], scale=1.0, size=p["N"])
    data = {"energy": energy}
    filename = savename(p)
    save_data(data, filename, subdir="sims/ising", metadata=p, include_git=True)
    print(f"Saved {filename}")
```

### 2 — Analyse with smart caching

```python
# scripts/analyze_data.py
import numpy as np
from my_analysis import produce_or_load, collect_results

def compute_statistics(params: dict) -> dict:
    """Load raw data and compute summary statistics."""
    from my_analysis import load_data, savename
    raw = load_data("sims/ising/" + savename(params))   # include subdir in path
    energy = raw["energy"]
    return {
        "mean_energy": np.array([energy.mean()]),
        "std_energy": np.array([energy.std()]),
        "N": np.array([params["N"]]),
        "beta": np.array([params["beta"]]),
    }

params = {"N": 1000, "beta": 0.44, "seed": 0}
filename = savename(params)
results, path = produce_or_load(filename, compute_statistics, params,
                                subdir="sims/stats")
print(f"Saved to {path}")
```

### 3 — Collect and plot

```python
# scripts/plot_results.py
import matplotlib.pyplot as plt
from my_analysis import collect_results, plotfile

df = collect_results(subdir="sims/stats", as_dataframe=True)
df = df.sort_values("beta")

fig, ax = plt.subplots()
ax.errorbar(df["beta"], df["mean_energy"], yerr=df["std_energy"], fmt="o-")
ax.set_xlabel("β (inverse temperature)")
ax.set_ylabel("⟨E⟩")
ax.set_title("Energy vs. temperature")
fig.savefig(plotfile("energy_vs_beta.pdf"))
print("Plot saved.")
```

---

## CLI Quick Reference

```
pywatson [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  init     Create a new Python project with modern tooling and best practices.
  status   Show an overview of the current PyWatson project.
  sweep    Print filenames for a parameter sweep.
  summary  Summarise HDF5 data files in the project data directory.
```

```
pywatson init [OPTIONS] PROJECT_NAME

Options:
  -p, --path PATH                  Directory to create the project in.  [default: .]
  --author-name TEXT               Author name.  [default: git config user.name]
  --author-email TEXT              Author email.  [default: git config user.email]
  --description TEXT               Short project description.
  -t, --project-type [default|minimal|full]
                                   Project structure type.  [default: default]
  --license [MIT|BSD-3-Clause|Apache-2.0|ISC]
                                   License for the generated project.  [default: MIT]
  --python-version TEXT            Target Python version (e.g. 3.11, 3.12).  [default: 3.12]
  --linting [minimal|strict]       Ruff ruleset.  [default: minimal]
  --type-checker [ty|mypy|none]    Type checker for the generated project.  [default: ty]
  --env-file PATH                  environment.yml to import dependencies from.
  --force                          Overwrite existing directory.
  --help                           Show this message and exit.
```

```
pywatson sweep [OPTIONS] KEY=VAL[,VAL...] ...

Options:
  --suffix TEXT     File suffix.  [default: .h5]
  --connector TEXT  Connector between key=value pairs.  [default: _]
  --help            Show this message and exit.
```

```
pywatson summary [OPTIONS]

Options:
  --subdir TEXT  Subdirectory within data/ to summarise.
  --recursive    Search recursively.  [default: True]
  --help         Show this message and exit.
```

---

*Generated by [PyWatson](https://github.com/isaac-tes/pywatson).*

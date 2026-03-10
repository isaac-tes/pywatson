# 🔬 PyWatson

**A Python scientific project management tool inspired by [DrWatson.jl](https://github.com/JuliaDynamics/DrWatson.jl)**

[![CI](https://github.com/isaac-tes/pywatson/actions/workflows/ci.yml/badge.svg)](https://github.com/isaac-tes/pywatson/actions/workflows/ci.yml)
[![Docs](https://github.com/isaac-tes/pywatson/actions/workflows/docs.yml/badge.svg)](https://isaac-tes.github.io/pywatson/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/isaac-tes/pywatson/blob/main/LICENSE)

PyWatson scaffolds well-structured, reproducible scientific computing projects with modern Python tooling — then provides DrWatson-inspired helpers for path management, smart caching, HDF5/Zarr data, and parameter-based filenames.

---

## ✨ Features

- 🗂️ **Project scaffolding** — one command creates a fully-wired research project
- 📦 **Adopt existing projects** — scan & migrate unstructured code into the pywatson layout
- 🔁 **Smart caching** — `produce_or_load()` skips recomputation when results already exist
- 🏷️ **Named results** — `savename()` builds deterministic filenames from parameter dicts
- 💾 **Multi-format IO** — HDF5, Zarr, CSV, JSON with git-state metadata
- 🔍 **Path helpers** — `datadir()`, `plotsdir()`, `scriptsdir()` rooted at project automatically
- 🐳 **Docker-ready** — generated projects include a working `Dockerfile`
- 🧪 **Test-first** — 280+ tests, pytest + ruff + mypy in CI

---

## 🚀 Quick Install

=== "from PyPI (coming soon)"

    ```bash
    pip install pywatson
    # or with uv (recommended)
    uv add pywatson
    ```

=== "from source"

    ```bash
    git clone https://github.com/isaac-tes/pywatson.git
    cd pywatson
    uv sync
    ```

---

## ⚡ Quick Start

```bash
# Create a new research project
pywatson init my_research --author-name "Your Name" --author-email "you@example.com"

cd my_research
uv sync        # install all generated project dependencies
uv run pytest  # verify everything works
```

Or adopt an existing project:

```bash
pywatson adopt /path/to/existing/project --output-path /path/to/destination
```

See [Getting Started](QUICKSTART.md) for a full walkthrough, or [Adopt Guide](ADOPT_GUIDE.md) for migrating existing projects.

---

## 📁 Generated Project Layout

```
my_research/
├── src/my_research/       # Package source (src-layout)
│   ├── core.py            # Experiment logic
│   └── pywatson_utils.py  # DrWatson helpers (pre-wired)
├── scripts/               # Standalone analysis scripts
│   ├── generate_data.py
│   └── analyze_data.py
├── notebooks/             # Jupyter notebooks
├── data/                  # Raw + processed data (git-ignored)
├── plots/                 # Figures (git-ignored)
├── tests/                 # pytest test suite
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 📖 Documentation

| Section | Description |
|---|---|
| [Getting Started](QUICKSTART.md) | Install, create a project, run your first experiment |
| [Adopt Guide](ADOPT_GUIDE.md) | Migrate an existing project into pywatson structure |
| [CLI Reference](CLI.md) | All `pywatson` commands and flags |
| [Utilities Reference](UTILITIES.md) | `pywatson_utils.py` API — path helpers, IO, caching |
| [API Reference](api/index.md) | Auto-generated from source docstrings |

---

## Citation

If you use PyWatson in published research, please see [Zenodo & Citation](ZENODO.md).

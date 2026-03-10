# 🔬 PyWatson

A Python scientific project management tool inspired by
[DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/).
Scaffolds reproducible scientific projects with modern Python tooling
([uv](https://docs.astral.sh/uv/) + pytest + ruff) and DrWatson-style
path management, HDF5 data handling, and smart caching.

## ✨ Features

- 📁 **Project scaffolding** — three types (default, minimal, full) with
  DrWatson.jl directory layout; author info auto-filled from `git config`
- 🔧 **Modern tooling** — [uv](https://docs.astral.sh/uv/) package manager,
  ruff for linting, pytest pre-configured
- 💾 **Multiple data formats** — HDF5, NumPy NPZ, Zarr via unified `save_*/load_*` API
- 📝 **Parameter naming** — `savename()`/`parse_savename()` for reproducible
  filenames from parameter dicts
- 📊 **Parameter grids** — `dict_list()` → Cartesian products;
  `pywatson sweep` previews without code
- ⚡ **Smart caching** — `produce_or_load()` skips recomputation; returns Path
- 🛡️ **Atomic saves** — `safesave()` (crash-safe) + `tmpsave()` (auto-cleanup)
- 📈 **Result aggregation** — `collect_results()` → pandas DataFrame
- 🎯 **Reproducibility** — `snapshot_environment()`, `set_random_seed()`
- 📊 **Dashboard** — `pywatson status` shows dirs, data, git state
- 📦 **Adopt existing** — `pywatson adopt` scans & reorganizes messy projects
  (see [docs/ADOPT_GUIDE.md](docs/ADOPT_GUIDE.md))
- 🐳 **Docker & Zenodo** — `--docker` adds reproducibility bundle
  (see [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md))

## 🚀 Quick Start

### Install

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pywatson
uv tool install git+https://github.com/isaac-tes/pywatson.git
```

### Create a project

```bash
pywatson init my-analysis \
  --author-name "Jane Doe" --author-email "jane@uni.edu" \
  --description "My research"

cd my-analysis
uv sync        # install dependencies
uv run pytest  # run tests
```

### Adopt an existing project

```bash
pywatson adopt /path/to/messy-code \
  --author-name "Jane" --author-email "jane@uni.edu"
# Scans, classifies files, organizes into pywatson structure
```

See [docs/ADOPT_GUIDE.md](docs/ADOPT_GUIDE.md) for details.

## 📚 uv Essentials

For complete docs: [uv documentation](https://docs.astral.sh/uv/)

| Command | Purpose |
|---------|---------|
| `uv sync` | Install all dependencies (create/update `.venv`) |
| `uv run pytest` | Run tests in project environment |
| `uv add PACKAGE` | Add a dependency |
| `uv remove PACKAGE` | Remove a dependency |
| `uv pip list` | List installed packages |
| `uv tool install TOOL` | Install CLI tool globally |

> **Developer workflow**: Clone repo → `uv sync` → `uv run pywatson` instead of `pywatson`


## 📂 Project Types

| Type | Best for | Includes |
|------|----------|----------|
| `default` | Standard research | data/{sims,exp_raw,exp_pro}, notebooks, _research |
| `minimal` | Lightweight | src, data, scripts, tests, docs |
| `full` | Publication-ready | everything + config, Makefile, CI, docs |

### Default project structure

```
my-project/
├── src/my_project/
│   ├── __init__.py         # Public API (DrWatson helpers re-exported)
│   ├── core.py             # Your analysis code
│   └── pywatson_utils.py   # Self-contained DrWatson utilities
├── scripts/
│   ├── generate_data.py
│   └── analyze_data.py
├── notebooks/
├── tests/
├── data/
│   ├── sims/
│   ├── exp_raw/
│   └── exp_pro/
├── plots/
├── _research/tmp/
├── pyproject.toml
└── README.md
```

> `pywatson_utils.py` is copied verbatim into every generated project so
> projects are **fully self-contained** and do not depend on pywatson at
> runtime.

## Usage at a Glance

```python
from my_project import (
    datadir, savename, parse_savename, dict_list,
    save_data, load_data, tagsave, produce_or_load,
    collect_results, snapshot_environment, set_random_seed,
)

# Paths (work from any subdirectory)
datadir("sims")                       # Path(".../data/sims")

# Parameter filenames
params = {"N": 1000, "beta": 0.44}
savename(params)                      # "N=1000_beta=0.44.h5"
parse_savename("N=1000_beta=0.44.h5") # {"N": 1000, "beta": 0.44}

# Parameter grid → Cartesian product
for p in dict_list({"N": [100, 1000], "beta": [0.3, 0.44]}):
    save_data(run(p), savename(p), subdir="sims")

# Smart caching — run once, load thereafter
data, path = produce_or_load(savename(params), run_simulation, **params)

# Aggregate all results into a DataFrame
df = collect_results(subdir="sims", as_dataframe=True)
```

For the complete API, see [docs/UTILITIES.md](docs/UTILITIES.md).

## 💻 CLI

```bash
pywatson init PROJ_NAME          # create new project
pywatson adopt /path/to/code     # adopt existing project
pywatson status                  # dashboard (dirs, data, git)
pywatson sweep K=V1,V2 ...      # preview parameter-sweep names
pywatson summary                 # list HDF5 files + keys
```

Full reference: [docs/CLI.md](docs/CLI.md)

## 📖 Documentation

| Guide | What |
|-------|------|
| [QUICKSTART.md](docs/QUICKSTART.md) | End-to-end workflow |
| [UTILITIES.md](docs/UTILITIES.md) | API reference |
| [CLI.md](docs/CLI.md) | CLI commands |
| [ADOPT_GUIDE.md](docs/ADOPT_GUIDE.md) | Adopting existing projects |
| [DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) | Docker reproducibility |
| [ZENODO.md](docs/ZENODO.md) | Zenodo deposit |

## 🛠️ Development

```bash
uv sync                          # install + dev deps
uv run pytest                    # run all tests
uv run ruff check src/ tests/    # lint
uv run ruff format src/ tests/   # format
uv build                         # package
```

### Architecture

| Component | Description |
|-----------|-------------|
| `src/pywatson/core.py` | `ProjectScaffolder` + Click CLI |
| `src/pywatson/utils.py` | DrWatson utilities (copied into generated projects) |
| `src/pywatson/templates/` | Jinja2 templates for generated project files |
| `tests/` | pytest suite (220+ tests) |

## 🔄 vs DrWatson.jl

| Feature | DrWatson.jl | PyWatson |
|---------|-------------|----------|
| Language | Julia | Python 3.12+ |
| Package manager | Pkg.jl | uv |
| Project templates | 1 | 3 (default, minimal, full) |
| Adopt existing projects | — | ✅ |
| Parameter naming | savename | savename + parse_savename |
| Smart caching | produce_or_load | produce_or_load (+ returns Path) |
| Data formats | HDF5 | HDF5 + NPZ + Zarr + pandas |
| Atomic saves | — | safesave + tmpsave |
| Collect results | collect_results | collect_results → DataFrame |
| Docker integration | — | ✅ |
| Zenodo integration | — | ✅ |

## 📄 License

MIT — see [LICENSE](LICENSE).

## 🙏 Built with

- [DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/) (inspiration)
- [uv](https://docs.astral.sh/uv/) (package management)
- [Click](https://click.palletsprojects.com/) (CLI)
- [Rich](https://rich.readthedocs.io/) (terminal UI)

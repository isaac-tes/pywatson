# PyWatson

A Python scientific project management tool inspired by
[DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/).
Scaffolds reproducible scientific computing projects with modern Python
tooling and DrWatson.jl-style path management, HDF5 data handling, and smart
caching.

## Features

- **Project scaffolding** — three types (default, minimal, full) with
  DrWatson.jl-style directory layout; author info auto-filled from `git config`
- **Modern tooling** — [uv](https://docs.astral.sh/uv/) for dependency
  management; ruff for linting; pytest pre-configured
- **Multiple data formats** — HDF5 (`.h5`), NumPy compressed (`.npz`), Zarr
  (`.zarr`) via a unified `save_*/load_*` API
- **Parameter-based naming** — `savename()` / `parse_savename()` generate and
  parse reproducible filenames from parameter dicts
- **Parameter grids** — `dict_list()` expands Cartesian products;
  `pywatson sweep` previews filenames without writing code
- **Smart caching** — `produce_or_load()` skips recomputation when results
  already exist; returns the cache `Path`
- **Atomic / temp saves** — `safesave()` (crash-safe rename) and `tmpsave()`
  (auto-deleted context manager)
- **Collect results** — `collect_results()` aggregates all data files into a
  pandas DataFrame
- **Reproducibility helpers** — `snapshot_environment()`, `set_random_seed()`
- **Project dashboard** — `pywatson status` shows dirs, data counts, git state
- **Docker & Zenodo** — `--docker` flag adds a self-contained reproducibility
  bundle (see [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md))

## Quick Start

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pywatson as a global tool
uv tool install git+https://github.com/isaac-tes/pywatson.git

# Scaffold a new project (author info auto-filled from git config)
pywatson init my-analysis \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Ising model Monte Carlo"

cd my-analysis
uv sync        # install dependencies
uv run pytest  # run the test suite
```

> **Developer / clone workflow**: `git clone … && uv sync` then use
> `uv run pywatson` instead of `pywatson`.

## Project Types

| Type | Use case | Extras |
|------|----------|--------|
| `default` | Standard scientific project | `data/{sims,exp_raw,exp_pro}`, `_research/`, `notebooks/`, `plots/` |
| `minimal` | Lightweight / tooling only | `src/`, `data/`, `scripts/`, `tests/`, `docs/` |
| `full` | Publication-ready | Everything in `default` + `config/`, `Makefile`, CI workflow, `CONTRIBUTING.md`, `CHANGELOG.md` |

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

## CLI

```
pywatson init    PROJECT_NAME   # scaffold a new project
pywatson status                 # project dashboard
pywatson sweep   KEY=V1,V2 ...  # preview parameter-sweep filenames
pywatson summary                # list HDF5 files + keys
```

Full reference: [docs/CLI.md](docs/CLI.md).

## Documentation

| Guide | Contents |
|-------|----------|
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | End-to-end scientific workflow walkthrough |
| [docs/UTILITIES.md](docs/UTILITIES.md) | Complete API reference |
| [docs/CLI.md](docs/CLI.md) | Full CLI reference |
| [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) | Docker reproducibility guide |
| [docs/ZENODO.md](docs/ZENODO.md) | Zenodo deposit guide |

## Development

```bash
uv run pytest               # run all tests
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Architecture

| Component | Description |
|-----------|-------------|
| `src/pywatson/core.py` | `ProjectScaffolder` + Click CLI |
| `src/pywatson/utils.py` | DrWatson utilities (copied into generated projects) |
| `src/pywatson/templates/` | Jinja2 templates for generated project files |
| `tests/` | pytest suite (220+ tests) |

## Comparison with DrWatson.jl

| Feature | DrWatson.jl | PyWatson |
|---------|-------------|----------|
| Package manager | Pkg.jl | uv |
| Project structure | Yes | Yes (3 types) |
| Parameter naming | `savename` | `savename` + `parse_savename` |
| Parameter grids | `dict_list` | `dict_list` |
| Smart caching | `produce_or_load` | `produce_or_load` (returns Path) |
| Collect results | `collect_results` | `collect_results` (→ DataFrame) |
| Git integration | Yes | Yes |
| Path management | Yes | Yes |
| HDF5 support | Yes | Yes |
| NumPy NPZ | -- | Yes |
| Zarr | -- | Yes |
| pandas DataFrame in HDF5 | -- | Yes |
| Atomic saves | -- | `safesave` |
| Temp-file context | -- | `tmpsave` |
| Environment snapshot | -- | `snapshot_environment` |
| Random seed management | -- | `set_random_seed` |
| Project dashboard CLI | -- | `pywatson status` |
| Sweep preview CLI | -- | `pywatson sweep` |
| Data summary CLI | -- | `pywatson summary` |
| License selection | -- | Yes |
| CI generation | -- | Yes (full type) |
| Docker reproducibility | -- | Yes (`--docker`) |
| Docker guide | -- | [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) |
| Zenodo guide | -- | [docs/ZENODO.md](docs/ZENODO.md) |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- Inspired by [DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/)
- Built with [uv](https://docs.astral.sh/uv/), [Click](https://click.palletsprojects.com/), and [Rich](https://rich.readthedocs.io/)

# PyWatson

A Python scientific project management tool inspired by
[DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/) for
creating well-structured, reproducible scientific computing projects with
modern Python tooling.

## Features

- **Complete Project Structure** -- Three project types (default, minimal,
  full) with DrWatson.jl-style data directories
- **Modern Tooling** -- Uses [uv](https://docs.astral.sh/uv/) for fast
  dependency management and virtual environments
- **HDF5 Data Management** -- Built-in support for saving/loading scientific
  data with h5py, automatic git tracking, and metadata
- **Smart Caching** -- `produce_or_load()` skips expensive recomputation when
  results already exist on disk
- **Parameter-Based Naming** -- `savename()` generates consistent filenames
  from parameter dictionaries
- **Path Management** -- Project-aware directory functions that work from
  anywhere in your project tree
- **Git Integration** -- Automatic git commit info embedded in saved data
- **License Selection** -- Choose MIT, BSD-3-Clause, Apache-2.0, or ISC at
  project creation time
- **Docker & Zenodo Reproducibility** -- `--docker` flag scaffolds a
  `Dockerfile`, `docker-compose.yml`, and a GitHub Actions publish workflow so
  readers can reproduce your results with a single `docker compose run reproduce`
  after downloading data from Zenodo

## Quick Start

```bash
# Install pywatson as a global tool (no clone required)
uv tool install git+https://github.com/isaac-tes/pywatson.git

# Scaffold a new project
pywatson init my-analysis \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "My analysis project"

# Enter the project and start working
cd my-analysis
uv sync            # install all dependencies
uv run pytest      # run the test suite
```

> **Detailed guide** — see [docs/QUICKSTART.md](docs/QUICKSTART.md) for full
> installation options (including dev/clone workflow), all project types,
> CLI flags, and an end-to-end scientific workflow walkthrough.

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install (dev / clone workflow)

```bash
git clone https://github.com/isaac-tes/pywatson.git
cd pywatson
uv sync
```

### Create a Project

```bash
# Recommended: new `pywatson` CLI
pywatson init my-analysis

# Legacy alias (still supported)
pywatson-init my-analysis

# Interactive mode via the bash helper
./create-project.sh -i

# Full control — all flags
pywatson init my-project \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Quantum spin chain simulations" \
  --project-type full \
  --license Apache-2.0

# With Docker + Zenodo reproducibility scaffolding
pywatson init my-project \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --project-type full \
  --docker
```

### Start Working

```bash
cd my-project
uv sync                                    # Install dependencies
uv run pytest                              # Run tests
uv run python scripts/generate_data.py     # Generate example data
uv run python scripts/analyze_data.py      # Run analysis
```

## Project Types

| Type | Description | Directories |
|------|-------------|-------------|
| **default** | DrWatson.jl standard | `data/{sims, exp_raw, exp_pro}`, `_research/`, `notebooks/`, `plots/` |
| **minimal** | Lightweight | `src/`, `data/`, `scripts/`, `tests/`, `docs/` |
| **full** | Everything + CI/tools | All of default + `config/`, `Makefile`, `.github/workflows/`, `CONTRIBUTING.md`, `CHANGELOG.md` |

### Default Project Structure

```
my-project/
├── src/my_project/
│   ├── __init__.py         # Public API (DrWatson functions re-exported)
│   ├── core.py             # Project-specific analysis functions
│   └── pywatson_utils.py   # Path management & HDF5 data utilities
├── scripts/
│   ├── generate_data.py    # Example data generation
│   └── analyze_data.py     # Example analysis workflow
├── notebooks/              # Jupyter notebooks
├── tests/                  # pytest test suite
├── data/
│   ├── sims/               # Simulation output
│   ├── exp_raw/            # Raw experimental data
│   └── exp_pro/            # Processed experimental data
├── plots/                  # Generated figures
├── _research/              # WIP scripts & scratch work
│   └── tmp/                # Temporary files (git-ignored)
├── docs/                   # Documentation
├── LICENSE
├── pyproject.toml
└── README.md
```

## CLI Reference

```
pywatson [--version] [--help]
pywatson init [OPTIONS] PROJECT_NAME
```

`pywatson-init PROJECT_NAME` is a backward-compatible alias for `pywatson init`.

| Option | Default | Description |
|--------|---------|-------------|
| `--path`, `-p` | `.` | Directory to create the project in |
| `--author-name` | (prompted) | Author name |
| `--author-email` | (prompted) | Author email |
| `--description` | (prompted) | Short project description |
| `--project-type`, `-t` | `default` | `default`, `minimal`, or `full` |
| `--license` | `MIT` | `MIT`, `BSD-3-Clause`, `Apache-2.0`, or `ISC` |
| `--env-file` | | Import dependencies from environment.yml |
| `--docker` | | Scaffold Docker + Zenodo reproducibility files |
| `--force` | | Overwrite existing directory |

## Docker & Zenodo Reproducibility

Pass `--docker` to any `pywatson init` invocation to scaffold a fully
reproducible Docker environment alongside the standard project files.

### What gets added

| File | Purpose |
|------|---------|
| `Dockerfile` | Slim Python image, installs uv, runs `analyze_data.py` |
| `.dockerignore` | Excludes `data/`, `plots/`, `.git/` from the image |
| `docker-compose.yml` | `reproduce` service (mounts data ro, plots rw); `shell` service for debugging |
| `README_DOCKER.md` | Reader-facing instructions: pull image → download Zenodo data → run |
| `.github/workflows/docker-publish.yml` | CI: build → smoke-test → push to GHCR on every tag (`full` type only) |

### Reader reproduction workflow

```bash
# 1. Pull the published image
docker pull ghcr.io/YOUR_GITHUB_USERNAME/my-project:latest

# 2. Download the data archive from the Zenodo DOI in README_DOCKER.md
#    and unpack into ./data/

# 3. Run the full analysis pipeline
docker compose run reproduce
# → plots appear in ./plots/
```

> **New to Docker?** — see [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md) for
> a plain-language introduction: what Docker is, how to install it on
> macOS/Linux/Windows, how the generated files work, and a cheat sheet of
> the commands you'll actually use.
>
> **Zenodo deposit** — see [docs/ZENODO.md](docs/ZENODO.md) for step-by-step
> instructions on depositing code and data on Zenodo, linking DOIs, and the
> pre-paper reproducibility checklist.

## DrWatson-Style Workflow

Generated projects include `pywatson_utils.py` which provides these utilities:

```python
from my_project import (
    datadir, plotsdir, savename,
    save_data, load_data, load_selective,
    tagsave, produce_or_load,
)

# Path management (always relative to project root)
datadir()                        # -> Path("<project>/data")
plotsdir("figures")              # -> Path("<project>/plots/figures")

# Parameter-based filenames
params = {"alpha": 0.5, "N": 100, "method": "euler"}
savename(params, "h5")           # -> "N=100_alpha=0.5_method=euler.h5"

# Save data with automatic metadata and git info
import numpy as np
data = {"temperature": np.random.randn(1000)}
save_data(data, "experiment_001", metadata={"sensor": "A"})

# Load data
result = load_data("experiment_001")
result["temperature"]            # numpy array
result["_metadata"]              # dict with git commit, timestamp, custom fields

# Load only specific datasets
partial = load_selective("experiment_001", keys=["temperature"])

# Smart caching -- run once, load thereafter
def expensive_simulation(params):
    # ... your simulation code ...
    return {"result": computed_data}

data, filepath = produce_or_load(expensive_simulation, {"N": 1000, "dt": 0.01})
```

## Environment File Support

You can import dependencies from a conda-style `environment.yml`:

```yaml
name: my-project
dependencies:
  - numpy>=1.24.0
  - pandas>=2.0.0
  - scikit-learn>=1.3.0
  - pip:
    - plotly>=5.0.0
```

```bash
pywatson init my-project --env-file environment.yml
```

## Development

### Running Tests

```bash
uv run python -m pytest tests/ -v
```

### Linting & Formatting

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Architecture

| Component | Description |
|-----------|-------------|
| `src/pywatson/core.py` | `ProjectScaffolder` class and Click CLI (`pywatson init`) |
| `src/pywatson/utils.py` | DrWatson.jl-style utilities (copied into generated projects) |
| `src/pywatson/templates/` | Jinja2 templates for generated project files |
| `create-project.sh` | Interactive bash wrapper for the CLI |
| `tests/` | pytest suite (scaffolding + template rendering tests) |

## Comparison with DrWatson.jl

| Feature | DrWatson.jl | PyWatson |
|---------|-------------|----------|
| Package manager | Pkg.jl | uv |
| Project structure | Yes | Yes (3 types) |
| Parameter-based naming | Yes | Yes |
| Smart caching | Yes | Yes |
| Git integration | Yes | Yes |
| Path management | Yes | Yes |
| HDF5 support | Yes | Yes |
| License selection | -- | Yes |
| CI generation | -- | Yes (full type) |
| Docker reproducibility | -- | Yes (`--docker`) |
| Docker beginner guide | -- | Yes ([docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md)) |
| Zenodo deposit guide | -- | Yes ([docs/ZENODO.md](docs/ZENODO.md)) |

## License

MIT License -- see [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by [DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/)
  from the Julia ecosystem
- Project patterns adopted from
  [copier-uv](https://github.com/pawamoy/copier-uv)
- Built with [uv](https://docs.astral.sh/uv/),
  [Click](https://click.palletsprojects.com/), and
  [Rich](https://rich.readthedocs.io/)

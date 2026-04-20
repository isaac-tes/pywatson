# 📦 Adopting Existing Projects

`pywatson adopt` scans an existing Python project and reorganizes it into the
pywatson structure, while preserving your code unchanged.

## When to use

- ✅ You have messy, unstructured code with files scattered around
- ✅ You want PyWatson-style organization without rewriting
- ✅ You want to migrate an existing project to pywatson standards
- ❌ You don't need it for brand-new projects (use `pywatson init`)

## Quick start

```bash
pywatson adopt /path/to/messy-code \
  --author-name "Jane Doe" \
  --author-email "jane@uni.edu" \
  --description "Monte Carlo simulations"
```

A new pywatson project will be created in the current directory with your code
organized into the standard structure.

## How it works

### 1. Scanning

`pywatson adopt` walks your project and **classifies each file** by:
- **Extension** (`.py`, `.csv`, `.ipynb`, etc.)
- **Name patterns** (test_*, *_test, requirements.txt, etc.)
- **Content** (imports pytest? Has `if __name__=='__main__'`? Etc.)

### 2. Classification

Files are sorted into 9 categories:

| Category | Examples | Default location |
|----------|----------|------------------|
| **tests** | test_*.py, *_test.py | `tests/` |
| **notebooks** | *.ipynb | `notebooks/` |
| **data** | *.csv, *.json, *.h5, *.npz, *.npy, *.nc, *.zarr | `data/` |
| **scripts** | main.py, analyze.py (with `if __name__=='__main__'`) | `scripts/` |
| **source** | helper.py, utils.py, package `__init__.py` | `src/{package_name}/` |
| **docs** | CHANGELOG.md, CONTRIBUTING.md, *.rst, *.tex, *.pdf (outside plot dirs) | `docs/` |
| **config** | README.md, LICENSE, *.yml, *.toml, *.ini, `uv.lock`, `.python-version` | Project root |
| **images** | *.png, *.jpg, *.svg, *.eps, *.gif, **.pdf inside `plots/`/`figures/`** | `plots/` |
| **other** | Anything else, and **all files inside `_research/`** | `_research/` |

> **Note**: `.pdf` files inside a `plots/`, `figures/`, `figs/`, or `fig/` directory are
> classified as **images** and go to `plots/`. PDFs elsewhere (e.g. a paper draft) go to `docs/`.

### What the scanner ignores

The scanner automatically skips:

- **Build / cache directories**: `.git`, `__pycache__`, `.venv`, `venv`, `dist`, `build`, `.tox`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `node_modules`, etc.
- **IDE config directories**: `.idea`, `.vscode`, `.specstory` — never scanned or copied.
- **CI/VCS config directories**: `.github` — workflows and Copilot instructions are ignored.
- **OS metadata files**: `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.gitkeep`, `.keep`.
- **Compiled bytecode**: `.pyc`, `.pyo`, `.pyd`.

> **`_research/` is special**: Python files inside `_research/` are always classified as
> **other** (→ `_research/`), regardless of their content. A script with
> `if __name__ == '__main__':` in `_research/` will *not* be routed to `scripts/`.

### 3. Interactive confirmation

Before copying, you can review the plan:

```
Adoption Plan for /path/to/messy-code → messy_code
────────────────────────────────────────────────────

Tests (2 files):
  test_utils.py → tests/
  test_analysis.py → tests/

Notebooks (3 files):
  exploration.ipynb → notebooks/
  ...

Data (5 files):
  results.csv → data/
  ...

Continue? [y/n]
```

### 4. Scaffolding & copying

Once confirmed:
1. Create all pywatson directories
2. Copy files to their new homes — using **collision-aware path placement**:
   - If all files in a category have **unique filenames**, they are placed flat (e.g. `data/results.npz`)
   - If two or more files share the same name (e.g. thousands of `ens_data.npz` in parameter-named subdirectories), the **full relative path is preserved** (e.g. `data/phi_0.5_N_10/run_001/ens_data.npz`) so nothing is lost
3. Generate boilerplate: `pyproject.toml`, `.gitignore`, `LICENSE`, etc.
4. Optionally initialize `uv` for dependency management

## Options

```bash
pywatson adopt SOURCE_PATH [OPTIONS]
```

| Option | Purpose |
|--------|---------|
| `-n, --project-name NAME` | Custom project name (default: source dir name) |
| `-o, --output-path PATH` | Write to different location (default: alongside source as `<name>_pywatson`) |
| `--auto` | Skip interactive confirmation |
| `--dry-run` | Preview plan, don't write anything |
| `--copy` | Copy files (default) |
| `--move` | Move files instead of copying |
| `--no-uv` | Skip `uv init` (useful for offline/testing) |
| `--author-name NAME` | Set author (default: `git config user.name`) |
| `--author-email EMAIL` | Set email (default: `git config user.email`) |
| `--description TEXT` | Project description |
| `-t, --project-type TYPE` | default, minimal, or full (default: default) |
| `--license TYPE` | MIT, Apache-2.0, BSD-3-Clause, ISC |
| `--python-version VERSION` | Minimum Python version (default: 3.12) |
| `--docker` | Scaffold Docker + docker-compose files for container reproducibility |
| `--zenodo` | Generate `.zenodo.json` metadata for Zenodo GitHub integration |

## Examples

### Example 1: Simple adoption

```bash
# Current directory: a messy research project
$ ls
simulation.py  plot.py  test_sim.py  data.csv  config.yaml

$ pywatson adopt . \
    --auto \
    --author-name "Alice" \
    --author-email "alice@example.com" \
    --project-name "my_sim"

# New structure created:
$ tree my_sim/ -L 2
my_sim/
├── src/my_sim/
│   ├── simulation.py
│   └── plot.py
├── tests/
│   └── test_sim.py
├── data/
│   └── data.csv
├── config.yaml
├── pyproject.toml
└── .gitignore
```

### Example 2: Dry-run preview

```bash
$ pywatson adopt /path/to/old-project --dry-run

Adoption Plan for old-project
────────────────────────────────────────────────────

Tests (2 files):
  test_core.py → tests/
  test_utils.py → tests/

Source (3 files):
  core.py → src/old_project/
  utils.py → src/old_project/
  helpers.py → src/old_project/

Data (4 files):
  raw_data.csv → data/
  ...

[DRY RUN - Nothing written]
```

### Example 3: From different location

```bash
# Adopt /path/to/messy, create result in ~/projects/
pywatson adopt /path/to/messy \
  --output-path ~/projects/adopted_project \
  --author-name "Bob" --author-email "bob@uni.edu" \
  --auto --move
```

### Example 4: Full project with all bells

```bash
pywatson adopt ~/old-research \
  --project-name "ising_model" \
  --author-name "Carol Doe" \
  --author-email "carol@physics.org" \
  --description "Ising model Monte Carlo study" \
  --project-type full \
  --license MIT \
  --python-version 3.11
```

## What gets regenerated

These files are **not copied** from the source (pywatson regenerates them):
- `pyproject.toml` — Package metadata & dependencies
- `setup.py` / `setup.cfg` — Old setuptools files
- `requirements.txt` — Dependency list (use `pyproject.toml` instead)
- `MANIFEST.in` — File inclusion rules
- `tox.ini` — Old test config

**Your custom versions are NOT moved.** Use `--move` with care if you have
important configuration here.

## After adoption

Your new project structure:

```bash
cd my-adopted-project
uv sync           # Install dependencies
uv run pytest     # Run tests
```

Edit the generated `pyproject.toml` to add your actual dependencies:

```toml
[project]
dependencies = [
    "numpy >= 1.20",
    "pandas >= 1.3",
]
```

Then:

```bash
uv sync --upgrade  # Resolve and install
```

## Troubleshooting

### Files in wrong category?

Edit the adoption result — file locations are now in your control. Or use `--dry-run`
and manually copy files as needed.

### Source and destination are the same?

Do not use `pywatson adopt .` (current dir as both source and output). Instead:
```bash
pywatson adopt /path/to/messy --output-path . --project-name my_proj
```

### Git conflicts after adoption?

Files are copied/moved, not renamed. Your `.git` history is unchanged. Consider:
```bash
git add -A
git commit -m "adopted: reorganized into pywatson structure"
```

## Design notes

- **Non-destructive by default** — Uses `--copy`; use `--move` to delete originals
- **Preserves content** — No code modifications, only file reorganization
- **Heuristic-based** — Classifiers use name patterns + content inspection
  (not 100% perfect, but good enough for most projects)
- **Self-contained result** — The generated project does not depend on pywatson
  at runtime (see [UTILITIES.md](UTILITIES.md))

## Related docs

- [QUICKSTART.md](QUICKSTART.md) — Using pywatson after adoption
- [CLI.md](CLI.md) — Full `pywatson adopt` reference
- [UTILITIES.md](UTILITIES.md) — PyWatson API in adopted projects

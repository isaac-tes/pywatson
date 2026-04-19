# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.0.2] — 2026-04-19

### Added

#### Docker scaffolding in `adopt`
- `pywatson adopt --docker` now generates the same Docker bundle as `pywatson init --docker`:
  `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `README_DOCKER.md`,
  and `.github/workflows/docker-publish.yml` (when a workflows directory exists)
- Interactive prompt for `--docker` in `adopt` non-auto mode

#### Zenodo metadata scaffolding (new feature)
- New `--zenodo` flag available on `pywatson` (direct), `pywatson init`, and `pywatson adopt`
- Generates `.zenodo.json` in the project root — links the repo to Zenodo for automatic
  DOI minting on every GitHub release
- Interactive prompt for `--zenodo` in non-auto / wizard modes
- New template `zenodo.json.jinja2`; new `ProjectScaffolder.create_zenodo_files()` method

#### Python 3.14 support
- Project venv pinned to Python 3.14 via `.python-version`
- CI matrix extended to `["3.12", "3.13", "3.14"]`
- `Programming Language :: Python :: 3.14` classifier added to `pyproject.toml`
- CI now also triggers on pushes to the `dev` branch

### Fixed

#### `adopt` robustness for real-world messy projects
- **Collision-aware path placement**: when two or more files in the same category share the
  same filename (e.g. thousands of `ens_data.npz` files in parameter-named subdirectories
  such as `phi_0.5_N_10/run_001/ens_data.npz`), `adopt` now automatically falls back to
  full source-relative path preservation. Normal projects with unique filenames retain flat
  placement (backward compatible).
- **IDE config directories ignored**: `.idea/`, `.vscode/`, `.specstory/` added to
  `ProjectScanner.IGNORE_DIRS` — their contents are never scanned or adopted.
- **OS metadata files ignored**: new `ProjectScanner.IGNORE_NAMES` frozenset skips
  `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.gitkeep`, `.keep`.
- **`__init__.py` classification fixed**: always classified as `source` (marks a Python
  package), but `tests/__init__.py` (inside a `tests/` directory) correctly stays `tests`.
- **Corrupt plan-building loop fixed**: previous partial edit had left `dest_file` assignment
  inside the `except ValueError:` block and left stale dry-run display code referencing
  undefined variables; rewritten cleanly.

#### Other fixes
- Docs: Zenodo link text clarity (`docs/citation.md`)
- Docs: `CLI.md` and `ADOPT_GUIDE.md` updated with new `--docker` / `--zenodo` options
- Docs: `ADOPT_GUIDE.md` classification table corrected — `.pdf` goes to `docs/` not `plots/`;
  added scanner ignore rules and collision-aware placement explanation
- CHANGELOG [0.0.1]: corrected project type list (`ml`, `data-analysis` never existed;
  the third type is `full`) and removed mention of nonexistent `--no-prompt` flag
- Version string in `core.py` and `__init__.py` corrected from stale values to `"0.0.2"`

### Tests

- 25 new tests added: `TestZenodoScaffolding` (12), `TestDockerAndZenodoInAdopt` (4),
  `TestDockerZenodoCLIFlags` (3), `test_zenodo_json_template_renders_valid_json` (1),
  `TestProjectScannerAndAdoptFixes` (7 — scanner IDE/OS ignoring, path collision preservation,
  module package structure, no IDE files adopted)
- Total: **340 collected, 333 passed, 7 skipped** (up from 315)

---

## [0.0.1] — 2026-03-10

Initial public release of PyWatson.

### Added

#### Project scaffolding
- `pywatson init` CLI command to scaffold new scientific Python projects
- Multiple project types: `default`, `minimal`, `full`
- Jinja2-based template system for all generated files (README, CHANGELOG,
  CI workflow, Makefile, notebooks, tests, core modules)
- Interactive wizard mode; non-interactive via CLI flags
- Optional uv environment initialisation (`--no-uv` to skip)
- Generated projects include: `src/` layout, `tests/`, `notebooks/`, `scripts/`,
  `data/`, `plots/`, `docs/` directories with sensible `.gitignore`

#### Project adoption (`pywatson adopt`)
- Adopt an existing unstructured project into the PyWatson layout
- Automatic file classification (source, data, tests, notebooks, scripts, docs, assets)
- `--dry-run` mode for safe inspection before any file moves
- `--auto` mode for unattended adoption in CI/scripts
- `--copy` flag to copy rather than move files

#### Path management utilities (DrWatson-inspired)
- `projectdir()`, `datadir()`, `plotsdir()`, `scriptsdir()`, `notebooksdir()`,
  `srcdir()`, `papersdir()` — project-root-relative path helpers
- `find_project_root()` — walk up to find `pyproject.toml` / `.git`

#### Data persistence
- `save_data()` / `load_data()` — HDF5 (h5py) with metadata stored as JSON attributes
- `save_npz()` / `load_npz()` — NumPy `.npz` format
- `save_zarr()` / `load_zarr()` — Zarr format with configurable compression
- `tagsave()` — always captures git hash/branch/dirty flag in metadata
- `produce_or_load()` — DrWatson-style smart cache: run function or load existing result

#### Parameter management
- `savename()` — deterministic filename from a parameter dictionary
  (`alpha=0.5_N=100_method=euler.h5`)
- `parse_savename()` — inverse: parse a filename back to a dictionary
- `dict_list()` / `dict_product()` — expand parameter sweeps

#### Data collection
- `collect_results()` — crawl `data/` for HDF5 files, aggregate into list of dicts
- Optional `as_dataframe=True` to return a `pandas.DataFrame`

#### Environment & reproducibility
- `snapshot_environment()` — capture package versions, Python version, OS, git state
- `set_random_seed()` — seed NumPy, random, and PyTorch (if available) in one call

#### Documentation & CI (this repo)
- MkDocs Material documentation site at
  [isaac-tes.github.io/pywatson](https://isaac-tes.github.io/pywatson)
- GitHub Actions CI: pytest on Python 3.12 and 3.13 + ruff linting
- GitHub Actions docs: auto-deploy to GitHub Pages on push to `main`

### Notes

- This is an **alpha release** (`0.0.x`). The public API may change before `1.0`.
- Requires Python 3.12+.

---

[0.0.2]: https://github.com/isaac-tes/pywatson/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/isaac-tes/pywatson/releases/tag/v0.0.1

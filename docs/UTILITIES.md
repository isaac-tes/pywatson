# PyWatson Utilities Reference

Complete API reference for `pywatson_utils.py` — the DrWatson.jl-inspired
helpers that are copied verbatim into every generated project.

---

## Table of Contents

1. [Path Management](#path-management)
2. [Parameter Filenames](#parameter-filenames)
3. [Parameter Grid Expansion](#parameter-grid-expansion)
4. [HDF5 Data I/O](#hdf5-data-io)
5. [NumPy NPZ Format](#numpy-npz-format)
6. [Zarr Format](#zarr-format)
7. [Smart Caching](#smart-caching)
8. [Atomic and Temporary Saves](#atomic-and-temporary-saves)
9. [Collecting Results](#collecting-results)
10. [Reproducibility Helpers](#reproducibility-helpers)
11. [Git Utilities](#git-utilities)

---

## Path Management

All path functions find the project root by walking upward until `pyproject.toml`
or `.git` is found.  They work correctly regardless of the working directory.

```python
from my_project import (
    datadir, plotsdir, scriptsdir, notebooksdir,
    docsdir, testsdir, srcdir, projectdir,
    datafile, plotfile,
)
```

### Directory functions

| Function | Returns |
|---|---|
| `datadir(*subdirs)` | `data/[subdirs]` |
| `plotsdir(*subdirs)` | `plots/[subdirs]` |
| `scriptsdir(*subdirs)` | `scripts/[subdirs]` |
| `notebooksdir(*subdirs)` | `notebooks/[subdirs]` |
| `docsdir(*subdirs)` | `docs/[subdirs]` |
| `testsdir(*subdirs)` | `tests/[subdirs]` |
| `srcdir(*subdirs)` | `src/[subdirs]` |
| `projectdir()` | Project root |

All functions accept optional `create: bool = True`.  Directories are created
automatically the first time you request them.

```python
datadir()                      # Path(".../my-project/data")
datadir("sims")                # Path(".../my-project/data/sims")
datadir("sims", "run_001")     # Path(".../my-project/data/sims/run_001")
plotsdir("figures", "final")   # Path(".../my-project/plots/figures/final")
```

### File helpers

```python
datafile("results.h5")         # Path(".../data/results.h5")
plotfile("energy.pdf")         # Path(".../plots/energy.pdf")
```

---

## Parameter Filenames

### `savename(d, suffix=".h5", connector="_", digits=3, ignore_keys=None)`

Creates a deterministic, human-readable filename from a parameter dictionary.
Keys are sorted alphabetically; floats are formatted with *significant figures*.

```python
from my_project import savename

params = {"alpha": 0.5, "N": 100, "method": "euler", "dt": 0.001}

savename(params)                         # "N=100_alpha=0.5_dt=0.001_method=euler.h5"
savename(params, suffix=".npz")          # "N=100_alpha=0.5_dt=0.001_method=euler.npz"
savename(params, connector="-")          # "N=100-alpha=0.5-dt=0.001-method=euler.h5"
savename(params, digits=2)               # "N=100_alpha=0.5_dt=0.001_method=euler.h5"
savename(params, ignore_keys=["method"]) # "N=100_alpha=0.5_dt=0.001.h5"
```

Pair with `datadir()` for a complete path:

```python
filepath = datadir("sims") / savename(params)
```

### `parse_savename(filename)`

Parses a `savename`-generated filename back into a parameter dictionary.
Performs automatic type coercion: integers stay `int`, other numbers become
`float`, everything else stays `str`.

```python
from my_project import parse_savename

parse_savename("N=100_alpha=0.5_method=euler.h5")
# -> {"N": 100, "alpha": 0.5, "method": "euler"}

parse_savename("beta=0.44_seed=0.npz")
# -> {"beta": 0.44, "seed": 0}
```

Known extensions (`.h5`, `.npz`, `.zarr`, `.nc`, `.csv`, `.json`, `.pkl`,
`.npy`, `.tmp`) are stripped before parsing.

---

## Parameter Grid Expansion

### `dict_list(*dicts)`

Expands one or more parameter dictionaries into every Cartesian-product
combination.  List-valued entries are expanded; scalars are broadcast.

```python
from my_project import dict_list

combos = dict_list({"alpha": [0.1, 0.5, 1.0], "N": [100, 1000]})
# -> 6 dicts:
# [{"alpha": 0.1, "N": 100}, {"alpha": 0.1, "N": 1000},
#  {"alpha": 0.5, "N": 100}, {"alpha": 0.5, "N": 1000},
#  {"alpha": 1.0, "N": 100}, {"alpha": 1.0, "N": 1000}]

# Fixed params + sweep
all_runs = dict_list({"model": "euler", "T": 10}, {"dt": [0.01, 0.001]})
# -> [{"model": "euler", "T": 10, "dt": 0.01},
#     {"model": "euler", "T": 10, "dt": 0.001}]

# Typical sweep loop
for p in dict_list({"alpha": [0.1, 0.5], "N": [100, 1000]}):
    data = run_simulation(p)
    save_data(data, savename(p), subdir="sims")
```

---

## HDF5 Data I/O

### `save_data(data, filename, metadata=None, compression="gzip", include_git=False, subdir=None)`

Saves a dictionary of arrays and scalars to an HDF5 file in `data/`.

```python
from my_project import save_data
import numpy as np

data = {
    "time":   np.linspace(0, 10, 1000),
    "signal": np.sin(np.linspace(0, 10, 1000)),
}

# Basic save
path = save_data(data, "experiment_001")
# -> data/experiment_001.h5

# With metadata
path = save_data(data, "experiment_001",
                 metadata={"sensor": "A", "gain": 2.0})

# Into a subdirectory (created automatically)
path = save_data(data, "run_001", subdir="sims")
# -> data/sims/run_001.h5

# Embed git commit hash (opt-in)
path = save_data(data, "run_001", include_git=True)

# Supported value types:
#   np.ndarray, scalars (int/float/bool), str, list/tuple,
#   dict (saved as HDF5 group), pandas.DataFrame
```

### `tagsave(filename, data, tags=None)`

Thin alias for `save_data(..., include_git=True)`.  Always embeds the current
git commit hash, branch, and dirty flag.

```python
from my_project import tagsave

params = {"N": 1000, "beta": 0.44}
tagsave(savename(params), data, tags=params)
# Metadata will include gitcommit, gitbranch + all params keys
```

### `load_data(filename, keys=None)`

Loads an HDF5 file from `data/`.  Metadata is always included as `_metadata`.

```python
from my_project import load_data

result = load_data("experiment_001")
result["time"]       # numpy array
result["signal"]     # numpy array
result["_metadata"]  # dict: created_at, created_by, script, + any custom fields

# Load only specific keys (efficient for large files)
partial = load_data("experiment_001", keys=["signal"])
```

### `load_selective(filename, keys)`

Convenience wrapper; equivalent to `load_data(filename, keys=keys)`.

```python
partial = load_selective("experiment_001", ["signal", "time"])
```

### `data_info(filename)`

Returns file stats and schema without loading arrays.

```python
info = data_info("experiment_001")
# {"filepath": ..., "size_bytes": ..., "datasets": {"time": {...}, ...}, "metadata": {...}}
```

### `list_data_files()`

Returns all `*.h5` files in `data/` as a list of `Path` objects.

---

## NumPy NPZ Format

### `save_npz(data, filename, metadata=None, compressed=True, subdir=None)`

```python
from my_project import save_npz, load_npz

save_npz({"x": arr, "y": arr2}, "run_001", metadata={"note": "test"})
# -> data/run_001.npz

save_npz(data, "run_001", subdir="sims")
# -> data/sims/run_001.npz
```

### `load_npz(filename, subdir=None)`

```python
result = load_npz("run_001")
result["x"]          # numpy array
result["_metadata"]  # dict (if metadata was saved)
```

---

## Zarr Format

Requires `zarr` package (`uv add zarr` or `pip install zarr`).

### `save_zarr(data, filename, metadata=None, compression="blosc", subdir=None)`

```python
from my_project import save_zarr, load_zarr

save_zarr({"signal": large_array}, "run_001", metadata={"run": 1})
# -> data/run_001.zarr/

save_zarr(data, "run_001", compression="gzip", subdir="sims")
```

### `load_zarr(filename, keys=None, subdir=None)`

```python
result = load_zarr("run_001")           # all arrays
result = load_zarr("run_001", keys=["signal"])  # selective load
result["_metadata"]                     # dict
```

---

## Smart Caching

### `produce_or_load(filename, producing_function, *args, subdir=None, **kwargs)`

Runs `producing_function` the **first time** and saves the result; on
subsequent calls with the same filename it loads from disk without calling
the function.

```python
from my_project import produce_or_load, savename

def run_simulation(N: int, beta: float) -> dict:
    """Expensive computation — only runs when cache is missing."""
    import numpy as np
    energy = np.random.normal(-beta, 1.0, N)
    return {"energy": energy}

params = {"N": 10_000, "beta": 0.44}
filename = savename(params)  # "N=10000_beta=0.44.h5"

# First call: runs function, saves result
data, filepath = produce_or_load(filename, run_simulation, **params)
print(f"Saved to: {filepath}")

# Second call: loads from disk, function NOT called
data, filepath = produce_or_load(filename, run_simulation, **params)

# With subdirectory
data, filepath = produce_or_load(filename, run_simulation, **params,
                                  subdir="sims/ising")
```

**Returns**: `(data_dict, Path)` — the data dictionary and the path to the
cached file.

**Note**: `producing_function` must return a `dict`.  The result is saved with
`include_git=True` (via `tagsave`) so every cache file carries a commit hash.

---

## Atomic and Temporary Saves

### `safesave(filename, data, metadata=None, compression="gzip", include_git=False, subdir=None)`

Writes to a `.tmp.h5` sibling file, then atomically renames it into place.
If the write fails, the original file (if any) is untouched.

```python
from my_project import safesave

# Safe even if process is killed mid-write
safesave("run_001", data, metadata={"run": 1}, subdir="sims")
```

### `tmpsave(data, suffix=".h5", compression="gzip")` (context manager)

Saves data to a temporary file, yields its `Path`, then deletes it when the
`with` block exits.

```python
from my_project import tmpsave

with tmpsave({"x": arr}) as tmp_path:
    # `tmp_path` is a valid HDF5 file here
    result = validate(tmp_path)
# File is deleted here automatically
```

---

## Collecting Results

### `collect_results(folder_path=None, subdir=None, recursive=True, as_dataframe=False)`

Loads all `*.h5` files from a directory.  Scalar values and metadata fields
are flattened into columns when `as_dataframe=True`.

```python
from my_project import collect_results

# List of dicts (one per file)
rows = collect_results(subdir="sims")

# pandas DataFrame
df = collect_results(subdir="sims", as_dataframe=True)
# Metadata keys are prefixed with _meta_:
# columns: N, beta, seed, energy, _meta_created_at, _filepath, ...

high_beta = df[df["beta"] > 0.4]

# Collect from an absolute path
rows = collect_results(folder_path="/path/to/dir")

# Non-recursive
rows = collect_results(subdir="sims", recursive=False)
```

---

## Reproducibility Helpers

### `snapshot_environment()`

Captures Python version, platform, and all installed packages.

```python
from my_project import snapshot_environment

env = snapshot_environment()
# {
#   "python_version": "3.12.9",
#   "platform": "macOS-14.4-arm64-...",
#   "packages": ["numpy==2.0.0", "h5py==3.11.0", ...],
#   "captured_at": "2025-03-09T10:00:00"
# }

# Embed in saved data
save_data(data, "run_001", metadata={"environment": env})
```

### `set_random_seed(seed)`

Sets seeds for Python `random`, NumPy, and PyTorch (if installed).
Returns a metadata-ready dict.

```python
from my_project import set_random_seed

meta = set_random_seed(42)   # -> {"random_seed": 42}

# Combine with params for a fully reproducible save
params = {"N": 1000, "beta": 0.44}
tagsave(savename(params), run_simulation(**params), tags={**params, **meta})
```

---

## Git Utilities

These are internal helpers used by `save_data` and `tagsave`, but available
for direct use if needed.

```python
from my_project.pywatson_utils import (
    current_git_commit,
    git_status_clean,
    find_project_root,
)

current_git_commit()       # "a3f9c1e"  (short hash)
current_git_commit(short=False)  # full 40-char hash
git_status_clean()         # True / False / None (if not a git repo)
find_project_root()        # Path to project root, or None
```

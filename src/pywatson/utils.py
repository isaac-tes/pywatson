"""
PyWatson utilities — path management and HDF5 data handling.

Provides DrWatson.jl-inspired helpers for:
  - Path management  : datadir(), plotsdir(), savename(), …
  - HDF5 data I/O    : save_data(), tagsave(), load_data(), load_selective(), …
  - Smart caching    : produce_or_load()

Key design choices
------------------
save_data  — git info is **opt-in** (``include_git=False`` by default).
             Pass ``include_git=True`` to embed commit hash / branch / dirty
             flag in the file's metadata.
tagsave    — thin alias that **always** captures git state; equivalent to
             ``save_data(..., include_git=True)``.  Use this when you want
             every saved file to be traceable to an exact commit.
"""

import itertools
import json
import os
import platform
import re as _re
import subprocess
import sys
import tempfile
import inspect
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Union

import h5py
import numpy as np

try:
    import pandas as pd  # type: ignore[import]
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

try:
    import zarr  # type: ignore[import]
    _HAS_ZARR = True
except ImportError:
    _HAS_ZARR = False


# Cache for project root to avoid repeated filesystem lookups
_PROJECT_ROOT = None


# Core path and data management functionality for DrWatson-style projects


def find_project_root(start_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """
    Find the project root directory by looking for pyproject.toml or .git.

    Args:
        start_path: Starting directory to search from. Defaults to current directory.

    Returns:
        Path to project root or None if not found.
    """
    global _PROJECT_ROOT

    if _PROJECT_ROOT is not None:
        return _PROJECT_ROOT

    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    current = start_path.resolve()

    # Walk up the directory tree looking for pyproject.toml or .git
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            _PROJECT_ROOT = current
            return _PROJECT_ROOT
        current = current.parent

    return None


def get_project_dir(directory: str, *subdirs: str, create: bool = True) -> Path:
    """
    Get path to a project directory (data, plots, scripts, etc.) with optional subdirectories.

    Args:
        directory: Directory name (e.g., 'data', 'plots', 'scripts', 'notebooks')
        *subdirs: Optional subdirectories to append
        create: Whether to create the directory if it doesn't exist

    Returns:
        Path to the requested directory

    Raises:
        RuntimeError: If project root cannot be found
    """
    project_root = find_project_root()

    if project_root is None:
        raise RuntimeError(
            "Could not find project root. Make sure you're in a PyWatson project "
            "(should contain pyproject.toml or .git)"
        )

    dir_path = project_root / directory
    if subdirs:
        dir_path = dir_path.joinpath(*subdirs)

    if create and not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)

    return dir_path


def datadir(*subdirs, create: bool = True) -> Path:
    """Get path to data directory, optionally with subdirectories."""
    return get_project_dir("data", *subdirs, create=create)


def plotsdir(*subdirs, create: bool = True) -> Path:
    """Get path to plots directory, optionally with subdirectories."""
    return get_project_dir("plots", *subdirs, create=create)


def scriptsdir(*subdirs, create: bool = True) -> Path:
    """Get path to scripts directory, optionally with subdirectories."""
    return get_project_dir("scripts", *subdirs, create=create)


def notebooksdir(*subdirs, create: bool = True) -> Path:
    """Get path to notebooks directory, optionally with subdirectories."""
    return get_project_dir("notebooks", *subdirs, create=create)


def docsdir(*subdirs, create: bool = True) -> Path:
    """Get path to docs directory, optionally with subdirectories."""
    return get_project_dir("docs", *subdirs, create=create)


def testsdir(*subdirs, create: bool = True) -> Path:
    """Get path to tests directory, optionally with subdirectories."""
    return get_project_dir("tests", *subdirs, create=create)


def srcdir(*subdirs, create: bool = True) -> Path:
    """Get path to src directory, optionally with subdirectories."""
    return get_project_dir("src", *subdirs, create=create)


def projectdir() -> Path:
    """Get path to project root directory."""
    project_root = find_project_root()
    if project_root is None:
        raise RuntimeError(
            "Could not find project root. Make sure you're in a PyWatson project "
            "(should contain pyproject.toml)"
        )
    return project_root


def datafile(filename: str, create_dir: bool = True) -> Path:
    """Get path to a file in the data directory."""
    return datadir(create=create_dir) / filename


def plotfile(filename: str, create_dir: bool = True) -> Path:
    """Get path to a file in the plots directory."""
    return plotsdir(create=create_dir) / filename


def scriptfile(filename: str, create_dir: bool = True) -> Path:
    """Get path to a file in the scripts directory."""
    return scriptsdir(create=create_dir) / filename


def notebookfile(filename: str, create_dir: bool = True) -> Path:
    """Get path to a file in the notebooks directory."""
    return notebooksdir(create=create_dir) / filename


def savename(
    d: dict,
    suffix: str = ".h5",
    connector: str = "_",
    access: Optional[Any] = None,
    digits: int = 3,
    ignore_keys: Optional[list] = None,
) -> str:
    """
    Create a filename from a dictionary, similar to DrWatson's savename.

    Args:
        d: Dictionary with parameter values.
        suffix: File suffix to be appended.
        connector: String used to join key-value pairs.
        access: Function to access specific properties of values.
        digits: Number of significant digits for floats (default: 3).
        ignore_keys: List of keys to exclude from filename.

    Returns:
        Formatted filename.

    Example:
        >>> savename({"alpha": 0.5, "beta": 10}, suffix=".h5")
        'alpha=0.5_beta=10.h5'
        >>> savename({"alpha": 0.6666666, "beta": 10}, digits=2)
        'alpha=0.67_beta=10.h5'
    """
    if not d:
        return suffix

    if ignore_keys is None:
        ignore_keys = []

    # Sort keys for consistent naming
    sorted_keys = sorted(k for k in d.keys() if k not in ignore_keys)

    parts = []
    for k in sorted_keys:
        v = d[k]
        if access is not None:
            v = access(v)

        # Format floats with significant digits (not decimal places)
        if isinstance(v, float):
            # g format: {digits} significant figures, strips trailing zeros automatically
            v_str = f"{v:.{digits}g}"
        else:
            v_str = str(v)

        parts.append(f"{k}={v_str}")

    return connector.join(parts) + suffix


# Git and script tracking utilities
def _run_git_command(cmd, cwd=None):
    """Run a git command and return its output."""
    if cwd is None:
        project_root = find_project_root()
        cwd = project_root if project_root else Path.cwd()

    try:
        result = subprocess.run(["git"] + cmd, capture_output=True, text=True, check=True, cwd=cwd)
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def current_git_commit(short=True):
    """Get the current git commit hash."""
    cmd = ["rev-parse", "--verify", "HEAD"]
    if short:
        cmd = ["rev-parse", "--short", "HEAD"]
    return _run_git_command(cmd)


def git_status_clean():
    """Check if the git repository has uncommitted changes."""
    status = _run_git_command(["status", "--porcelain"])
    return status == "" if status is not None else None


def _get_script_info():
    """Get information about the calling script.

    Walks up the call stack and returns the first frame whose file is not
    this module (utils.py / pywatson_utils.py).  This works correctly
    regardless of call depth:

    * ``save_data(..., include_git=True)`` — 2 frames deep
    * ``tagsave(...)`` — 3 frames deep
    * ``produce_or_load(...)`` — 4 frames deep
    """
    this_file = Path(__file__).resolve()
    frame = inspect.currentframe()
    try:
        outer_frames = inspect.getouterframes(frame)
        script_absolute_path = None
        for caller in outer_frames[1:]:  # skip frame 0 (this function itself)
            caller_path = Path(caller.filename).resolve()
            if caller_path != this_file:
                script_absolute_path = caller_path
                break

        if script_absolute_path is None:
            return "unknown_script"

        # Try to return a path relative to the project root
        project_root = find_project_root()
        if project_root:
            try:
                return str(script_absolute_path.relative_to(project_root))
            except ValueError:
                pass

        return str(script_absolute_path)
    except (IndexError, AttributeError):
        return "unknown_script"
    finally:
        del frame  # Avoid reference cycles


# Data management functions
def save_data(
    data: Dict[str, Any],
    filename: str,
    metadata: Optional[Dict[str, Any]] = None,
    compression: Optional[str] = "gzip",
    include_git: bool = False,
    subdir: Optional[str] = None,
) -> Path:
    """
    Save data to HDF5 file in the data directory with metadata.

    Git information is **opt-in**: pass ``include_git=True`` to embed the
    current commit hash, branch, and dirty-state flag in the file metadata.
    Use :func:`tagsave` instead if you always want git tracking.

    Args:
        data: Dictionary of data to save (keys become HDF5 groups/datasets).
              Values may be numpy arrays, scalars, strings, lists, dicts, or
              ``pandas.DataFrame`` objects (saved as column datasets).
        filename: Name of the file (without extension)
        metadata: Optional metadata dictionary
        compression: Compression method ('gzip', 'lzf', 'szip', or None)
        include_git: Whether to include git information in metadata
                     (default: False — opt-in)
        subdir: Optional subdirectory within data/ to save the file in.
                Created automatically if it does not exist.

    Returns:
        Path to the saved file
    """
    # Ensure filename has .h5 extension (filename is a str, not Path)
    if not filename.endswith(".h5"):
        filename = filename + ".h5"

    if subdir:
        filepath = datadir(subdir, create=True) / filename
    else:
        filepath = datafile(filename)

    with h5py.File(filepath, "w") as f:
        # Prepare metadata
        if metadata is None:
            metadata = {}

        # Add timestamp and creator info
        metadata["created_at"] = datetime.now().isoformat()
        metadata["created_by"] = "PyWatson"
        metadata["script"] = _get_script_info()

        # Add git information if requested
        if include_git:
            git_info = {
                "gitcommit": current_git_commit(),
                "gitpatch": not git_status_clean() if git_status_clean() is not None else None,
                "gitbranch": _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]),
            }
            # Only add non-None values
            git_info = {k: v for k, v in git_info.items() if v is not None}
            if git_info:
                metadata.update(git_info)

        # Save metadata as JSON string attribute
        f.attrs["metadata"] = json.dumps(metadata)

        # Save data
        for key, value in data.items():
            _save_value_to_hdf5(f, key, value, compression)

    return filepath


def load_data(filename: str, keys: Optional[list] = None) -> Dict[str, Any]:
    """
    Load data from HDF5 file in the data directory.

    Args:
        filename: Name of the file (with or without .h5 extension)
        keys: Optional list of dataset keys to load. If None, loads all datasets.
              Metadata is always loaded regardless of this parameter.

    Returns:
        Dictionary containing the loaded data and metadata
    """
    # Ensure filename has .h5 extension (filename is a str, not Path)
    if not filename.endswith(".h5"):
        filename = filename + ".h5"

    filepath = datafile(filename, create_dir=False)

    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    data = {}

    with h5py.File(filepath, "r") as f:
        # Load metadata (always loaded)
        if "metadata" in f.attrs:
            try:
                data["_metadata"] = json.loads(str(f.attrs["metadata"]))
            except json.JSONDecodeError:
                data["_metadata"] = {"note": "Could not parse metadata"}

        # Load datasets and groups
        if keys is None:
            # Load everything
            for key in f.keys():
                data[key] = _load_item_from_hdf5(f[key])
        else:
            # Load only specified keys
            for key in keys:
                if key in f:
                    data[key] = _load_item_from_hdf5(f[key])
                else:
                    print(f"Warning: Key '{key}' not found in {filename}")

    return data


def _save_value_to_hdf5(
    parent: Union[h5py.File, h5py.Group],
    key: str,
    value: Any,
    compression: Optional[str] = "gzip",
) -> None:
    """Write a single value into an HDF5 file or group."""
    if _HAS_PANDAS and isinstance(value, pd.DataFrame):
        grp = parent.create_group(key)
        grp.attrs["_pywatson_type"] = "dataframe"
        grp.attrs["_df_columns"] = json.dumps(list(value.columns))
        for col in value.columns:
            col_data = value[col].to_numpy()
            if col_data.dtype.kind in ("U", "O", "S"):
                encoded = np.array([str(x).encode("utf-8") for x in col_data])
                grp.create_dataset(str(col), data=encoded)
            else:
                grp.create_dataset(str(col), data=col_data, compression=compression)
    elif isinstance(value, np.ndarray):
        parent.create_dataset(key, data=value, compression=compression)
    elif isinstance(value, (int, float, bool)):
        parent.create_dataset(key, data=value)
    elif isinstance(value, str):
        parent.create_dataset(key, data=value.encode("utf-8") if value else b"")
    elif isinstance(value, (list, tuple)):
        parent.create_dataset(key, data=np.array(value), compression=compression)
    elif isinstance(value, dict):
        group = parent.create_group(key)
        _save_dict_to_group(group, value, compression)
    else:
        try:
            parent.create_dataset(key, data=np.array(value), compression=compression)
        except Exception as e:
            print(f"Warning: Could not save {key}: {e}")


def _save_dict_to_group(
    group: h5py.Group, data: Dict[str, Any], compression: Optional[str] = "gzip"
) -> None:
    """Recursively save dictionary to HDF5 group."""
    for key, value in data.items():
        _save_value_to_hdf5(group, key, value, compression)


def _load_item_from_hdf5(item: Union[h5py.Dataset, h5py.Group]) -> Any:
    """Load item from HDF5 file (dataset or group), reconstructing DataFrames."""
    if isinstance(item, h5py.Group):
        if item.attrs.get("_pywatson_type") == "dataframe" and _HAS_PANDAS:
            columns = json.loads(item.attrs["_df_columns"])
            col_data = {}
            for col in columns:
                raw = item[str(col)][()]
                if isinstance(raw, np.ndarray) and raw.dtype.kind == "S":
                    col_data[col] = np.array([x.decode("utf-8") for x in raw])
                else:
                    col_data[col] = raw
            return pd.DataFrame(col_data)
        return {key: _load_item_from_hdf5(item[key]) for key in item.keys()}
    elif isinstance(item, h5py.Dataset):
        data = item[()]
        if isinstance(data, bytes):
            return data.decode("utf-8")
        elif isinstance(data, np.ndarray) and data.dtype.kind == "S":
            return np.array([x.decode("utf-8") for x in data])
        return data
    else:
        return item


def load_selective(filename: str, keys: list) -> Dict[str, Any]:
    """
    Load only specific keys from HDF5 file (convenience wrapper for load_data).
    Metadata is always loaded automatically.

    Args:
        filename: Name of the file (with or without .h5 extension)
        keys: List of dataset keys to load

    Returns:
        Dictionary containing the loaded data and metadata

    Example:
        >>> data = load_selective('results.h5', ['dataset1', 'dataset3'])
        >>> # Returns only dataset1 and dataset3, plus _metadata
    """
    return load_data(filename, keys=keys)


def list_data_files() -> list[Path]:
    """List all HDF5 data files in the data directory."""
    data_dir = datadir(create=False)
    if not data_dir.exists():
        return []

    return list(data_dir.glob("*.h5"))


def data_info(filename: str) -> Dict[str, Any]:
    """
    Get information about a data file without loading all data.

    Args:
        filename: Name of the file (with or without .h5 extension)

    Returns:
        Dictionary with file information
    """
    if not filename.endswith(".h5"):
        filename = filename + ".h5"

    filepath = datafile(filename, create_dir=False)

    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    info = {
        "filepath": str(filepath),
        "size_bytes": filepath.stat().st_size,
        "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        "datasets": {},
        "groups": [],
        "metadata": {},
    }

    with h5py.File(filepath, "r") as f:
        # Get metadata
        if "metadata" in f.attrs:
            try:
                info["metadata"] = json.loads(str(f.attrs["metadata"]))
            except json.JSONDecodeError:
                info["metadata"] = {"note": "Could not parse metadata"}

        # Get dataset and group info
        def collect_info(name, obj):
            if isinstance(obj, h5py.Dataset):
                info["datasets"][name] = {
                    "shape": obj.shape,
                    "dtype": str(obj.dtype),
                    "size_bytes": obj.size * obj.dtype.itemsize,
                }
            elif isinstance(obj, h5py.Group):
                info["groups"].append(name)

        f.visititems(collect_info)

    return info


def save_array(array: np.ndarray, name: str, metadata: Optional[Dict[str, Any]] = None) -> Path:
    """
    Convenience function to save a single numpy array.

    Args:
        array: Numpy array to save
        name: Name for the array (used as filename)
        metadata: Optional metadata

    Returns:
        Path to saved file
    """
    return save_data({name: array}, name, metadata)


def load_array(filename: str, array_name: Optional[str] = None) -> np.ndarray:
    """
    Convenience function to load a single numpy array.

    Args:
        filename: Name of the file
        array_name: Name of the array in the file (if None, loads first array found)

    Returns:
        Numpy array
    """
    data = load_data(filename)

    # Remove metadata from consideration
    arrays = {k: v for k, v in data.items() if not k.startswith("_")}

    if array_name is None:
        if len(arrays) == 0:
            raise ValueError(f"No arrays found in {filename}")
        array_name = next(iter(arrays.keys()))

    if array_name not in arrays:
        available = list(arrays.keys())
        raise KeyError(f"Array '{array_name}' not found. Available: {available}")

    return arrays[array_name]


def tagsave(filename: str, data: Dict[str, Any], tags: Optional[Dict[str, Any]] = None) -> Path:
    """
    Save data with git state and custom tags (DrWatson.jl-style alias).

    Equivalent to ``save_data(data, filename, metadata=tags, include_git=True)``.
    Use this whenever you want every file to carry an exact git commit hash,
    branch name, and dirty-state flag — e.g. for parameter sweeps where
    reproducibility is critical.

    Args:
        filename: Name of the file (with or without .h5 extension)
        data: Data dictionary to save
        tags: Additional tags to include in metadata (merged with git info)

    Returns:
        Path to the saved file

    Example:
        >>> params = {"alpha": 0.01, "nx": 100}
        >>> tagsave(savename(params), {"T": temperature_array}, tags=params)
    """
    if tags is None:
        tags = {}

    # Merge data and tags
    all_data = {**data}

    # Save with git info and tags as metadata
    return save_data(all_data, filename, metadata=tags, include_git=True)


def produce_or_load(
    filename: str,
    producing_function: Any,
    *args: Any,
    subdir: Optional[str] = None,
    **kwargs: Any,
) -> tuple[Dict[str, Any], Path]:
    """
    Load existing data or produce and save new data (DrWatson.jl-style smart cache).

    On the **first** call the producing function is executed and its result is
    saved via :func:`tagsave` (git info always captured).  On every subsequent
    call the file is loaded directly — the producing function is not called.

    Args:
        filename: Name of the cache file to load from or save to
        producing_function: Function that returns a ``dict`` if the file does
                            not yet exist
        *args: Positional arguments forwarded to ``producing_function``
        subdir: Optional subdirectory within data/ (keyword-only)
        **kwargs: Keyword arguments forwarded to ``producing_function``

    Returns:
        Tuple of ``(data_dict, filepath)`` where ``filepath`` is the
        :class:`~pathlib.Path` of the cached file.

    Raises:
        TypeError: If ``producing_function`` does not return a ``dict``.

    Example:
        >>> data, fp = produce_or_load("sim_alpha=0.01", run_simulation, alpha=0.01)
        >>> print("loaded from", fp)
    """
    if not filename.endswith(".h5"):
        filename = filename + ".h5"

    if subdir:
        filepath = datadir(subdir, create=True) / filename
    else:
        filepath = datafile(filename, create_dir=False)

    if filepath.exists():
        return load_data(filepath.name) if not subdir else _load_data_from_path(filepath), filepath

    data = producing_function(*args, **kwargs)

    if not isinstance(data, dict):
        raise TypeError("producing_function must return a dictionary")

    save_data(data, filename[:-3], include_git=True, subdir=subdir)
    return data, filepath


def _load_data_from_path(filepath: Path) -> Dict[str, Any]:
    """Load HDF5 data from an absolute path (internal helper)."""
    data: Dict[str, Any] = {}
    with h5py.File(filepath, "r") as f:
        if "metadata" in f.attrs:
            try:
                data["_metadata"] = json.loads(str(f.attrs["metadata"]))
            except json.JSONDecodeError:
                data["_metadata"] = {"note": "Could not parse metadata"}
        for key in f.keys():
            data[key] = _load_item_from_hdf5(f[key])
    return data


def collect_results(
    folder_path: Optional[str] = None,
    subdir: Optional[str] = None,
    recursive: bool = True,
    as_dataframe: bool = False,
) -> "list[Dict[str, Any]] | pd.DataFrame":
    """
    Collect all results from .h5 files in a folder.

    Args:
        folder_path: Explicit path to the folder. Defaults to ``datadir()``.
        subdir: Subdirectory *within* ``datadir()`` to search (mutually
                exclusive with ``folder_path``).
        recursive: Whether to search subdirectories recursively (default True).
        as_dataframe: Return a ``pandas.DataFrame`` instead of a list of dicts.
                      Scalar values and metadata fields become columns.
                      Requires pandas to be installed.

    Returns:
        List of data dicts, or a ``pandas.DataFrame`` when *as_dataframe*
        is ``True``.
    """
    if folder_path is not None:
        folder = Path(folder_path)
    elif subdir is not None:
        folder = datadir(subdir, create=False)
    else:
        folder = datadir(create=False)

    if not folder.exists():
        return (pd.DataFrame() if as_dataframe and _HAS_PANDAS else [])

    pattern = "**/*.h5" if recursive else "*.h5"
    results: list[Dict[str, Any]] = []

    for filepath in sorted(folder.glob(pattern)):
        try:
            data = _load_data_from_path(filepath)
            data["_filepath"] = str(filepath)
            results.append(data)
        except Exception as e:
            print(f"Warning: could not load {filepath}: {e}")

    if as_dataframe:
        if not _HAS_PANDAS:
            raise ImportError(
                "pandas is required for as_dataframe=True. "
                "Install with: uv add pandas  or  pip install pandas"
            )
        # Flatten scalar metadata fields into top-level columns
        flat_rows = []
        for row in results:
            flat: Dict[str, Any] = {}
            for k, v in row.items():
                if k == "_metadata" and isinstance(v, dict):
                    for mk, mv in v.items():
                        flat[f"_meta_{mk}"] = mv
                elif not isinstance(v, (np.ndarray, dict, list)):
                    flat[k] = v
            flat_rows.append(flat)
        return pd.DataFrame(flat_rows)

    return results


# ---------------------------------------------------------------------------
# DrWatson primitives: parse_savename, dict_list
# ---------------------------------------------------------------------------


def parse_savename(filename: str) -> Dict[str, Any]:
    """
    Parse a filename produced by :func:`savename` back into a parameter dict.

    Performs best-effort type coercion: integer strings become ``int``,
    numeric strings become ``float``, everything else stays ``str``.
    Keys not in ``key=value`` form (e.g. a bare project name prefix) are
    silently ignored.

    Args:
        filename: Filename or path string, e.g. ``"alpha=0.5_N=100_method=euler.h5"``.

    Returns:
        Dictionary of parameter key→value pairs.

    Example:
        >>> parse_savename("alpha=0.5_N=100_method=euler.h5")
        {'N': 100, 'alpha': 0.5, 'method': 'euler'}
    """
    # Strip directory component, then strip only *known* file extensions from the right.
    # Using Path.stem in a loop would drop value-dots (e.g. alpha=0.5 → alpha=0).
    _KNOWN_EXTS = {".h5", ".npz", ".zarr", ".nc", ".csv", ".json", ".pkl", ".tmp", ".npy"}
    stem = Path(filename).name
    changed = True
    while changed:
        changed = False
        for ext in _KNOWN_EXTS:
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                changed = True
                break

    result: Dict[str, Any] = {}
    for part in stem.split("_"):
        if "=" not in part:
            continue
        key, _, raw = part.partition("=")
        if not key:
            continue
        # Type coercion: int → float → str
        try:
            result[key] = int(raw)
        except ValueError:
            try:
                result[key] = float(raw)
            except ValueError:
                result[key] = raw
    return result


def dict_list(*dicts: dict) -> list[Dict[str, Any]]:
    """
    Expand parameter dictionaries into every combination (Cartesian product).

    List-valued entries are expanded; scalar entries are broadcast.  Accepts
    multiple dicts that are first merged left-to-right.

    Args:
        *dicts: One or more parameter dictionaries.  Later dicts override
                earlier keys.  List values are expanded; scalars are
                treated as single-element lists.

    Returns:
        List of flat parameter dicts, one per combination.

    Example:
        >>> dict_list({"alpha": [0.1, 0.5], "N": [100, 1000]})
        [{'alpha': 0.1, 'N': 100}, {'alpha': 0.1, 'N': 1000},
         {'alpha': 0.5, 'N': 100}, {'alpha': 0.5, 'N': 1000}]
        >>> dict_list({"model": "euler"}, {"dt": [0.01, 0.001], "T": 10})
        [{'model': 'euler', 'dt': 0.01, 'T': 10},
         {'model': 'euler', 'dt': 0.001, 'T': 10}]
    """
    combined: Dict[str, Any] = {}
    for d in dicts:
        combined.update(d)

    keys = list(combined.keys())
    values = [v if isinstance(v, (list, tuple)) else [v] for v in combined.values()]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


# ---------------------------------------------------------------------------
# Reproducibility helpers
# ---------------------------------------------------------------------------


def safesave(
    filename: str,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    compression: Optional[str] = "gzip",
    include_git: bool = False,
    subdir: Optional[str] = None,
) -> Path:
    """
    Atomically save data to an HDF5 file, preventing partial-write corruption.

    Writes to a temporary file in the same directory, then renames it to the
    final destination.  If the write fails the original file (if any) is
    untouched.

    Args:
        filename: Target filename (without extension).
        data: Data dictionary (same contract as :func:`save_data`).
        metadata: Optional metadata dictionary.
        compression: HDF5 compression algorithm.
        include_git: Embed git state in metadata.
        subdir: Subdirectory within ``data/``.

    Returns:
        Path to the saved file.
    """
    if not filename.endswith(".h5"):
        filename = filename + ".h5"

    if subdir:
        target_dir = datadir(subdir, create=True)
    else:
        target_dir = datadir(create=True)

    final_path = target_dir / filename

    # Write to a sibling temp file, then atomically rename to final_path.
    tmp_fd, tmp_path_str = tempfile.mkstemp(dir=target_dir, suffix=".tmp.h5")
    tmp_path = Path(tmp_path_str)
    try:
        os.close(tmp_fd)
        # Build metadata the same way save_data does
        meta = dict(metadata or {})
        meta.setdefault("created_at", datetime.now().isoformat())
        meta.setdefault("created_by", "PyWatson/safesave")
        meta["script"] = _get_script_info()
        if include_git:
            git_info = {
                "gitcommit": current_git_commit(),
                "gitbranch": _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]),
            }
            meta.update({k: v for k, v in git_info.items() if v is not None})
        with h5py.File(tmp_path, "w") as f:
            f.attrs["metadata"] = json.dumps(meta)
            for key, value in data.items():
                _save_value_to_hdf5(f, key, value, compression)
        # POSIX rename is atomic within the same filesystem
        tmp_path.replace(final_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise

    return final_path


@contextmanager
def tmpsave(
    data: Dict[str, Any],
    suffix: str = ".h5",
    compression: Optional[str] = "gzip",
) -> Generator[Path, None, None]:
    """
    Context manager: save data to a temporary file, yield its path, then delete it.

    Useful for testing or one-off intermediate results that should not persist.

    Args:
        data: Data dictionary.
        suffix: File suffix (default ``".h5"``).
        compression: HDF5 compression.

    Yields:
        :class:`~pathlib.Path` of the temporary HDF5 file.

    Example:
        >>> with tmpsave({"x": np.eye(3)}) as p:
        ...     result = load_data(str(p))
    """
    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(tmp_path_str)
    try:
        os.close(tmp_fd)
        tmp_path.unlink()  # h5py must create the file itself
        with h5py.File(tmp_path, "w") as f:
            f.attrs["metadata"] = json.dumps(
                {"created_at": datetime.now().isoformat(), "created_by": "PyWatson/tmpsave"}
            )
            for key, value in data.items():
                _save_value_to_hdf5(f, key, value, compression)
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def snapshot_environment() -> Dict[str, Any]:
    """
    Capture the current Python environment for reproducibility.

    Returns a dictionary with Python version, platform, and installed packages
    (as reported by ``pip list``).  Safe to embed in HDF5 metadata.

    Returns:
        Dictionary with keys ``python_version``, ``platform``, ``packages``.
    """
    packages: list[str] = []
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            packages = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "captured_at": datetime.now().isoformat(),
    }


def set_random_seed(seed: int) -> Dict[str, int]:
    """
    Set random seeds for reproducibility and return a metadata-ready dict.

    Sets seeds for Python's built-in :mod:`random` module and NumPy.  If
    PyTorch is installed its seed is set too.

    Args:
        seed: Integer seed value.

    Returns:
        Dictionary ``{"random_seed": seed}`` suitable for passing as metadata.

    Example:
        >>> params = {"N": 100, **set_random_seed(42)}
        >>> tagsave(savename(params), run_simulation(params), tags=params)
    """
    import random

    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch  # type: ignore[import]
        torch.manual_seed(seed)
    except ImportError:
        pass

    return {"random_seed": seed}


# ---------------------------------------------------------------------------
# Variant formats: NumPy NPZ
# ---------------------------------------------------------------------------


def save_npz(
    data: Dict[str, Any],
    filename: str,
    metadata: Optional[Dict[str, Any]] = None,
    compressed: bool = True,
    subdir: Optional[str] = None,
) -> Path:
    """
    Save arrays to a NumPy ``.npz`` archive in the data directory.

    Args:
        data: Dictionary of arrays (values are passed to :func:`numpy.savez`).
        filename: Filename without extension.
        metadata: Metadata dict stored as a ``_metadata.json`` entry.
        compressed: Use :func:`numpy.savez_compressed` when ``True``
                    (default) else :func:`numpy.savez`.
        subdir: Subdirectory within ``data/``.

    Returns:
        Path to the saved ``.npz`` file.
    """
    if filename.endswith(".npz"):
        filename = filename[:-4]

    if subdir:
        filepath = datadir(subdir, create=True) / (filename + ".npz")
    else:
        filepath = datadir(create=True) / (filename + ".npz")

    save_fn = np.savez_compressed if compressed else np.savez

    arrays = {k: np.asarray(v) for k, v in data.items() if not k.startswith("_")}
    if metadata is not None:
        arrays["_metadata_json"] = np.array([json.dumps(metadata).encode("utf-8")])

    save_fn(str(filepath)[:-4], **arrays)  # numpy appends .npz automatically
    # numpy.savez appends .npz to the given path, so `filepath` already points there
    return filepath


def load_npz(
    filename: str,
    subdir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load a NumPy ``.npz`` archive from the data directory.

    Args:
        filename: Filename with or without ``.npz`` extension.
        subdir: Subdirectory within ``data/``.

    Returns:
        Dictionary of arrays plus ``_metadata`` if present.
    """
    if not filename.endswith(".npz"):
        filename = filename + ".npz"

    if subdir:
        filepath = datadir(subdir, create=False) / filename
    else:
        filepath = datadir(create=False) / filename

    if not filepath.exists():
        raise FileNotFoundError(f"NPZ file not found: {filepath}")

    npz = np.load(str(filepath), allow_pickle=False)
    result: Dict[str, Any] = {}
    for key in npz.files:
        if key == "_metadata_json":
            try:
                result["_metadata"] = json.loads(npz[key][0].decode("utf-8"))
            except Exception:
                pass
        else:
            result[key] = npz[key]
    return result


# ---------------------------------------------------------------------------
# Variant formats: Zarr
# ---------------------------------------------------------------------------


def save_zarr(
    data: Dict[str, Any],
    filename: str,
    metadata: Optional[Dict[str, Any]] = None,
    compression: str = "blosc",
    subdir: Optional[str] = None,
) -> Path:
    """
    Save arrays to a Zarr store in the data directory.

    Requires the ``zarr`` package (``uv add zarr`` or ``pip install zarr``).

    Args:
        data: Dictionary of arrays.
        filename: Directory name for the Zarr store (without extension).
        metadata: Metadata dict stored in the Zarr store's ``.zattrs``.
        compression: Zarr compressor name (``"blosc"``/``"gzip"``/``"zstd"``).
        subdir: Subdirectory within ``data/``.

    Returns:
        Path to the Zarr store directory.
    """
    if not _HAS_ZARR:
        raise ImportError(
            "zarr is required for save_zarr/load_zarr. "
            "Install with: uv add zarr  or  pip install zarr"
        )

    if filename.endswith(".zarr"):
        filename = filename[:-5]

    if subdir:
        store_path = datadir(subdir, create=True) / (filename + ".zarr")
    else:
        store_path = datadir(create=True) / (filename + ".zarr")

    import numcodecs  # type: ignore[import]

    compressor = {"blosc": numcodecs.Blosc(), "gzip": numcodecs.GZip(), "zstd": numcodecs.Zstd()}.get(
        compression, numcodecs.Blosc()
    )

    z = zarr.open(str(store_path), mode="w")
    for key, value in data.items():
        z.create_dataset(key, data=np.asarray(value), compressor=compressor, overwrite=True)

    z.attrs["metadata"] = json.dumps(
        {**(metadata or {}), "created_at": datetime.now().isoformat(), "created_by": "PyWatson"}
    )
    return store_path


def load_zarr(
    filename: str,
    keys: Optional[list] = None,
    subdir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load arrays from a Zarr store in the data directory.

    Requires the ``zarr`` package.

    Args:
        filename: Directory name of the Zarr store (with or without ``.zarr``).
        keys: Optional list of dataset keys to load. ``None`` loads all.
        subdir: Subdirectory within ``data/``.

    Returns:
        Dictionary of arrays plus ``_metadata`` if present.
    """
    if not _HAS_ZARR:
        raise ImportError(
            "zarr is required for save_zarr/load_zarr. "
            "Install with: uv add zarr  or  pip install zarr"
        )

    if not filename.endswith(".zarr"):
        filename = filename + ".zarr"

    if subdir:
        store_path = datadir(subdir, create=False) / filename
    else:
        store_path = datadir(create=False) / filename

    if not store_path.exists():
        raise FileNotFoundError(f"Zarr store not found: {store_path}")

    z = zarr.open(str(store_path), mode="r")
    result: Dict[str, Any] = {}

    if "metadata" in z.attrs:
        try:
            result["_metadata"] = json.loads(z.attrs["metadata"])
        except (json.JSONDecodeError, KeyError):
            pass

    target_keys = keys if keys is not None else list(z.keys())
    for key in target_keys:
        if key in z:
            result[key] = z[key][:]

    return result

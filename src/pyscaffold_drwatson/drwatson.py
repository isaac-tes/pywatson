"""
PyWatson utilities - Combined path and data management.

This module provides utilities for path management and HDF5 data handling
with DrWatson.jl-inspired features including git tracking and smart caching.
"""

import numpy as np
import h5py
from pathlib import Path
from typing import Dict, Any, Optional, Union
import json
import subprocess
import inspect
from datetime import datetime


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


def get_project_dir(directory: str, *subdirs, create: bool = True) -> Path:
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


def savename(d: dict, suffix: str = ".h5", connector: str = "_", access=None) -> str:
    """
    Create a filename from a dictionary, similar to DrWatson's savename.
    
    Args:
        d: Dictionary with parameter values.
        suffix: File suffix to be appended.
        connector: String used to join key-value pairs.
        access: Function to access specific properties of values.
        
    Returns:
        Formatted filename.
        
    Example:
        >>> savename({"alpha": 0.5, "beta": 10}, suffix=".h5")
        'alpha=0.5_beta=10.h5'
    """
    if not d:
        return suffix
    
    # Sort keys for consistent naming
    sorted_keys = sorted(d.keys())
    
    parts = []
    for k in sorted_keys:
        v = d[k]
        if access is not None:
            v = access(v)
        parts.append(f"{k}={v}")
    
    return connector.join(parts) + suffix


# Git and script tracking utilities
def _run_git_command(cmd, cwd=None):
    """Run a git command and return its output."""
    if cwd is None:
        project_root = find_project_root()
        cwd = project_root if project_root else Path.cwd()
    
    try:
        result = subprocess.run(
            ["git"] + cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
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
    """Get information about the calling script."""
    frame = inspect.currentframe()
    try:
        # Get the frame of the caller (skip this function and save_data/tagsave)
        caller = inspect.getouterframes(frame)[2]
        script_absolute_path = Path(caller.filename).resolve()
        
        # Get the project root path
        project_root = find_project_root()
        
        # Try to get relative path from project root
        if project_root:
            try:
                script_relative_path = script_absolute_path.relative_to(project_root)
                return str(script_relative_path)
            except ValueError:
                pass
        
        # If not in project directory, use the full path
        return str(script_absolute_path)
    except (IndexError, AttributeError):
        return "unknown_script"
    finally:
        del frame  # Avoid reference cycles


# Data management functions
def save_data(data: Dict[str, Any], filename: str, 
              metadata: Optional[Dict[str, Any]] = None,
              compression: Optional[str] = 'gzip',
              include_git: bool = True) -> Path:
    """
    Save data to HDF5 file in the data directory with metadata and git information.
    
    Args:
        data: Dictionary of data to save (keys become HDF5 groups/datasets)
        filename: Name of the file (without extension)
        metadata: Optional metadata dictionary
        compression: Compression method ('gzip', 'lzf', 'szip', or None)
        include_git: Whether to include git information in metadata
        
    Returns:
        Path to the saved file
    """
    if not filename.endswith('.h5'):
        filename = filename + '.h5'
    
    filepath = datafile(filename)
    
    with h5py.File(filepath, 'w') as f:
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        # Add timestamp and creator info
        metadata['created_at'] = datetime.now().isoformat()
        metadata['created_by'] = 'PyWatson'
        metadata['script'] = _get_script_info()
        
        # Add git information if requested
        if include_git:
            git_info = {
                'gitcommit': current_git_commit(),
                'gitpatch': not git_status_clean() if git_status_clean() is not None else None,
                'gitbranch': _run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]),
            }
            # Only add non-None values
            git_info = {k: v for k, v in git_info.items() if v is not None}
            if git_info:
                metadata.update(git_info)
        
        # Save metadata as JSON string attribute
        f.attrs['metadata'] = json.dumps(metadata)
        
        # Save data
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                f.create_dataset(key, data=value, compression=compression)
            elif isinstance(value, (int, float, bool)):
                f.create_dataset(key, data=value)
            elif isinstance(value, str):
                # Handle string data properly for HDF5
                f.create_dataset(key, data=value.encode('utf-8') if value else b'')
            elif isinstance(value, (list, tuple)):
                f.create_dataset(key, data=np.array(value), compression=compression)
            elif isinstance(value, dict):
                # Create group for nested dictionaries
                group = f.create_group(key)
                _save_dict_to_group(group, value, compression)
            else:
                # Try to convert to numpy array
                try:
                    f.create_dataset(key, data=np.array(value), compression=compression)
                except Exception as e:
                    print(f"Warning: Could not save {key}: {e}")
    
    return filepath


def load_data(filename: str) -> Dict[str, Any]:
    """
    Load data from HDF5 file in the data directory.
    
    Args:
        filename: Name of the file (with or without .h5 extension)
        
    Returns:
        Dictionary containing the loaded data and metadata
    """
    if not filename.endswith('.h5'):
        filename = filename + '.h5'
    
    filepath = datafile(filename, create_dir=False)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    data = {}
    
    with h5py.File(filepath, 'r') as f:
        # Load metadata
        if 'metadata' in f.attrs:
            try:
                data['_metadata'] = json.loads(f.attrs['metadata'])
            except json.JSONDecodeError:
                data['_metadata'] = {'note': 'Could not parse metadata'}
        
        # Load datasets and groups
        for key in f.keys():
            data[key] = _load_item_from_hdf5(f[key])
    
    return data


def _save_dict_to_group(group: h5py.Group, data: Dict[str, Any], 
                       compression: Optional[str] = 'gzip'):
    """Recursively save dictionary to HDF5 group."""
    for key, value in data.items():
        if isinstance(value, np.ndarray):
            group.create_dataset(key, data=value, compression=compression)
        elif isinstance(value, (int, float, bool)):
            group.create_dataset(key, data=value)
        elif isinstance(value, str):
            group.create_dataset(key, data=value.encode('utf-8') if value else b'')
        elif isinstance(value, (list, tuple)):
            group.create_dataset(key, data=np.array(value), compression=compression)
        elif isinstance(value, dict):
            subgroup = group.create_group(key)
            _save_dict_to_group(subgroup, value, compression)
        else:
            try:
                group.create_dataset(key, data=np.array(value), compression=compression)
            except Exception as e:
                print(f"Warning: Could not save {key}: {e}")


def _load_item_from_hdf5(item) -> Any:
    """Load item from HDF5 file (dataset or group)."""
    if isinstance(item, h5py.Dataset):
        data = item[()]
        # Convert bytes to string if necessary
        if isinstance(data, bytes):
            return data.decode('utf-8')
        elif isinstance(data, np.ndarray) and data.dtype.kind == 'S':
            return data.astype(str)
        return data
    elif isinstance(item, h5py.Group):
        return {key: _load_item_from_hdf5(item[key]) for key in item.keys()}
    else:
        return item


def list_data_files() -> list[Path]:
    """List all HDF5 data files in the data directory."""
    data_dir = datadir(create=False)
    if not data_dir.exists():
        return []
    
    return list(data_dir.glob('*.h5'))


def data_info(filename: str) -> Dict[str, Any]:
    """
    Get information about a data file without loading all data.
    
    Args:
        filename: Name of the file (with or without .h5 extension)
        
    Returns:
        Dictionary with file information
    """
    if not filename.endswith('.h5'):
        filename = filename + '.h5'
    
    filepath = datafile(filename, create_dir=False)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    info = {
        'filepath': str(filepath),
        'size_bytes': filepath.stat().st_size,
        'modified': datetime.fromtimestamp(filepath.stat().st_mtime).isoformat(),
        'datasets': {},
        'groups': [],
        'metadata': {}
    }
    
    with h5py.File(filepath, 'r') as f:
        # Get metadata
        if 'metadata' in f.attrs:
            try:
                info['metadata'] = json.loads(f.attrs['metadata'])
            except json.JSONDecodeError:
                info['metadata'] = {'note': 'Could not parse metadata'}
        
        # Get dataset and group info
        def collect_info(name, obj):
            if isinstance(obj, h5py.Dataset):
                info['datasets'][name] = {
                    'shape': obj.shape,
                    'dtype': str(obj.dtype),
                    'size_bytes': obj.size * obj.dtype.itemsize
                }
            elif isinstance(obj, h5py.Group):
                info['groups'].append(name)
        
        f.visititems(collect_info)
    
    return info


def save_array(array: np.ndarray, name: str, 
               metadata: Optional[Dict[str, Any]] = None) -> Path:
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
    arrays = {k: v for k, v in data.items() if not k.startswith('_')}
    
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
    Save data with git information and custom tags (DrWatson.jl style).
    
    Args:
        filename: Name of the file (with or without .h5 extension)
        data: Data dictionary to save
        tags: Additional tags to include in metadata
        
    Returns:
        Path to the saved file
    """
    if tags is None:
        tags = {}
    
    # Merge data and tags
    all_data = {**data}
    
    # Save with git info and tags as metadata
    return save_data(all_data, filename, metadata=tags, include_git=True)


def produce_or_load(filename: str, producing_function, *args, **kwargs):
    """
    Load existing data or produce and save new data (DrWatson.jl style).
    
    Args:
        filename: Name of the file to load from or save to
        producing_function: Function that produces the data if file doesn't exist
        *args: Positional arguments for producing_function
        **kwargs: Keyword arguments for producing_function
        
    Returns:
        Tuple of (data_dict, existed) where existed is bool indicating if file existed
    """
    if not filename.endswith('.h5'):
        filename = filename + '.h5'
    
    filepath = datafile(filename, create_dir=False)
    
    if filepath.exists():
        return load_data(filename), True
    
    data = producing_function(*args, **kwargs)
    
    if not isinstance(data, dict):
        raise TypeError("producing_function must return a dictionary")
    
    tagsave(filename, data)
    return data, False


def collect_results(folder_path: Optional[str] = None) -> list[Dict[str, Any]]:
    """
    Collect all results from .h5 files in a folder.
    
    Args:
        folder_path: Path to the folder (defaults to data directory)
        
    Returns:
        List of dictionaries, each containing data from one file
    """
    if folder_path is None:
        folder = datadir(create=False)
    else:
        folder = Path(folder_path)
    
    if not folder.exists():
        return []
    
    results = []
    
    for filepath in folder.glob('**/*.h5'):
        try:
            data = load_data(filepath.name)
            # Add the file path
            data['_filepath'] = str(filepath)
            results.append(data)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    return results
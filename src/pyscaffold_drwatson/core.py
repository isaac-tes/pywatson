"""
PyScaffold DrWatson - A Python project scaffolding tool inspired by DrWatson.jl

This tool creates a complete Python project structure with modern tooling (uv),
comprehensive documentation, example code, and tests.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import click
import yaml
from rich.console import Console
from rich.progress import track
from rich.prompt import Confirm

__version__ = "0.1.0"

console = Console()


class ProjectScaffolder:
    """Main class for scaffolding Python projects."""

    def __init__(self, project_name: str, project_path: Path):
        self.project_name = project_name
        self.project_path = project_path
        self.package_name = project_name.lower().replace("-", "_").replace(" ", "_")
        
    def create_project_structure(self) -> None:
        """Create the basic directory structure."""
        directories = [
            "src",
            f"src/{self.package_name}",
            "scripts",
            "notebooks",
            "tests", 
            "plots",
            "data",
            "docs",
        ]
        
        for directory in track(directories, description="Creating directories..."):
            (self.project_path / directory).mkdir(parents=True, exist_ok=True)

    def initialize_uv_project(self) -> None:
        """Initialize the uv project."""
        console.print("🔧 Initializing uv project...", style="bold blue")
        
        # Change to project directory and run uv init --lib
        original_cwd = Path.cwd()
        try:
            os.chdir(self.project_path)
            result = subprocess.run(
                ["uv", "init", "--lib", "--name", self.project_name],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                console.print(f"❌ Error initializing uv project: {result.stderr}", style="bold red")
                raise RuntimeError("Failed to initialize uv project")
                
        finally:
            os.chdir(original_cwd)

    def add_dependencies(self, dependencies: List[str], dev_dependencies: List[str] = None) -> None:
        """Add dependencies using uv."""
        original_cwd = Path.cwd()
        try:
            os.chdir(self.project_path)
            
            if dependencies:
                console.print("📦 Adding dependencies...", style="bold blue")
                failed_deps = []
                for dep in track(dependencies, description="Installing packages..."):
                    try:
                        result = subprocess.run(["uv", "add", dep], capture_output=True, check=False)
                        if result.returncode != 0:
                            console.print(f"⚠️  Warning: Failed to install {dep}: {result.stderr.decode()}", style="yellow")
                            failed_deps.append(dep)
                    except Exception as e:
                        console.print(f"⚠️  Warning: Error installing {dep}: {e}", style="yellow")
                        failed_deps.append(dep)
                
                if failed_deps:
                    console.print(f"⚠️  Some dependencies failed to install: {failed_deps}", style="yellow")
                    console.print("You can manually install them later with: uv add <package>", style="yellow")
            
            if dev_dependencies:
                console.print("🔧 Adding development dependencies...", style="bold blue")
                for dep in track(dev_dependencies, description="Installing dev packages..."):
                    subprocess.run(["uv", "add", "--group", "dev", dep], capture_output=True, check=True)
                    
        finally:
            os.chdir(original_cwd)

    def create_source_files(self, author_name: str, author_email: str) -> None:
        """Create source code files with templates."""
        
        # Create __init__.py
        init_content = f'''"""
{self.project_name.title().replace("-", " ").replace("_", " ")}

A Python library for scientific computing and data analysis with built-in
path management and HDF5 data handling capabilities.
"""

from .core import (
    hello_world,
    create_example_data,
    analyze_data,
)
from .drwatson import (
    # Path management
    datadir, plotsdir, scriptsdir, notebooksdir, docsdir, testsdir, srcdir, projectdir,
    datafile, plotfile, scriptfile, notebookfile, savename,
    # Data management
    save_data, load_data, save_array, load_array, data_info, list_data_files,
    tagsave, produce_or_load, collect_results
)

__version__ = "0.1.0"
__author__ = "{author_name}"
__email__ = "{author_email}"

__all__ = [
    "hello_world",
    "create_example_data", 
    "analyze_data",
    # Path management
    "datadir", "plotsdir", "scriptsdir", "notebooksdir", "docsdir", "testsdir", "srcdir", "projectdir",
    "datafile", "plotfile", "scriptfile", "notebookfile", "savename",
    # Data management
    "save_data", "load_data", "save_array", "load_array", "data_info", "list_data_files",
    "tagsave", "produce_or_load", "collect_results",
]


def hello() -> str:
    """Legacy hello function for backwards compatibility."""
    return hello_world()
'''
        
        (self.project_path / "src" / self.package_name / "__init__.py").write_text(init_content)

        # Create core.py
        core_content = f'''"""
Core functionality for {self.project_name}.

This module provides the main functionality for data analysis and processing.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Optional, Dict, Any
from pathlib import Path


def hello_world() -> str:
    """
    A simple hello world function to verify the package installation.
    
    Returns:
        str: A greeting message.
    """
    return f"Hello from {self.package_name}!"


def create_example_data(size: Tuple[int, int] = (100, 2), 
                       data_type: str = "random") -> np.ndarray:
    """
    Create example data for analysis and testing.
    
    Args:
        size: Tuple of (rows, columns) for the data dimensions.
        data_type: Type of data to create ("random", "linear", "sinusoidal").
        
    Returns:
        np.ndarray: A 2D array containing the example data.
        
    Raises:
        ValueError: If data_type is not supported.
    """
    if data_type not in ["random", "linear", "sinusoidal"]:
        raise ValueError(f"Unsupported data type: {{data_type}}")
    
    rows, cols = size
    
    if data_type == "random":
        return np.random.randn(rows, cols)
    elif data_type == "linear":
        x = np.linspace(0, 10, rows)
        data = np.column_stack([x + np.random.normal(0, 0.1, rows) for _ in range(cols)])
        return data
    elif data_type == "sinusoidal":
        x = np.linspace(0, 4*np.pi, rows)
        data = np.column_stack([np.sin(x + i*np.pi/4) + np.random.normal(0, 0.1, rows) 
                               for i in range(cols)])
        return data


def analyze_data(data: np.ndarray, method: str = "basic") -> Dict[str, Any]:
    """
    Analyze data using various statistical methods.
    
    Args:
        data: 2D numpy array to analyze.
        method: Analysis method ("basic", "correlation", "pca").
        
    Returns:
        dict: Dictionary containing analysis results.
    """
    results = {{}}
    
    if method == "basic":
        results["mean"] = np.mean(data, axis=0)
        results["std"] = np.std(data, axis=0)
        results["min"] = np.min(data, axis=0)
        results["max"] = np.max(data, axis=0)
        
    elif method == "correlation":
        results["correlation_matrix"] = np.corrcoef(data.T)
        results["mean"] = np.mean(data, axis=0)
        results["std"] = np.std(data, axis=0)
        
    elif method == "pca":
        # Simple PCA implementation
        centered_data = data - np.mean(data, axis=0)
        cov_matrix = np.cov(centered_data.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
        
        # Sort by eigenvalues (descending)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        results["eigenvalues"] = eigenvalues
        results["eigenvectors"] = eigenvectors
        results["explained_variance_ratio"] = eigenvalues / np.sum(eigenvalues)
        
    else:
        raise ValueError(f"Unknown analysis method: {{method}}")
    
    return results


def simple_plot(data: np.ndarray, save_path: Optional[Path] = None) -> None:
    """
    Create a simple plot of 2D data.
    
    Args:
        data: 2D numpy array to plot.
        save_path: Optional path to save the plot.
    """
    if data.shape[1] < 2:
        raise ValueError("Data must have at least 2 columns for plotting")
        
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Scatter plot
    ax1.scatter(data[:, 0], data[:, 1], alpha=0.6)
    ax1.set_xlabel("Column 1")
    ax1.set_ylabel("Column 2")
    ax1.set_title("Scatter Plot")
    
    # Histograms
    ax2.hist(data[:, 0], alpha=0.7, label="Column 1", bins=30)
    ax2.hist(data[:, 1], alpha=0.7, label="Column 2", bins=30)
    ax2.set_xlabel("Value")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Histograms")
    ax2.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def compute_basic_stats(data: np.ndarray) -> Dict[str, Any]:
    """
    Compute basic statistics for data.
    
    Args:
        data: Input data array.
        
    Returns:
        Dictionary with basic statistics.
    """
    return {{
        "shape": data.shape,
        "mean": np.mean(data, axis=0),
        "median": np.median(data, axis=0),
        "std": np.std(data, axis=0),
        "min": np.min(data, axis=0),
        "max": np.max(data, axis=0),
    }}



'''
        
        (self.project_path / "src" / self.package_name / "core.py").write_text(core_content)
        
        # Create paths.py
        paths_content = '''"""
Path management utilities for this project.

This module provides utilities to find and reference project directories
(data, plots, scripts, notebooks, etc.) from anywhere within the project workspace.
"""

from pathlib import Path
from typing import Optional, Union


def find_project_root(start_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """
    Find the project root directory by looking for pyproject.toml.
    
    Args:
        start_path: Starting directory to search from. Defaults to current directory.
        
    Returns:
        Path to project root or None if not found.
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)
    
    current = start_path.resolve()
    
    # Walk up the directory tree looking for pyproject.toml
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    
    return None


def get_project_dir(directory: str, create: bool = True) -> Path:
    """
    Get path to a project directory (data, plots, scripts, etc.).
    
    Args:
        directory: Directory name (e.g., 'data', 'plots', 'scripts', 'notebooks')
        create: Whether to create the directory if it doesn't exist
        
    Returns:
        Path to the requested directory
        
    Raises:
        RuntimeError: If project root cannot be found
    """
    project_root = find_project_root()
    
    if project_root is None:
        raise RuntimeError(
            "Could not find project root. Make sure you're in a project "
            "(should contain pyproject.toml)"
        )
    
    dir_path = project_root / directory
    
    if create and not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dir_path


def datadir(create: bool = True) -> Path:
    """Get path to data directory."""
    return get_project_dir("data", create=create)


def plotsdir(create: bool = True) -> Path:
    """Get path to plots directory."""
    return get_project_dir("plots", create=create)


def scriptsdir(create: bool = True) -> Path:
    """Get path to scripts directory."""
    return get_project_dir("scripts", create=create)


def notebooksdir(create: bool = True) -> Path:
    """Get path to notebooks directory."""
    return get_project_dir("notebooks", create=create)


def docsdir(create: bool = True) -> Path:
    """Get path to docs directory."""
    return get_project_dir("docs", create=create)


def testsdir(create: bool = True) -> Path:
    """Get path to tests directory."""
    return get_project_dir("tests", create=create)


def srcdir(create: bool = True) -> Path:
    """Get path to src directory."""
    return get_project_dir("src", create=create)


def projectdir() -> Path:
    """Get path to project root directory."""
    project_root = find_project_root()
    if project_root is None:
        raise RuntimeError(
            "Could not find project root. Make sure you're in a project "
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
'''
        
        (self.project_path / "src" / self.package_name / "paths.py").write_text(paths_content)
        
        # Create data.py
        data_content = '''"""
Data management utilities with HDF5 support.

This module provides utilities for saving and loading data in HDF5 format,
which is efficient for scientific data and maintains metadata.
"""

import numpy as np
import h5py
from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime

from .paths import datadir, datafile


def save_data(data: Dict[str, Any], filename: str, 
              metadata: Optional[Dict[str, Any]] = None,
              compression: Optional[str] = 'gzip') -> Path:
    """
    Save data to HDF5 file in the data directory.
    
    Args:
        data: Dictionary of data to save (keys become HDF5 groups/datasets)
        filename: Name of the file (without extension)
        metadata: Optional metadata dictionary
        compression: Compression method ('gzip', 'lzf', 'szip', or None)
        
    Returns:
        Path to the saved file
    """
    if not filename.endswith('.h5'):
        filename = filename + '.h5'
    
    filepath = datafile(filename)
    
    with h5py.File(filepath, 'w') as f:
        # Save metadata
        if metadata is None:
            metadata = {}
        
        # Add timestamp
        metadata['created_at'] = datetime.now().isoformat()
        metadata['created_by'] = 'PyScaffold DrWatson Generated Project'
        
        # Save metadata as JSON string attribute
        f.attrs['metadata'] = json.dumps(metadata)
        
        # Save data
        for key, value in data.items():
            if isinstance(value, np.ndarray):
                f.create_dataset(key, data=value, compression=compression)
            elif isinstance(value, (int, float, bool, str)):
                f.create_dataset(key, data=value)
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
        elif isinstance(value, (int, float, bool, str)):
            group.create_dataset(key, data=value)
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
'''
        
        (self.project_path / "src" / self.package_name / "data.py").write_text(data_content)
        
        # Replace separate files with combined drwatson.py approach
        self._replace_with_combined_drwatson()

    def _replace_with_combined_drwatson(self) -> None:
        """Replace separate paths.py and data.py with combined drwatson.py file."""
        import shutil
        
        # Copy our working drwatson.py file
        source_drwatson = Path(__file__).parent / "drwatson.py"
        target_drwatson = self.project_path / "src" / self.package_name / "drwatson.py"
        
        if source_drwatson.exists():
            shutil.copy2(source_drwatson, target_drwatson)
            
            # Remove the old separate files
            paths_file = self.project_path / "src" / self.package_name / "paths.py"
            data_file = self.project_path / "src" / self.package_name / "data.py"
            
            if paths_file.exists():
                paths_file.unlink()
            if data_file.exists():
                data_file.unlink()
            
            # Update the __init__.py to use the combined approach
            init_content = f'''"""
{self.project_name.title().replace("-", " ").replace("_", " ")}

A Python library for scientific computing and data analysis with built-in
path management and HDF5 data handling capabilities, inspired by DrWatson.jl.
"""

from .core import hello_world, create_example_data, analyze_data
from .drwatson import (
    # Path management
    datadir, plotsdir, scriptsdir, notebooksdir, docsdir, testsdir, srcdir, projectdir,
    datafile, plotfile, scriptfile, notebookfile, savename,
    # Data management
    save_data, load_data, save_array, load_array, data_info, list_data_files,
    tagsave, produce_or_load, collect_results
)

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "hello_world", "create_example_data", "analyze_data",
    # Path management
    "datadir", "plotsdir", "scriptsdir", "notebooksdir", "docsdir", "testsdir", "srcdir", "projectdir",
    "datafile", "plotfile", "scriptfile", "notebookfile", "savename",
    # Data management
    "save_data", "load_data", "save_array", "load_array", "data_info", "list_data_files",
    "tagsave", "produce_or_load", "collect_results"
]


def hello() -> str:
    """Legacy hello function for backwards compatibility."""
    return hello_world()
'''
            (self.project_path / "src" / self.package_name / "__init__.py").write_text(init_content)

    def create_test_files(self) -> None:
        """Create comprehensive test files."""
        
        # Create __init__.py for tests
        (self.project_path / "tests" / "__init__.py").write_text("# Tests package\n")
        
        # Create test_core.py
        test_content = f'''"""
Tests for the {self.package_name} library.
"""

import numpy as np
import pytest
from pathlib import Path
import tempfile
from {self.package_name} import hello_world, create_example_data, analyze_data


def test_hello_world():
    """Test the hello_world function."""
    result = hello_world()
    assert isinstance(result, str)
    assert "{self.package_name}" in result


def test_create_example_data_random():
    """Test creation of random data."""
    size = (50, 3)
    data = create_example_data(size, "random")
    
    assert data.shape == size
    assert isinstance(data, np.ndarray)


def test_create_example_data_linear():
    """Test creation of linear data."""
    size = (30, 2)
    data = create_example_data(size, "linear")
    
    assert data.shape == size
    assert isinstance(data, np.ndarray)


def test_create_example_data_sinusoidal():
    """Test creation of sinusoidal data."""
    size = (40, 2)
    data = create_example_data(size, "sinusoidal")
    
    assert data.shape == size
    assert isinstance(data, np.ndarray)


def test_create_example_data_invalid():
    """Test that invalid data type raises ValueError."""
    with pytest.raises(ValueError):
        create_example_data((10, 2), "invalid")


def test_analyze_data_basic():
    """Test basic data analysis."""
    data = np.random.randn(100, 3)
    results = analyze_data(data, "basic")
    
    assert "mean" in results
    assert "std" in results
    assert "min" in results
    assert "max" in results
    assert len(results["mean"]) == 3


def test_analyze_data_correlation():
    """Test correlation analysis."""
    data = np.random.randn(50, 2)
    results = analyze_data(data, "correlation")
    
    assert "correlation_matrix" in results
    assert "mean" in results
    assert "std" in results
    assert results["correlation_matrix"].shape == (2, 2)


def test_analyze_data_pca():
    """Test PCA analysis."""
    data = np.random.randn(100, 3)
    results = analyze_data(data, "pca")
    
    assert "eigenvalues" in results
    assert "eigenvectors" in results
    assert "explained_variance_ratio" in results
    assert len(results["eigenvalues"]) == 3


def test_analyze_data_invalid():
    """Test that invalid method raises ValueError."""
    data = np.random.randn(10, 2)
    with pytest.raises(ValueError):
        analyze_data(data, "invalid")



'''
        
        (self.project_path / "tests" / "test_core.py").write_text(test_content)

    def create_example_script(self) -> None:
        """Create simplified example scripts."""
        
        # Create data generation script
        data_script_content = f'''#!/usr/bin/env python3
"""
Example script: Generate and save data using HDF5 format.

This script demonstrates:
1. Creating example data with the core module
2. Using path management to save to data directory
3. Saving data in HDF5 format with metadata
"""

from {self.package_name} import create_example_data, save_data, datafile
import numpy as np


def main():
    """Generate and save example datasets."""
    print("📊 Generating Example Data")
    print("=" * 40)
    
    # Create different types of data
    print("\\n1. Creating datasets...")
    random_data = create_example_data((200, 3), "random")
    linear_data = create_example_data((150, 2), "linear") 
    sinusoidal_data = create_example_data((180, 2), "sinusoidal")
    
    print(f"   Random data: {{random_data.shape}}")
    print(f"   Linear data: {{linear_data.shape}}")
    print(f"   Sinusoidal data: {{sinusoidal_data.shape}}")
    
    # Save data with metadata
    print("\\n2. Saving data to HDF5 files...")
    
    # Save random data
    metadata_random = {{
        "description": "Random normally distributed data",
        "data_type": "random",
        "n_samples": random_data.shape[0],
        "n_features": random_data.shape[1]
    }}
    
    file_path = save_data(
        {{"random_data": random_data}},
        "example_random_data",
        metadata=metadata_random
    )
    print(f"   Saved random data: {{file_path}}")
    
    # Save linear data  
    metadata_linear = {{
        "description": "Linear data with noise",
        "data_type": "linear",
        "n_samples": linear_data.shape[0],
        "n_features": linear_data.shape[1]
    }}
    
    file_path = save_data(
        {{"linear_data": linear_data}},
        "example_linear_data", 
        metadata=metadata_linear
    )
    print(f"   Saved linear data: {{file_path}}")
    
    # Save sinusoidal data
    metadata_sin = {{
        "description": "Sinusoidal data with noise",
        "data_type": "sinusoidal", 
        "n_samples": sinusoidal_data.shape[0],
        "n_features": sinusoidal_data.shape[1]
    }}
    
    file_path = save_data(
        {{"sinusoidal_data": sinusoidal_data}},
        "example_sinusoidal_data",
        metadata=metadata_sin
    )
    print(f"   Saved sinusoidal data: {{file_path}}")
    
    print("\\n✅ Data generation complete!")
    print("   Run the analysis script next: python scripts/analyze_data.py")


if __name__ == "__main__":
    main()
'''
        
        (self.project_path / "scripts" / "generate_data.py").write_text(data_script_content)
        
        # Create analysis script
        analysis_script_content = f'''#!/usr/bin/env python3
"""
Example script: Load data and create plots.

This script demonstrates:
1. Loading data from HDF5 files
2. Performing analysis with the core module
3. Creating and saving plots to the plots directory
"""

from {self.package_name} import load_data, analyze_data, plotfile
import matplotlib.pyplot as plt
import numpy as np


def main():
    """Load data and create analysis plots."""
    print("📈 Data Analysis and Plotting")
    print("=" * 40)
    
    # Load data files
    print("\\n1. Loading data from HDF5 files...")
    
    try:
        random_data_dict = load_data("example_random_data")
        linear_data_dict = load_data("example_linear_data") 
        sinusoidal_data_dict = load_data("example_sinusoidal_data")
        
        print("   ✅ All data files loaded successfully")
        
        # Extract data arrays
        random_data = random_data_dict["random_data"]
        linear_data = linear_data_dict["linear_data"]
        sinusoidal_data = sinusoidal_data_dict["sinusoidal_data"]
        
        # Print metadata
        print("\\n2. Data metadata:")
        for name, data_dict in [("Random", random_data_dict), 
                               ("Linear", linear_data_dict),
                               ("Sinusoidal", sinusoidal_data_dict)]:
            if "_metadata" in data_dict:
                meta = data_dict["_metadata"]
                print(f"   {{name}}: {{meta.get('description', 'No description')}}")
        
    except FileNotFoundError:
        print("   ❌ Data files not found. Run generate_data.py first!")
        return
    
    # Perform analysis
    print("\\n3. Performing statistical analysis...")
    
    random_stats = analyze_data(random_data, "basic")
    linear_corr = analyze_data(linear_data, "correlation")
    sin_pca = analyze_data(sinusoidal_data, "pca")
    
    print(f"   Random data mean: {{np.round(random_stats['mean'], 3)}}")
    print(f"   Linear data correlation: {{np.round(linear_corr['correlation_matrix'][0,1], 3)}}")
    print(f"   Sinusoidal PCA variance ratio: {{np.round(sin_pca['explained_variance_ratio'][:2], 3)}}")
    
    # Create plots
    print("\\n4. Creating plots...")
    
    # Plot 1: Comparison of data types
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Random data
    axes[0].scatter(random_data[:, 0], random_data[:, 1], alpha=0.6, color='blue')
    axes[0].set_title('Random Data')
    axes[0].set_xlabel('Feature 1')
    axes[0].set_ylabel('Feature 2')
    axes[0].grid(True, alpha=0.3)
    
    # Linear data  
    axes[1].scatter(linear_data[:, 0], linear_data[:, 1], alpha=0.6, color='orange')
    axes[1].set_title('Linear Data')
    axes[1].set_xlabel('Feature 1')
    axes[1].set_ylabel('Feature 2')
    axes[1].grid(True, alpha=0.3)
    
    # Sinusoidal data
    axes[2].scatter(sinusoidal_data[:, 0], sinusoidal_data[:, 1], alpha=0.6, color='green')
    axes[2].set_title('Sinusoidal Data')
    axes[2].set_xlabel('Feature 1') 
    axes[2].set_ylabel('Feature 2')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save using path management
    plot_path = plotfile("data_comparison.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   Saved comparison plot: {{plot_path}}")
    
    # Plot 2: Statistical summary
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Histograms
    axes[0, 0].hist(random_data[:, 0], bins=30, alpha=0.7, color='blue', label='Random')
    axes[0, 0].hist(linear_data[:, 0], bins=30, alpha=0.7, color='orange', label='Linear')  
    axes[0, 0].hist(sinusoidal_data[:, 0], bins=30, alpha=0.7, color='green', label='Sinusoidal')
    axes[0, 0].set_title('Feature 1 Distributions')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Box plots
    data_for_box = [random_data[:, 0], linear_data[:, 0], sinusoidal_data[:, 0]]
    axes[0, 1].boxplot(data_for_box, labels=['Random', 'Linear', 'Sinusoidal'])
    axes[0, 1].set_title('Feature 1 Box Plots')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Correlation matrix for linear data
    im = axes[1, 0].imshow(linear_corr['correlation_matrix'], cmap='coolwarm', vmin=-1, vmax=1)
    axes[1, 0].set_title('Linear Data Correlation Matrix')
    plt.colorbar(im, ax=axes[1, 0])
    
    # PCA explained variance
    axes[1, 1].bar(range(len(sin_pca['explained_variance_ratio'])), 
                   sin_pca['explained_variance_ratio'])
    axes[1, 1].set_title('Sinusoidal Data PCA Explained Variance')
    axes[1, 1].set_xlabel('Principal Component')
    axes[1, 1].set_ylabel('Explained Variance Ratio')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save statistical summary plot
    stats_plot_path = plotfile("statistical_summary.png")
    plt.savefig(stats_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   Saved statistical summary: {{stats_plot_path}}")
    
    print("\\n✅ Analysis complete!")
    print(f"   Check the plots directory for visualizations")


if __name__ == "__main__":
    main()
'''
        
        (self.project_path / "scripts" / "analyze_data.py").write_text(analysis_script_content)

    def create_readme(self, author_name: str, author_email: str, 
                     dependencies: List[str], description: str) -> None:
        """Create a comprehensive README.md file."""
        
        deps_list = "\n".join([f"- **{dep.split('==')[0] if '==' in dep else dep.split('>=')[0] if '>=' in dep else dep}**: {dep}" for dep in dependencies])
        
        readme_content = f'''# {self.project_name.title().replace("-", " ").replace("_", " ")}

{description}

## Project Structure

This project follows a structured organization inspired by DrWatson.jl:

```
{self.project_name}/
├── src/                 # Source code for the library
│   └── {self.package_name}/
├── scripts/             # Standalone scripts and utilities
├── notebooks/           # Jupyter notebooks for analysis and examples
├── tests/               # Unit tests
├── plots/               # Generated plots and figures
├── data/                # Data files (raw and processed)
├── docs/                # Documentation
├── pyproject.toml       # Project configuration and dependencies
└── README.md           # This file
```

## Installation and Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and virtual environment handling. Follow these steps to set up the project:

### Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) package manager

Install uv if you haven't already:
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Setting up the project

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd {self.project_name}
   ```

2. **Install dependencies and activate the environment:**
   ```bash
   # This will create a virtual environment and install all dependencies
   uv sync
   ```

3. **Activate the virtual environment:**
   ```bash
   # Activate the environment
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\\Scripts\\activate     # On Windows
   ```

### Environment Management

#### Activating the Environment
```bash
# Method 1: Traditional activation
source .venv/bin/activate  # Unix/macOS
.venv\\Scripts\\activate     # Windows

# Method 2: Using uv run (runs commands in the project environment)
uv run python script.py
uv run jupyter notebook
```

#### Deactivating the Environment
```bash
deactivate
```

## Quick Guide to uv

### Basic Commands

- **Create a new project:** `uv init --lib project-name`
- **Add dependencies:** `uv add package-name`
- **Add development dependencies:** `uv add --group dev package-name`
- **Remove dependencies:** `uv remove package-name`
- **Install project dependencies:** `uv sync`
- **Run commands in the project environment:** `uv run command`
- **Show project info:** `uv tree`
- **Lock dependencies:** `uv lock`

### Working with Dependencies

```bash
# Add a specific version
uv add "numpy==1.24.0"

# Add from PyPI
uv add requests

# Add development dependencies
uv add --group dev pytest

# Install from requirements.txt
uv add -r requirements.txt
```

### Running Code

```bash
# Run Python scripts
uv run python src/your_script.py

# Run Jupyter notebooks
uv run jupyter notebook

# Run tests
uv run pytest

# Run any command in the virtual environment
uv run <command>
```

## Usage

### Running the Example Analysis
```bash
uv run python scripts/example_analysis.py
```

### Running Jupyter Notebooks
```bash
uv run jupyter notebook
# Navigate to the notebooks/ directory for examples
```

### Running Tests
```bash
uv run pytest tests/ -v
```

### Using the Library

```python
from {self.package_name} import create_example_data, analyze_data

# Create example data
data = create_example_data((100, 3), "random")

# Perform basic analysis
results = analyze_data(data, "basic")
print(f"Mean: {{results['mean']}}")

# Perform different types of analysis
correlation_results = analyze_data(data, "correlation")
pca_results = analyze_data(data, "pca")
```

## Development

### Installing in Development Mode
The package is automatically installed in development mode when you run `uv sync`. Any changes to the source code will be immediately available.

### Adding New Dependencies
```bash
# Add a new runtime dependency
uv add new-package

# Add a new development dependency
uv add --group dev new-dev-package
```

### Project Dependencies

This project includes the following key dependencies:
{deps_list}

## API Reference

### Core Functions

- `hello_world()`: Simple greeting function for testing installation
- `create_example_data(size, data_type)`: Generate example datasets
- `analyze_data(data, method)`: Perform various statistical analyses

### Analysis Functions

The package provides simple analysis functions:

- `compute_statistics()`: Calculate descriptive statistics
- `plot_data(save_path, plot_type)`: Create visualizations
- `export_results(filepath)`: Export analysis results

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `uv run pytest`
6. Submit a pull request

## Author

**{author_name}** - {author_email}

## License

[Add your license information here]
'''
        
        (self.project_path / "README.md").write_text(readme_content)

    def update_pyproject_toml(self, author_name: str, author_email: str, description: str) -> None:
        """Update pyproject.toml with project metadata."""
        pyproject_path = self.project_path / "pyproject.toml"
        
        if pyproject_path.exists():
            # Read current content
            content = pyproject_path.read_text()
            
            # Update description
            content = content.replace(
                'description = "Add your description here"',
                f'description = "{description}"'
            )
            
            # Write back
            pyproject_path.write_text(content)

    def create_gitignore(self) -> None:
        """Create a comprehensive .gitignore file."""
        gitignore_content = """# Python-generated files
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info

# Virtual environments
.venv
venv/
env/

# IDEs and editors
.vscode/
.idea/
*.swp
*.swo
*~

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Jupyter Notebook checkpoints
.ipynb_checkpoints

# pytest cache
.pytest_cache/

# Coverage reports
htmlcov/
.coverage
.coverage.*

# Environment files
.env
.env.local

# Data files (excluded by default for DrWatson workflow)
data/
# plots/

# Documentation builds
docs/_build/
docs/build/
"""
        
        (self.project_path / ".gitignore").write_text(gitignore_content)

    def create_example_notebook(self) -> None:
        """Create a simplified example Jupyter notebook for the project."""
        import json
        
        # Create a clean, simple notebook structure
        notebook_content = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        f"# {self.project_name.title()} - DrWatson Example\n",
                        "\n",
                        "This notebook demonstrates the main features of the DrWatson-style project structure."
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Import the project modules\n",
                        f"from {self.package_name} import (\n",
                        "    datadir, plotsdir, savename, save_data, load_data,\n",
                        "    create_example_data, analyze_data\n",
                        ")\n",
                        "import numpy as np\n",
                        "import matplotlib.pyplot as plt\n",
                        "\n",
                        "# Set up matplotlib for inline plotting\n",
                        "%matplotlib inline\n",
                        "\n",
                        "print('DrWatson-style workflow ready!')"
                    ]
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Path Management\n",
                        "\n",
                        "DrWatson provides convenient path management functions."
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Show project directories\n",
                        "print('Project directories:')\n",
                        "print(f'  Data directory: {datadir()}')\n",
                        "print(f'  Plots directory: {plotsdir()}')\n",
                        "\n",
                        "# Create a savename for files\n",
                        "params = {'alpha': 0.5, 'beta': 10, 'method': 'demo'}\n",
                        "filename = savename(params, suffix='.h5')\n",
                        "print(f'\\nGenerated filename: {filename}')"
                    ]
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Data Generation and Analysis"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Create example data\n",
                        "data = create_example_data((100, 2), 'random')\n",
                        "print(f'Generated data shape: {data.shape}')\n",
                        "\n",
                        "# Analyze the data\n",
                        "results = analyze_data(data, 'basic')\n",
                        "print('\\nAnalysis results:')\n",
                        "for key, value in results.items():\n",
                        "    print(f'  {key}: {value}')"
                    ]
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Data Saving and Loading"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Save data with metadata\n",
                        "sample_data = {'experiment_data': data}\n",
                        "metadata = {\n",
                        "    'experiment': 'notebook_demo',\n",
                        "    'date': '2025-09-26',\n",
                        "    'notes': 'Generated from example notebook'\n",
                        "}\n",
                        "\n",
                        "saved_path = save_data(sample_data, 'demo_experiment', metadata=metadata)\n",
                        "print(f'Data saved to: {saved_path}')\n",
                        "\n",
                        "# Load it back\n",
                        "loaded_data = load_data('demo_experiment')\n",
                        "print(f'\\nLoaded data keys: {list(loaded_data.keys())}')\n",
                        "print(f'Loaded data shape: {loaded_data[\"experiment_data\"].shape}')"
                    ]
                },
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "## Visualization"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Create a simple plot\n",
                        "plt.figure(figsize=(8, 6))\n",
                        "plt.scatter(data[:, 0], data[:, 1], alpha=0.6)\n",
                        "plt.title('Example Data Visualization')\n",
                        "plt.xlabel('Feature 1')\n",
                        "plt.ylabel('Feature 2')\n",
                        "plt.grid(True, alpha=0.3)\n",
                        "plt.show()\n",
                        "\n",
                        "print('Visualization complete!')"
                    ]
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "codemirror_mode": {
                        "name": "ipython",
                        "version": 3
                    },  
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.12.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        
        notebook_path = self.project_path / "notebooks" / f"{self.package_name}_example.ipynb"
        with open(notebook_path, 'w') as f:
            json.dump(notebook_content, f, indent=2)


def load_environment_file(env_file: Path) -> tuple[List[str], List[str]]:
    """Load dependencies from environment.yml file."""
    if not env_file.exists():
        return [], []
    
    with open(env_file) as f:
        env_data = yaml.safe_load(f)
    
    dependencies = []
    dev_dependencies = []
    
    # Process conda dependencies
    if 'dependencies' in env_data:
        for dep in env_data['dependencies']:
            if isinstance(dep, str) and not dep.startswith('python'):
                # Convert conda format (=) to pip format (>=) for better compatibility
                if '=' in dep and not dep.startswith('=') and '==' not in dep and '>=' not in dep:
                    dep = dep.replace('=', '>=', 1)
                dependencies.append(dep)
            elif isinstance(dep, dict) and 'pip' in dep:
                # Process pip dependencies
                for pip_dep in dep['pip']:
                    dependencies.append(pip_dep)
    
    # Add common dev dependencies
    dev_dependencies = ['pytest>=7.0.0', 'pytest-cov>=4.0.0']
    
    return dependencies, dev_dependencies


@click.command()
@click.argument('project_name')
@click.option('--path', '-p', type=click.Path(), default='.', 
              help='Directory to create the project in')
@click.option('--author-name', prompt='Author name', help='Author name')
@click.option('--author-email', prompt='Author email', help='Author email')
@click.option('--description', prompt='Project description', 
              help='Short project description')
@click.option('--env-file', type=click.Path(exists=True), 
              help='Environment file (environment.yml) to import dependencies from')
@click.option('--force', is_flag=True, help='Overwrite existing directory')
def create_project(project_name: str, path: str, author_name: str, 
                  author_email: str, description: str, env_file: Optional[str], 
                  force: bool):
    """
    Create a new Python project with modern tooling and best practices.
    
    This tool creates a complete project structure similar to DrWatson.jl
    with uv for dependency management, comprehensive documentation, 
    example code, and tests.
    """
    console.print(f"🚀 Creating project: [bold blue]{project_name}[/bold blue]")
    console.print(f"📂 Working directory: [dim]{Path.cwd()}[/dim]")
    
    project_path = Path(path) / project_name
    
    # Check if directory exists
    if project_path.exists() and not force:
        if not Confirm.ask(f"Directory {project_path} already exists. Continue?"):
            console.print("❌ Aborted.", style="bold red")
            return
    
    # Load dependencies from environment file if provided
    dependencies, dev_dependencies = [], []
    if env_file:
        console.print(f"📁 Loading dependencies from {env_file}")
        dependencies, dev_dependencies = load_environment_file(Path(env_file))
        
        # Always ensure h5py is included for data saving routines
        if not any("h5py" in dep for dep in dependencies):
            dependencies.append("h5py>=3.10.0")
            console.print("📦 Added h5py>=3.10.0 as default dependency for HDF5 data saving routines", style="cyan")
    else:
        # Default scientific computing dependencies
        dependencies = [
            "numpy>=1.24.0",
            "matplotlib>=3.7.0", 
            "scipy>=1.10.0",
            "jupyter>=1.0.0",
            "ipython>=8.0.0",
            "h5py>=3.10.0"
        ]
        dev_dependencies = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]
    
    # Create scaffolder and build project
    scaffolder = ProjectScaffolder(project_name, project_path)
    
    try:
        # Create directory structure
        scaffolder.create_project_structure()
        
        # Initialize uv project
        scaffolder.initialize_uv_project()
        
        # Add dependencies
        scaffolder.add_dependencies(dependencies, dev_dependencies)
        
        # Create source files
        scaffolder.create_source_files(author_name, author_email)
        
        # Create test files
        scaffolder.create_test_files()
        
        # Create example script
        scaffolder.create_example_script()
        
        # Create documentation
        scaffolder.create_readme(author_name, author_email, dependencies, description)
        
        # Update pyproject.toml
        scaffolder.update_pyproject_toml(author_name, author_email, description)
        
        # Create .gitignore
        scaffolder.create_gitignore()
        
        # Create example notebook
        scaffolder.create_example_notebook()
        
        console.print("✅ Project created successfully!", style="bold green")
        console.print(f"\n📂 Project location: [blue]{project_path.absolute()}[/blue]")
        
        console.print("\n🚀 Next steps:")
        console.print(f"   cd {project_name}")
        console.print("   uv sync                                    # Install dependencies")
        console.print("   uv run pytest                             # Run tests")
        console.print("   uv run python scripts/example_analysis.py # Run example")
        console.print("   uv run jupyter notebook                   # Open notebooks")
        
    except Exception as e:
        console.print(f"❌ Error creating project: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    create_project()

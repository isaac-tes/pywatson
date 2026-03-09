"""
PyWatson - A Python scientific project management tool inspired by DrWatson.jl

This tool creates a complete Python project structure with modern tooling (uv),
comprehensive documentation, example code, and tests.
"""

from . import utils
from .utils import (
    # Path management
    datadir,
    plotsdir,
    scriptsdir,
    notebooksdir,
    docsdir,
    testsdir,
    srcdir,
    projectdir,
    datafile,
    plotfile,
    scriptfile,
    notebookfile,
    savename,
    # Data management
    save_data,
    load_data,
    load_selective,
    save_array,
    load_array,
    data_info,
    list_data_files,
    tagsave,
    produce_or_load,
    collect_results,
    # DrWatson primitives
    parse_savename,
    dict_list,
    # Reproducibility
    safesave,
    tmpsave,
    snapshot_environment,
    set_random_seed,
    # Variant formats
    save_npz,
    load_npz,
    save_zarr,
    load_zarr,
)

__version__ = "0.1.0"

__all__ = [
    "utils",
    # Path management
    "datadir",
    "plotsdir",
    "scriptsdir",
    "notebooksdir",
    "docsdir",
    "testsdir",
    "srcdir",
    "projectdir",
    "datafile",
    "plotfile",
    "scriptfile",
    "notebookfile",
    "savename",
    # Data management
    "save_data",
    "load_data",
    "load_selective",
    "save_array",
    "load_array",
    "data_info",
    "list_data_files",
    "tagsave",
    "produce_or_load",
    "collect_results",
    # DrWatson primitives
    "parse_savename",
    "dict_list",
    # Reproducibility
    "safesave",
    "tmpsave",
    "snapshot_environment",
    "set_random_seed",
    # Variant formats
    "save_npz",
    "load_npz",
    "save_zarr",
    "load_zarr",
]

from .core import create_project, ProjectScaffolder

# Add core functions to __all__
__all__.extend(["create_project", "ProjectScaffolder"])


def hello() -> str:
    return "Hello from PyWatson!"

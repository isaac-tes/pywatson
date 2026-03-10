"""
PyWatson - A Python scientific project management tool

This tool creates a complete Python project structure with modern tooling (uv),
comprehensive documentation, example code, and tests.
"""

from . import utils
from .utils import (
    collect_results,
    data_info,
    # Path management
    datadir,
    datafile,
    dict_list,
    docsdir,
    list_data_files,
    load_array,
    load_data,
    load_npz,
    load_selective,
    load_zarr,
    notebookfile,
    notebooksdir,
    # PyWatson primitives
    parse_savename,
    plotfile,
    plotsdir,
    produce_or_load,
    projectdir,
    # Reproducibility
    safesave,
    save_array,
    # Data management
    save_data,
    # Variant formats
    save_npz,
    save_zarr,
    savename,
    scriptfile,
    scriptsdir,
    set_random_seed,
    snapshot_environment,
    srcdir,
    tagsave,
    testsdir,
    tmpsave,
)

__version__ = "0.0.1"

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
    # PyWatson primitives
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

from .core import ProjectScaffolder  # noqa: F401

# Add core classes to __all__
__all__.extend(["ProjectScaffolder"])


def hello() -> str:
    return "Hello from PyWatson!"

# AGENTS.md — Coding Agent Instructions for PyWatson

## Project Overview

PyWatson is a Python scientific project management tool inspired by
[DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/).
It scaffolds reproducible scientific computing projects with modern Python
tooling (uv, pytest, ruff) and provides DrWatson-style utilities for path
management, HDF5 data handling, parameter-based filenames, and smart caching.

- **Language**: Python 3.12+
- **Package manager**: [uv](https://docs.astral.sh/uv/) (not pip, not conda)
- **Build backend**: `uv_build`
- **Layout**: `src/` layout — the package lives at `src/pywatson/`
- **Entry point**: `drwatson-init` CLI → `pywatson.core:create_project`

## Build / Lint / Test Commands

All commands use `uv run` to execute inside the project's virtual environment.

```bash
# Setup
uv sync                        # Install all deps including dev group

# Run ALL tests
uv run pytest                  # Discover and run all tests

# Run a SINGLE test file
uv run pytest tests/test_scaffolder.py

# Run a SINGLE test class
uv run pytest tests/test_scaffolder.py::TestProjectScaffolder

# Run a SINGLE test method
uv run pytest tests/test_scaffolder.py::TestProjectScaffolder::test_scaffolder_initialization

# Run tests matching a keyword expression
uv run pytest -k "template"

# Verbose output with print capture disabled
uv run pytest -v -s

# Lint (ruff)
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/   # Auto-fix what's possible

# Format (ruff)
uv run ruff format src/ tests/
uv run ruff format --check src/ tests/ # Check only, don't modify

# Type check (mypy)
uv run mypy src/pywatson/

# Build distribution
uv build

# Run the CLI
uv run drwatson-init --help
uv run drwatson-init PROJECT_NAME --author-name "Name" --author-email "e@x.com" --description "desc"
```

## Project Layout

```
pywatson/
├── src/pywatson/              # Main package (src-layout)
│   ├── __init__.py            # Public API re-exports from core + drwatson
│   ├── core.py                # ProjectScaffolder class + Click CLI
│   ├── drwatson.py            # Path management, HDF5 data, git tracking
│   ├── py.typed               # PEP 561 typed-package marker
│   └── templates/             # Jinja2 templates for generated projects
│       ├── *.py.jinja2        # Python file templates
│       ├── *.jinja2           # Non-Python templates (gitignore, README, etc.)
│       └── ...
├── tests/                     # pytest test suite
│   ├── test_scaffolder.py     # Integration tests for ProjectScaffolder
│   └── test_templates.py      # Template rendering tests
├── create-project.sh          # Interactive bash wrapper for the CLI
├── pyproject.toml             # Project metadata, deps, tool config
└── AGENTS.md                  # This file
```

## Code Style

### Imports
- **Order**: stdlib → third-party → local (separated by blank lines)
- **Internal imports**: use relative (`from .module import ...`, `from . import module`)
- **Deferred imports**: acceptable inside functions for optional or heavy dependencies
- Example:
  ```python
  import os
  from pathlib import Path
  from typing import Optional

  import click
  import numpy as np

  from .drwatson import datadir, save_data
  ```

### Formatting
- **Line length**: 99 characters (configured in pyproject.toml `[tool.ruff]`)
- **Indentation**: 4 spaces, no tabs
- **Quotes**: double quotes for strings (ruff default)
- **Trailing commas**: use them in multi-line collections and function signatures

### Type Annotations
- **Required** on all public function signatures (parameters AND return type)
- Prefer built-in generics for Python 3.12+: `list[str]`, `dict[str, Any]`, `X | None`
- Legacy code may use `from typing import List, Optional, Dict` — acceptable but
  prefer modern syntax for new code
- `py.typed` marker is present — this package is typed for consumers
- Private helpers: annotations encouraged but not strictly required

### Naming Conventions
| Element              | Convention         | Examples                                   |
|----------------------|--------------------|--------------------------------------------|
| Classes              | `PascalCase`       | `ProjectScaffolder`                        |
| Functions / methods  | `snake_case`       | `create_project`, `load_data`              |
| Private helpers      | `_snake_case`      | `_render_template`, `_run_git_command`     |
| Variables            | `snake_case`       | `project_path`, `package_name`             |
| Module constants     | `UPPER_SNAKE_CASE` | `_PROJECT_ROOT` (private constant)         |
| Test classes         | `TestXxx`          | `TestProjectScaffolder`                    |
| Test functions       | `test_xxx`         | `test_scaffolder_initialization`           |
| Source files         | `snake_case.py`    | `core.py`, `drwatson.py`                   |
| Template files       | `name.ext.jinja2`  | `core.py.jinja2`, `README.md.jinja2`       |

### Docstrings — Google Style
```python
def save_data(data: dict[str, Any], filename: str,
              metadata: dict[str, Any] | None = None) -> Path:
    """
    Save data to HDF5 file in the data directory.

    Args:
        data: Dictionary of data to save (keys become HDF5 datasets).
        filename: Name of the file (without extension).
        metadata: Optional metadata dictionary.

    Returns:
        Path to the saved file.

    Raises:
        RuntimeError: If project root cannot be found.
    """
```
- Use `Args:`, `Returns:`, `Raises:`, `Example:` sections
- Single-line docstrings for trivial functions: `"""Get path to data directory."""`

### Error Handling
- Use **specific** exception types: `ValueError`, `RuntimeError`, `FileNotFoundError`, `TypeError`
- Broad `except Exception` only for **non-fatal** fallback paths (log warning, continue)
- `try/finally` to restore working directory after `os.chdir`
- Top-level CLI uses `try/except` + `sys.exit(1)`
- Tests: use `pytest.raises(ExceptionType)` for expected exceptions

## Testing Conventions

- **Framework**: pytest (run via `uv run pytest`)
- **Test grouping**: tests are organized into classes (`TestXxx`) within test files
- **Fixtures**: defined as methods within test classes using `@pytest.fixture`;
  use `yield` + cleanup pattern for temporary directories
- **Assertions**: plain `assert` statements (pytest-style), never `unittest` assertions
- **No conftest.py**: fixtures live inside the test classes that use them
- **Syntax validation**: generated Python templates are compiled with `compile()`
  to verify valid syntax

## Template Development

- Templates live in `src/pywatson/templates/` as `.jinja2` files
- Template variables use `{{ variable_name }}` syntax
- Common context variables: `project_name`, `package_name`, `author_name`,
  `author_email`, `project_name_title`, `description`
- After adding a new template, add a rendering test in `tests/test_templates.py`
- Python templates should be validated with `compile()` in tests

## Key Design Decisions

- `drwatson.py` is **copied verbatim** into generated projects (not templated)
- The `_PROJECT_ROOT` global caches the project root to avoid repeated filesystem walks
- HDF5 is the default data format (via h5py); metadata stored as JSON in HDF5 attributes
- Git commit info is automatically embedded in saved data files
- `produce_or_load()` implements DrWatson.jl-style smart caching
- `savename()` creates deterministic filenames from parameter dictionaries

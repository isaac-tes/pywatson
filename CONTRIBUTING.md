# Contributing to PyWatson

Thank you for your interest in contributing to PyWatson! This document provides
guidelines and instructions for contributing.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/pywatson.git
cd pywatson

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev group)
uv sync

# Verify everything works
uv run pytest
```

## Development Workflow

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes**, following the code style in [AGENTS.md](AGENTS.md).

3. **Format and lint** your code:
   ```bash
   uv run ruff format src/ tests/
   uv run ruff check --fix src/ tests/
   ```

4. **Run the tests**:
   ```bash
   uv run pytest -v
   ```

5. **Commit** using [Angular commit conventions](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit):
   ```
   feat: Add new project structure template
   fix: Correct HDF5 filename extension handling
   docs: Update README with new examples
   test: Add tests for minimal project type
   refactor: Simplify template rendering logic
   ```

6. **Open a pull request** with a clear description of the changes.

## Code Style

See [AGENTS.md](AGENTS.md) for comprehensive code style guidelines including:
- Import ordering (stdlib, third-party, local)
- Type annotation requirements
- Naming conventions
- Google-style docstrings
- Error handling patterns

## Testing

- All new features should have accompanying tests.
- Tests live in `tests/` and use pytest.
- Run a single test: `uv run pytest tests/test_file.py::TestClass::test_method`
- Generated Python templates must pass `compile()` syntax validation.

## Adding New Templates

1. Create the template in `src/pywatson/templates/` with `.jinja2` extension.
2. Add rendering logic in `src/pywatson/core.py` (in `ProjectScaffolder`).
3. Add a test in `tests/test_templates.py` to verify the template renders.
4. If it's a Python template, add a `compile()` syntax check in the test.

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests.
- Include the Python version, uv version, and OS in bug reports.
- For generated project issues, include the command used to create the project.

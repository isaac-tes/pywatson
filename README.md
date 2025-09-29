# PyScaffold DrWatson

A Python project scaffolding tool inspired by [DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/) for creating well-structured scientific computing projects with modern Python tooling.

## Features

- 🏗️ **Complete Project Structure**: Creates standard Python project layout with data, plots, scripts, notebooks, docs, and tests directories
- 📦 **Modern Tooling**: Uses [`uv`](https://docs.astral.sh/uv/) for fast dependency management and virtual environments ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
- 🐍 **Python Best Practices**: Includes pyproject.toml, proper package structure, and type hints
- 📊 **HDF5 Data Management**: Built-in support for saving/loading scientific data with h5py and git tracking
- 🧪 **DrWatson.jl-Inspired Workflow**: Parameter-based filenames, caching, and experiment management
- 📝 **Path Management**: Project-aware directory functions that work from anywhere in your project
- ⚡ **Smart Caching**: Automatic result caching with `produce_or_load()` for expensive computations
- 🔄 **Git Integration**: Automatic git commit tracking in saved data files
- 🎯 **Parameter-Based Naming**: Generate consistent filenames from parameter dictionaries
- 📈 **Batch Result Collection**: Easily collect and analyze results from multiple experiments

## Quick Start

### 1. Install Dependencies

```bash
# Install uv (modern Python package manager)
# See: https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone this repository
git clone https://github.com/your-username/pyscaffold-drwatson.git
cd pyscaffold-drwatson

# Install in development mode
uv sync
```

> 💡 **New to uv?** Check out the [uv documentation](https://docs.astral.sh/uv/) and [why uv is faster](https://docs.astral.sh/uv/concepts/resolution/) than traditional pip workflows.

### 2. Create Your First Project

```bash
# Option 1: Interactive mode (recommended)
./create-project.sh -i

# Option 2: Quick mode with defaults
./create-project.sh my-analysis-project

# Option 3: Command line with all options
uv run drwatson-init my-project \
  --author-name "Your Name" \
  --author-email "your.email@domain.com" \
  --description "My research project" \
  --env-file environment.example.yml
```

### 3. Start Working

```bash
cd my-project
uv sync                                    # Install dependencies
uv run pytest                             # Run tests (should all pass)
uv run python scripts/generate_data.py    # Generate example data
uv run python scripts/analyze_data.py     # Run example analysis
```

## Usage Examples

### Command Line Options

```bash
# Basic usage
uv run drwatson-init PROJECT_NAME

# Full options
uv run drwatson-init my-project \
  --path ./projects \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Analysis of quantum systems" \
  --env-file my-environment.yml \
  --force  # Overwrite if exists
```

### Environment File Support

Create an `environment.yml` file:
```yaml
name: my-project
dependencies:
  - python=3.12
  - numpy>=1.24.0
  - pandas>=2.0.0
  - scikit-learn>=1.3.0
  - pip:
    - seaborn>=0.12.0
    - plotly>=5.0.0
```

Then use it:
```bash
uv run drwatson-init my-project --env-file environment.yml
```

### Generated Project Structure

```
my-project/
├── src/my_project/         # Your library source code
│   ├── __init__.py         # Package initialization with DrWatson functions
│   ├── core.py             # Analysis functions and utilities
│   └── drwatson.py         # Path management and data handling
├── scripts/                # Standalone analysis scripts
│   ├── generate_data.py    # Example data generation
│   └── analyze_data.py     # Example analysis workflow
├── notebooks/              # Jupyter notebooks
│   └── example.ipynb       # Interactive analysis example
├── tests/                  # Unit tests
│   └── test_core.py        # Comprehensive test suite
├── data/                   # Data files (created when needed)
├── plots/                  # Generated figures and plots
├── docs/                   # Documentation
├── pyproject.toml          # Project configuration
├── README.md               # Project documentation
└── .gitignore              # Git ignore patterns
```

### DrWatson-Style Workflow

In your generated project:

```python
from my_project import (
    # Path management
    datadir, plotsdir, savename,
    # Data management
    save_data, load_data, tagsave, produce_or_load,
    # Analysis functions
    create_example_data, analyze_data
)

# 1. Parameter-based filenames
params = {'lr': 0.01, 'epochs': 100, 'batch_size': 32}
filename = savename(params, suffix='.h5')
# → "batch_size=32_epochs=100_lr=0.01.h5"

# 2. Smart data handling
data = create_example_data((1000, 5), "random")
results = analyze_data(data, "pca")

# 3. Save with git tracking
filepath = tagsave(filename, {'data': data, 'results': results}, params)

# 4. Cache expensive computations
def expensive_computation(param1, param2):
    # Your expensive ML/simulation code here
    return {'result': 'computed_value'}

result, existed = produce_or_load('cache.h5', expensive_computation, 'arg1', 'arg2')
print(f"Used cache: {existed}")

# 5. Path management from anywhere
data_path = datadir("experiments", "session_1")  # Creates data/experiments/session_1/
plot_path = plotsdir("results")                   # Creates plots/results/
```

## Development Workflow

### For Contributors

```bash
# Clone the repo
git clone https://github.com/your-username/pyscaffold-drwatson.git
cd pyscaffold-drwatson

# Setup development environment
uv sync

# Test CLI functionality
uv run drwatson-init test-project \
  --author-name "Test User" \
  --author-email "test@example.com" \
  --description "Test project"

# Test interactive script
./create-project.sh -i
```

### Testing Your Changes

```bash
# Create a test project to verify everything works
cd /tmp
/path/to/pyscaffold-drwatson/create-project.sh test-my-changes

# Test the generated project
cd test-my-changes
uv sync
uv run pytest
uv run python scripts/generate_data.py
uv run python scripts/analyze_data.py
```

### Working with Generated Projects

Generated projects are fully integrated with uv for modern Python development:

```bash
# Setup a new project
cd my-project
uv sync                    # Install all dependencies
uv run pytest             # Run tests
uv run python script.py   # Run Python scripts

# Add new dependencies
uv add pandas plotly       # Runtime dependencies
uv add --group dev black   # Development dependencies

# Environment management
uv run jupyter notebook    # Run Jupyter without global install
uv run python -m pip list  # List installed packages

# Build and publish (when ready)
uv build                   # Build wheel and source dist
```

#### Key uv Features Used

- **[Fast dependency resolution](https://docs.astral.sh/uv/concepts/resolution/)**: Projects install dependencies in seconds
- **[Virtual environment management](https://docs.astral.sh/uv/concepts/projects/)**: Automatic `.venv` creation and management
- **[Lock file support](https://docs.astral.sh/uv/concepts/resolution/#lockfile)**: `uv.lock` ensures reproducible installs
- **[Dependency groups](https://docs.astral.sh/uv/concepts/dependencies/#dependency-groups)**: Separate dev, test, and docs dependencies
- **[Python version management](https://docs.astral.sh/uv/concepts/python-versions/)**: Pin Python versions in `pyproject.toml`

> 📚 **Learn more**: [uv User Guide](https://docs.astral.sh/uv/guides/) | [uv vs pip/conda](https://docs.astral.sh/uv/pip/compatibility/) | [Migration Guide](https://docs.astral.sh/uv/guides/integration/)

## Architecture

### Core Components

- **`core.py`**: Main scaffolding logic and CLI interface
- **`drwatson.py`**: DrWatson.jl-inspired utilities (path management, data handling)
- **`create-project.sh`**: Convenient bash wrapper script
- **Templates**: Embedded in `core.py` for generating project files

### Design Philosophy

- **Reproducible**: Clear structure and dependency management
- **Shareable**: Easy collaboration via Git
- **Scalable**: Grows with your project
- **Modern**: Latest Python tooling (uv, pytest, type hints)

## Comparison with DrWatson.jl

| Feature | DrWatson.jl | PyScaffold DrWatson |
|---------|-------------|-------------------|
| Package Manager | Pkg.jl | uv |
| Project Structure | ✅ | ✅ |
| Parameter-based naming | ✅ | ✅ |
| Smart caching | ✅ | ✅ |
| Git integration | ✅ | ✅ |
| Path management | ✅ | ✅ |
| HDF5 support | ✅ | ✅ |
| Example workflows | ✅ | ✅ |

## Troubleshooting

### Common Issues

**Command not found: drwatson-init**
```bash
# Make sure you're in the project directory and have synced
cd pyscaffold-drwatson
uv sync
uv run drwatson-init --help
```

**Environment file not found**
```bash
# Use absolute path or make sure file exists
uv run drwatson-init my-project --env-file /absolute/path/to/environment.yml
```

**"Got unexpected extra arguments"**
```bash
# Quote strings with spaces
uv run drwatson-init my-project --description "My analysis project"
```

## Examples

### Create a Data Science Project

```bash
uv run drwatson-init data-analysis \
  --author-name "Jane Doe" \
  --author-email "jane@example.com" \
  --description "Analysis of customer behavior data"
```

### Create a Machine Learning Project

```bash
# First create environment.yml with ML dependencies
cat > ml-environment.yml << EOF
name: ml-project
dependencies:
  - python=3.12
  - numpy>=1.24.0
  - pandas>=2.0.0
  - scikit-learn>=1.3.0
  - matplotlib>=3.7.0
  - seaborn>=0.12.0
  - jupyter>=1.0.0
  - pip:
    - plotly>=5.0.0
    - optuna>=3.0.0
EOF

# Create project with ML dependencies
uv run drwatson-init ml-project --env-file ml-environment.yml
```

### Adding Development Tools to Generated Projects

```bash
cd my-project
# Install development tools
uv add --group dev black ruff mypy
```
## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Inspired by [DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/) from the Julia ecosystem
- Built with [uv](https://docs.astral.sh/uv/) for modern Python package management
- CLI powered by [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)

"""
PyWatson - A Python scientific project managment tool inspired by DrWatson.jl

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
from jinja2 import Environment, PackageLoader, select_autoescape
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
        
        # Initialize Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=PackageLoader('pywatson', 'templates'),
            autoescape=select_autoescape(['html', 'xml']),
            keep_trailing_newline=True
        )
    
    def _render_template(self, template_name: str, **context) -> str:
        """
        Render a Jinja2 template with the given context.
        
        Args:
            template_name: Name of the template file in the templates directory
            **context: Variables to pass to the template
            
        Returns:
            Rendered template as a string
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)
        
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
        """Create source code files using Jinja2 templates."""
        console.print("📝 Creating source files from templates...", style="bold blue")
        
        # Prepare template context
        context = {
            'project_name': self.project_name,
            'project_name_title': self.project_name.title().replace("-", " ").replace("_", " "),
            'package_name': self.package_name,
            'author_name': author_name,
            'author_email': author_email,
        }
        
        # Create __init__.py
        init_content = self._render_template('__init__.py.jinja2', **context)
        (self.project_path / "src" / self.package_name / "__init__.py").write_text(init_content)
        
        # Create core.py
        core_content = self._render_template('core.py.jinja2', **context)
        (self.project_path / "src" / self.package_name / "core.py").write_text(core_content)
        
        # Copy drwatson.py directly (no template needed)
        self._copy_drwatson_file()
    
    def _copy_drwatson_file(self) -> None:
        """Copy the drwatson.py file directly to the project."""
        import shutil
        
        source_drwatson = Path(__file__).parent / "drwatson.py"
        target_drwatson = self.project_path / "src" / self.package_name / "drwatson.py"
        
        if source_drwatson.exists():
            shutil.copy2(source_drwatson, target_drwatson)
        else:
            console.print(f"⚠️  Warning: drwatson.py not found at {source_drwatson}", style="yellow")

    def create_test_files(self) -> None:
        """Create test files using Jinja2 templates."""
        console.print("🧪 Creating test files...", style="bold blue")
        
        # Create __init__.py for tests
        (self.project_path / "tests" / "__init__.py").write_text("# Tests package\n")
        
        # Create test_core.py from template
        context = {'package_name': self.package_name}
        test_content = self._render_template('test_core.py.jinja2', **context)
        (self.project_path / "tests" / "test_core.py").write_text(test_content)

    def create_example_script(self) -> None:
        """Create example scripts using Jinja2 templates."""
        console.print("📜 Creating example scripts...", style="bold blue")
        
        context = {'package_name': self.package_name}
        
        # Create data generation script
        generate_script = self._render_template('generate_data.py.jinja2', **context)
        (self.project_path / "scripts" / "generate_data.py").write_text(generate_script)
        
        # Create analysis script
        analyze_script = self._render_template('analyze_data.py.jinja2', **context)
        (self.project_path / "scripts" / "analyze_data.py").write_text(analyze_script)

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
        """Create a .gitignore file using Jinja2 template."""
        console.print("📄 Creating .gitignore...", style="bold blue")
        
        gitignore_content = self._render_template('gitignore.jinja2')
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

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
            "_research",
            "_research/tmp",
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
        """Create a comprehensive README.md file using Jinja2 template."""
        console.print("📄 Creating README.md from template...", style="bold blue")
        
        # Format dependencies list
        deps_list = "\n".join([f"- **{dep.split('==')[0] if '==' in dep else dep.split('>=')[0] if '>=' in dep else dep}**: {dep}" for dep in dependencies])
        
        # Prepare template context
        context = {
            'project_name': self.project_name,
            'project_name_title': self.project_name.title().replace("-", " ").replace("_", " "),
            'package_name': self.package_name,
            'author_name': author_name,
            'author_email': author_email,
            'description': description,
            'deps_list': deps_list,
        }
        
        # Render template
        readme_content = self._render_template('README.md.jinja2', **context)
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
        """Create a simplified example Jupyter notebook using Jinja2 template."""
        console.print("📓 Creating example notebook from template...", style="bold blue")
        
        # Prepare template context
        context = {
            'project_name_title': self.project_name.title().replace("-", " ").replace("_", " "),
            'package_name': self.package_name,
        }
        
        # Render template
        notebook_content = self._render_template('notebook.ipynb.jinja2', **context)
        notebook_path = self.project_path / "notebooks" / f"{self.package_name}_example.ipynb"
        notebook_path.write_text(notebook_content)


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

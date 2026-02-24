"""
PyWatson - A Python scientific project management tool inspired by DrWatson.jl

This tool creates a complete Python project structure with modern tooling (uv),
comprehensive documentation, example code, and tests.

Project types:
  - default: DrWatson.jl standard layout with data/{sims, exp_raw, exp_pro}
  - minimal: Lightweight layout with just src, data, scripts, tests
  - full:    Everything + config/, Makefile, CI, CONTRIBUTING, CHANGELOG
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console
from rich.progress import track
from rich.prompt import Confirm

__version__ = "0.1.0"

console = Console()

# Valid project types and their descriptions
PROJECT_TYPES = {
    "default": "DrWatson.jl standard (data/{sims, exp_raw, exp_pro})",
    "minimal": "Lightweight (src, data, scripts, tests)",
    "full": "Full (everything + config/, Makefile, CI, CONTRIBUTING, CHANGELOG)",
}

# Valid license choices and their template filenames
LICENSE_TEMPLATES = {
    "MIT": "LICENSE_MIT.jinja2",
    "BSD-3-Clause": "LICENSE_BSD3.jinja2",
    "Apache-2.0": "LICENSE_APACHE2.jinja2",
    "ISC": "LICENSE_ISC.jinja2",
}


class ProjectScaffolder:
    """Main class for scaffolding Python projects.

    Supports three project types:
      - ``default``: DrWatson.jl standard layout with data/{sims, exp_raw, exp_pro}
      - ``minimal``: Lightweight layout with just src, data, scripts, tests
      - ``full``:    Everything from *default* plus config/, Makefile, CI,
                     CONTRIBUTING, CHANGELOG
    """

    def __init__(
        self,
        project_name: str,
        project_path: Path,
        project_type: str = "default",
        license_type: str = "MIT",
    ) -> None:
        self.project_name = project_name
        self.project_path = project_path
        self.package_name = project_name.lower().replace("-", "_").replace(" ", "_")
        self.project_type = project_type
        self.license_type = license_type

        # Validate project_type
        if self.project_type not in PROJECT_TYPES:
            raise ValueError(
                f"Unknown project type '{self.project_type}'. "
                f"Valid options: {', '.join(PROJECT_TYPES)}"
            )

        # Validate license_type
        if self.license_type not in LICENSE_TEMPLATES:
            raise ValueError(
                f"Unknown license type '{self.license_type}'. "
                f"Valid options: {', '.join(LICENSE_TEMPLATES)}"
            )

        # Initialize Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=PackageLoader("pywatson", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            keep_trailing_newline=True,
        )

    def _render_template(self, template_name: str, **context: object) -> str:
        """Render a Jinja2 template with the given context.

        Args:
            template_name: Name of the template file in the templates directory.
            **context: Variables to pass to the template.

        Returns:
            Rendered template as a string.
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    # ------------------------------------------------------------------
    # Directory structure
    # ------------------------------------------------------------------

    def create_project_structure(self) -> None:
        """Create the project directory tree based on the chosen project type.

        ``default``
            src/<pkg>, scripts, notebooks, tests, plots,
            data/{sims, exp_raw, exp_pro}, docs, _research/tmp

        ``minimal``
            src/<pkg>, scripts, tests, data, docs

        ``full``
            Everything from *default* plus config/, .github/workflows/
        """
        # Directories common to ALL project types
        base_dirs = [
            "src",
            f"src/{self.package_name}",
            "scripts",
            "tests",
            "data",
            "docs",
        ]

        if self.project_type == "minimal":
            directories = base_dirs

        elif self.project_type == "default":
            directories = base_dirs + [
                "notebooks",
                "plots",
                # DrWatson.jl-style data subdirectories
                "data/sims",
                "data/exp_raw",
                "data/exp_pro",
                "_research",
                "_research/tmp",
            ]

        else:  # full
            directories = base_dirs + [
                "notebooks",
                "plots",
                "data/sims",
                "data/exp_raw",
                "data/exp_pro",
                "_research",
                "_research/tmp",
                "config",
                ".github",
                ".github/workflows",
            ]

        for directory in track(directories, description="Creating directories..."):
            (self.project_path / directory).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # uv project init & dependencies
    # ------------------------------------------------------------------

    def initialize_uv_project(self) -> None:
        """Initialize the uv project."""
        console.print("Initializing uv project...", style="bold blue")

        original_cwd = Path.cwd()
        try:
            os.chdir(self.project_path)
            result = subprocess.run(
                ["uv", "init", "--lib", "--name", self.project_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                console.print(
                    f"Error initializing uv project: {result.stderr}",
                    style="bold red",
                )
                raise RuntimeError("Failed to initialize uv project")
        finally:
            os.chdir(original_cwd)

    def add_dependencies(
        self,
        dependencies: list[str],
        dev_dependencies: list[str] | None = None,
    ) -> None:
        """Add dependencies using uv.

        Args:
            dependencies: Runtime dependencies to install.
            dev_dependencies: Development dependencies to install.
        """
        original_cwd = Path.cwd()
        try:
            os.chdir(self.project_path)

            if dependencies:
                console.print("Adding dependencies...", style="bold blue")
                failed_deps: list[str] = []
                for dep in track(dependencies, description="Installing packages..."):
                    try:
                        result = subprocess.run(
                            ["uv", "add", dep],
                            capture_output=True,
                            check=False,
                        )
                        if result.returncode != 0:
                            console.print(
                                f"Warning: Failed to install {dep}: {result.stderr.decode()}",
                                style="yellow",
                            )
                            failed_deps.append(dep)
                    except Exception as e:
                        console.print(
                            f"Warning: Error installing {dep}: {e}",
                            style="yellow",
                        )
                        failed_deps.append(dep)

                if failed_deps:
                    console.print(
                        f"Some dependencies failed to install: {failed_deps}",
                        style="yellow",
                    )
                    console.print(
                        "You can manually install them later with: uv add <package>",
                        style="yellow",
                    )

            if dev_dependencies:
                console.print("Adding development dependencies...", style="bold blue")
                for dep in track(dev_dependencies, description="Installing dev packages..."):
                    subprocess.run(
                        ["uv", "add", "--group", "dev", dep],
                        capture_output=True,
                        check=True,
                    )
        finally:
            os.chdir(original_cwd)

    # ------------------------------------------------------------------
    # Source files
    # ------------------------------------------------------------------

    def create_source_files(self, author_name: str, author_email: str) -> None:
        """Create source code files using Jinja2 templates.

        Args:
            author_name: Author's full name.
            author_email: Author's email address.
        """
        console.print("Creating source files from templates...", style="bold blue")

        context = {
            "project_name": self.project_name,
            "project_name_title": self.project_name.title().replace("-", " ").replace("_", " "),
            "package_name": self.package_name,
            "author_name": author_name,
            "author_email": author_email,
        }

        # __init__.py
        init_content = self._render_template("__init__.py.jinja2", **context)
        (self.project_path / "src" / self.package_name / "__init__.py").write_text(init_content)

        # core.py
        core_content = self._render_template("core.py.jinja2", **context)
        (self.project_path / "src" / self.package_name / "core.py").write_text(core_content)

        # drwatson.py — copied verbatim (not templated)
        self._copy_drwatson_file()

    def _copy_drwatson_file(self) -> None:
        """Copy the drwatson.py file directly to the project."""
        import shutil

        source_drwatson = Path(__file__).parent / "drwatson.py"
        target_drwatson = self.project_path / "src" / self.package_name / "drwatson.py"

        if source_drwatson.exists():
            shutil.copy2(source_drwatson, target_drwatson)
        else:
            console.print(
                f"Warning: drwatson.py not found at {source_drwatson}",
                style="yellow",
            )

    # ------------------------------------------------------------------
    # Test files
    # ------------------------------------------------------------------

    def create_test_files(self) -> None:
        """Create test files using Jinja2 templates."""
        console.print("Creating test files...", style="bold blue")

        (self.project_path / "tests" / "__init__.py").write_text("# Tests package\n")

        context = {"package_name": self.package_name}
        test_content = self._render_template("test_core.py.jinja2", **context)
        (self.project_path / "tests" / "test_core.py").write_text(test_content)

    # ------------------------------------------------------------------
    # Example scripts
    # ------------------------------------------------------------------

    def create_example_script(self) -> None:
        """Create example scripts using Jinja2 templates."""
        console.print("Creating example scripts...", style="bold blue")

        context = {"package_name": self.package_name}

        generate_script = self._render_template("generate_data.py.jinja2", **context)
        (self.project_path / "scripts" / "generate_data.py").write_text(generate_script)

        analyze_script = self._render_template("analyze_data.py.jinja2", **context)
        (self.project_path / "scripts" / "analyze_data.py").write_text(analyze_script)

    # ------------------------------------------------------------------
    # README
    # ------------------------------------------------------------------

    def create_readme(
        self,
        author_name: str,
        author_email: str,
        dependencies: list[str],
        description: str,
    ) -> None:
        """Create a comprehensive README.md file using Jinja2 template.

        Args:
            author_name: Author's full name.
            author_email: Author's email address.
            dependencies: List of runtime dependencies.
            description: Short project description.
        """
        console.print("Creating README.md from template...", style="bold blue")

        # Format dependencies list for display
        deps_list = "\n".join(
            [
                f"- **{dep.split('==')[0] if '==' in dep else dep.split('>=')[0] if '>=' in dep else dep}**: {dep}"
                for dep in dependencies
            ]
        )

        context = {
            "project_name": self.project_name,
            "project_name_title": self.project_name.title().replace("-", " ").replace("_", " "),
            "package_name": self.package_name,
            "author_name": author_name,
            "author_email": author_email,
            "description": description,
            "deps_list": deps_list,
            "project_type": self.project_type,
            "license_type": self.license_type,
        }

        readme_content = self._render_template("README.md.jinja2", **context)
        (self.project_path / "README.md").write_text(readme_content)

    # ------------------------------------------------------------------
    # pyproject.toml updates
    # ------------------------------------------------------------------

    def update_pyproject_toml(
        self,
        author_name: str,
        author_email: str,
        description: str,
    ) -> None:
        """Update pyproject.toml with project metadata.

        Args:
            author_name: Author's full name.
            author_email: Author's email address.
            description: Short project description.
        """
        pyproject_path = self.project_path / "pyproject.toml"

        if pyproject_path.exists():
            content = pyproject_path.read_text()
            content = content.replace(
                'description = "Add your description here"',
                f'description = "{description}"',
            )
            pyproject_path.write_text(content)

    # ------------------------------------------------------------------
    # .gitignore
    # ------------------------------------------------------------------

    def create_gitignore(self) -> None:
        """Create a .gitignore file using Jinja2 template."""
        console.print("Creating .gitignore...", style="bold blue")

        gitignore_content = self._render_template("gitignore.jinja2")
        (self.project_path / ".gitignore").write_text(gitignore_content)

    # ------------------------------------------------------------------
    # License
    # ------------------------------------------------------------------

    def create_license(self, author_name: str) -> None:
        """Create a LICENSE file from the chosen license template.

        Args:
            author_name: Author's full name (used in copyright line).
        """
        console.print(f"Creating LICENSE ({self.license_type})...", style="bold blue")

        template_name = LICENSE_TEMPLATES[self.license_type]
        context = {
            "author_name": author_name,
            "year": str(datetime.now().year),
        }

        license_content = self._render_template(template_name, **context)
        (self.project_path / "LICENSE").write_text(license_content)

    # ------------------------------------------------------------------
    # Full-type extras: config/, Makefile, CI, CONTRIBUTING, CHANGELOG
    # ------------------------------------------------------------------

    def create_full_extras(self, author_name: str, author_email: str) -> None:
        """Create additional files for the 'full' project type.

        Generates:
          - config/ruff.toml
          - config/pytest.ini
          - Makefile
          - .github/workflows/ci.yml
          - CONTRIBUTING.md
          - CHANGELOG.md

        Args:
            author_name: Author's full name.
            author_email: Author's email address.
        """
        console.print("Creating full project extras...", style="bold blue")

        context = {
            "project_name": self.project_name,
            "project_name_title": self.project_name.title().replace("-", " ").replace("_", " "),
            "package_name": self.package_name,
            "author_name": author_name,
            "author_email": author_email,
        }

        # config/ruff.toml
        ruff_content = self._render_template("ruff.toml.jinja2", **context)
        (self.project_path / "config" / "ruff.toml").write_text(ruff_content)

        # config/pytest.ini
        pytest_content = self._render_template("pytest.ini.jinja2", **context)
        (self.project_path / "config" / "pytest.ini").write_text(pytest_content)

        # Makefile
        makefile_content = self._render_template("Makefile.jinja2", **context)
        (self.project_path / "Makefile").write_text(makefile_content)

        # .github/workflows/ci.yml
        ci_content = self._render_template("ci.yml.jinja2", **context)
        (self.project_path / ".github" / "workflows" / "ci.yml").write_text(ci_content)

        # CONTRIBUTING.md
        contributing_content = self._render_template("CONTRIBUTING.md.jinja2", **context)
        (self.project_path / "CONTRIBUTING.md").write_text(contributing_content)

        # CHANGELOG.md
        changelog_content = self._render_template("CHANGELOG.md.jinja2", **context)
        (self.project_path / "CHANGELOG.md").write_text(changelog_content)

    # ------------------------------------------------------------------
    # Notebook
    # ------------------------------------------------------------------

    def create_example_notebook(self) -> None:
        """Create a simplified example Jupyter notebook using Jinja2 template.

        Only created for 'default' and 'full' project types (they include
        the notebooks/ directory).
        """
        if self.project_type == "minimal":
            return  # minimal projects don't include notebooks/

        console.print("Creating example notebook from template...", style="bold blue")

        context = {
            "project_name_title": self.project_name.title().replace("-", " ").replace("_", " "),
            "package_name": self.package_name,
        }

        notebook_content = self._render_template("notebook.ipynb.jinja2", **context)
        notebook_path = self.project_path / "notebooks" / f"{self.package_name}_example.ipynb"
        notebook_path.write_text(notebook_content)


# ==========================================================================
# Helper functions
# ==========================================================================


def load_environment_file(env_file: Path) -> tuple[list[str], list[str]]:
    """Load dependencies from an environment.yml file.

    Args:
        env_file: Path to environment.yml.

    Returns:
        Tuple of (runtime_dependencies, dev_dependencies).
    """
    if not env_file.exists():
        return [], []

    with open(env_file) as f:
        env_data = yaml.safe_load(f)

    dependencies: list[str] = []
    dev_dependencies: list[str] = []

    # Process conda dependencies
    if "dependencies" in env_data:
        for dep in env_data["dependencies"]:
            if isinstance(dep, str) and not dep.startswith("python"):
                # Convert conda format (=) to pip format (>=) for better compatibility
                if "=" in dep and not dep.startswith("=") and "==" not in dep and ">=" not in dep:
                    dep = dep.replace("=", ">=", 1)
                dependencies.append(dep)
            elif isinstance(dep, dict) and "pip" in dep:
                for pip_dep in dep["pip"]:
                    dependencies.append(pip_dep)

    # Add common dev dependencies
    dev_dependencies = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]

    return dependencies, dev_dependencies


# ==========================================================================
# CLI
# ==========================================================================


@click.command()
@click.argument("project_name")
@click.option(
    "--path",
    "-p",
    type=click.Path(),
    default=".",
    help="Directory to create the project in.",
)
@click.option("--author-name", prompt="Author name", help="Author name.")
@click.option("--author-email", prompt="Author email", help="Author email.")
@click.option(
    "--description",
    prompt="Project description",
    help="Short project description.",
)
@click.option(
    "--project-type",
    "-t",
    type=click.Choice(list(PROJECT_TYPES.keys()), case_sensitive=False),
    default="default",
    show_default=True,
    help="Project structure type.",
)
@click.option(
    "--license",
    "license_type",
    type=click.Choice(list(LICENSE_TEMPLATES.keys()), case_sensitive=False),
    default="MIT",
    show_default=True,
    help="License for the generated project.",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    help="Environment file (environment.yml) to import dependencies from.",
)
@click.option("--force", is_flag=True, help="Overwrite existing directory.")
def create_project(
    project_name: str,
    path: str,
    author_name: str,
    author_email: str,
    description: str,
    project_type: str,
    license_type: str,
    env_file: Optional[str],
    force: bool,
) -> None:
    """Create a new Python project with modern tooling and best practices.

    This tool creates a complete project structure similar to DrWatson.jl
    with uv for dependency management, comprehensive documentation,
    example code, and tests.

    PROJECT_NAME is the name for your new project (e.g. 'my-simulation').
    """
    console.print(f"Creating project: [bold blue]{project_name}[/bold blue]")
    console.print(f"  Type: [cyan]{project_type}[/cyan] ({PROJECT_TYPES[project_type]})")
    console.print(f"  License: [cyan]{license_type}[/cyan]")
    console.print(f"  Working directory: [dim]{Path.cwd()}[/dim]")

    project_path = Path(path) / project_name

    # Check if directory exists
    if project_path.exists() and not force:
        if not Confirm.ask(f"Directory {project_path} already exists. Continue?"):
            console.print("Aborted.", style="bold red")
            return

    # Load dependencies from environment file if provided
    dependencies: list[str] = []
    dev_dependencies: list[str] = []
    if env_file:
        console.print(f"Loading dependencies from {env_file}")
        dependencies, dev_dependencies = load_environment_file(Path(env_file))

        # Always ensure h5py is included for data saving routines
        if not any("h5py" in dep for dep in dependencies):
            dependencies.append("h5py>=3.10.0")
            console.print(
                "Added h5py>=3.10.0 as default dependency for HDF5 data saving routines",
                style="cyan",
            )
    else:
        # Default scientific computing dependencies
        dependencies = [
            "numpy>=1.24.0",
            "matplotlib>=3.7.0",
            "scipy>=1.10.0",
            "jupyter>=1.0.0",
            "ipython>=8.0.0",
            "h5py>=3.10.0",
        ]
        dev_dependencies = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]

    # Create scaffolder and build project
    scaffolder = ProjectScaffolder(
        project_name,
        project_path,
        project_type=project_type,
        license_type=license_type,
    )

    try:
        # 1. Directory structure
        scaffolder.create_project_structure()

        # 2. uv init
        scaffolder.initialize_uv_project()

        # 3. Dependencies
        scaffolder.add_dependencies(dependencies, dev_dependencies)

        # 4. Source files
        scaffolder.create_source_files(author_name, author_email)

        # 5. Tests
        scaffolder.create_test_files()

        # 6. Example scripts
        scaffolder.create_example_script()

        # 7. README (uses project_type and license_type internally)
        scaffolder.create_readme(author_name, author_email, dependencies, description)

        # 8. pyproject.toml metadata
        scaffolder.update_pyproject_toml(author_name, author_email, description)

        # 9. .gitignore
        scaffolder.create_gitignore()

        # 10. LICENSE file
        scaffolder.create_license(author_name)

        # 11. Example notebook (skipped for minimal)
        scaffolder.create_example_notebook()

        # 12. Full-type extras (Makefile, CI, CONTRIBUTING, CHANGELOG, config/)
        if project_type == "full":
            scaffolder.create_full_extras(author_name, author_email)

        console.print("\nProject created successfully!", style="bold green")
        console.print(f"\nProject location: [blue]{project_path.absolute()}[/blue]")

        console.print("\nNext steps:")
        console.print(f"   cd {project_name}")
        console.print("   uv sync                                    # Install dependencies")
        console.print("   uv run pytest                              # Run tests")
        console.print("   uv run python scripts/generate_data.py     # Generate example data")
        if project_type == "full":
            console.print("   make check                                 # Run all quality checks")

    except Exception as e:
        console.print(f"Error creating project: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    create_project()

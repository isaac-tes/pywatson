"""
PyWatson - A Python scientific project management tool.

This tool creates a complete Python project structure with modern tooling (uv),
comprehensive documentation, example code, and tests.

Project types:
  - default: PyWatson standard layout with data/{sims, exp_raw, exp_pro}
  - minimal: Lightweight layout with just src, data, scripts, tests
  - full:    Everything + config/, Makefile, CI, CONTRIBUTING, CHANGELOG
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
import yaml  # type: ignore[import-untyped]
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console
from rich.progress import track
from rich.prompt import Confirm

__version__ = "0.1.0"

console = Console()


def _git_config(key: str) -> str:
    """Read a git global/local config value, return empty string if unavailable."""
    try:
        result = subprocess.run(
            ["git", "config", key],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


# Valid project types and their descriptions
PROJECT_TYPES = {
    "default": "PyWatson standard (data/{sims, exp_raw, exp_pro})",
    "minimal": "Lightweight (src, data, scripts, tests)",
    "full": "Full (everything + config/, Makefile, CI, CONTRIBUTING, CHANGELOG)",
}

# --------------------------------------------------------------------------
# File classification constants (used by ProjectScanner and adopt command)
# --------------------------------------------------------------------------

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "tests": "Test files",
    "notebooks": "Jupyter notebooks",
    "data": "Data files",
    "scripts": "Analysis scripts",
    "source": "Library source",
    "docs": "Documentation",
    "config": "Config files",
    "images": "Images / figures",
    "other": "Other files",
}

# Default target subdirectory (relative to new project root) for each category.
# "{package_name}" is substituted at runtime.
CATEGORY_DEFAULT_DIRS: dict[str, str] = {
    "tests": "tests",
    "notebooks": "notebooks",
    "data": "data",
    "scripts": "scripts",
    "source": "src/{package_name}",
    "docs": "docs",
    "config": "",  # empty string → project root
    "images": "plots",
    "other": "_research",
}

# Files that pywatson regenerates from templates; skip copying from source.
_REGENERATED_FILES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "MANIFEST.in",
        "tox.ini",
        "requirements.txt",
    }
)

# Valid license choices and their template filenames
LICENSE_TEMPLATES = {
    "MIT": "LICENSE_MIT.jinja2",
    "BSD-3-Clause": "LICENSE_BSD3.jinja2",
    "Apache-2.0": "LICENSE_APACHE2.jinja2",
    "ISC": "LICENSE_ISC.jinja2",
}

# Valid linting modes
LINTING_MODES = ["minimal", "strict"]

# Valid type checkers
TYPE_CHECKERS = ["ty", "mypy", "none"]


class ProjectScaffolder:
    """Main class for scaffolding Python projects.

    Supports three project types:
      - ``default``: PyWatson standard layout with data/{sims, exp_raw, exp_pro}
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
        python_version: str = "3.12",
        linting_mode: str = "minimal",
        type_checker: str = "ty",
        docker: bool = False,
    ) -> None:
        self.project_name = project_name
        self.project_path = project_path
        self.package_name = project_name.lower().replace("-", "_").replace(" ", "_")
        self.project_type = project_type
        self.license_type = license_type
        self.python_version = python_version
        self.linting_mode = linting_mode
        self.type_checker = type_checker
        self.docker = docker

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

        # Validate linting_mode
        if self.linting_mode not in LINTING_MODES:
            raise ValueError(
                f"Unknown linting mode '{self.linting_mode}'. "
                f"Valid options: {', '.join(LINTING_MODES)}"
            )

        # Validate type_checker
        if self.type_checker not in TYPE_CHECKERS:
            raise ValueError(
                f"Unknown type checker '{self.type_checker}'. "
                f"Valid options: {', '.join(TYPE_CHECKERS)}"
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

    def _base_context(self, author_name: str = "", author_email: str = "") -> dict:
        """Build the base Jinja2 context shared by all templates.

        Args:
            author_name: Author's full name.
            author_email: Author's email address.

        Returns:
            Dictionary of template variables.
        """
        python_version_nodot = self.python_version.replace(".", "")
        return {
            "project_name": self.project_name,
            "project_name_title": (self.project_name.title().replace("-", " ").replace("_", " ")),
            "package_name": self.package_name,
            "author_name": author_name,
            "author_email": author_email,
            "project_type": self.project_type,
            "license_type": self.license_type,
            "python_version": self.python_version,
            "python_version_nodot": python_version_nodot,
            "linting_mode": self.linting_mode,
            "type_checker": self.type_checker,
        }

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
                # PyWatson-style data subdirectories
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
            # If pyproject.toml already exists, assume the directory has been
            # initialized with uv already — skip uv init to avoid failure.
            pyproject_file = self.project_path / "pyproject.toml"
            if pyproject_file.exists():
                console.print(
                    f"pyproject.toml already exists in {self.project_path}; skipping 'uv init'",
                    style="dim",
                )
                return

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

            # Remove .python-version created by uv init — it pins an exact
            # patch version (e.g. "3.12.9") which is overly restrictive.
            # The requires-python field in pyproject.toml is sufficient.
            python_version_file = self.project_path / ".python-version"
            if python_version_file.exists():
                python_version_file.unlink()
                console.print(
                    "Removed .python-version (version constraint handled by pyproject.toml)",
                    style="dim",
                )
        except Exception:
            # Ensure we always restore cwd on any exception
            os.chdir(original_cwd)
            raise
        finally:
            # Restore original working directory in all cases
            if Path.cwd() != original_cwd:
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

        context = self._base_context(author_name, author_email)

        # __init__.py
        init_content = self._render_template("__init__.py.jinja2", **context)
        (self.project_path / "src" / self.package_name / "__init__.py").write_text(init_content)

        # core.py
        core_content = self._render_template("core.py.jinja2", **context)
        (self.project_path / "src" / self.package_name / "core.py").write_text(core_content)

        # pywatson_utils.py — copied verbatim (not templated)
        self._copy_utils_file()

    def _copy_utils_file(self) -> None:
        """Copy pywatson_utils.py (utils.py) directly to the generated project."""
        import shutil

        source_utils = Path(__file__).parent / "utils.py"
        target_utils = self.project_path / "src" / self.package_name / "pywatson_utils.py"

        if source_utils.exists():
            shutil.copy2(source_utils, target_utils)
        else:
            console.print(
                f"Warning: utils.py not found at {source_utils}",
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

        context = self._base_context()

        generate_script = self._render_template("generate_data.py.jinja2", **context)
        (self.project_path / "scripts" / "generate_data.py").write_text(generate_script)

        analyze_script = self._render_template("analyze_data.py.jinja2", **context)
        (self.project_path / "scripts" / "analyze_data.py").write_text(analyze_script)

        showcase_script = self._render_template("pywatson_showcase.py.jinja2", **context)
        (self.project_path / "scripts" / "pywatson_showcase.py").write_text(showcase_script)

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
                "- **{}**: {}".format(
                    dep.split("==")[0]
                    if "==" in dep
                    else (dep.split(">=")[0] if ">=" in dep else dep),
                    dep,
                )
                for dep in dependencies
            ]
        )

        context = self._base_context(author_name, author_email)
        context["description"] = description
        context["deps_list"] = deps_list

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
            # Patch requires-python to match the user's chosen Python version
            content = re.sub(
                r'requires-python\s*=\s*">=[\d.]+"',
                f'requires-python = ">={self.python_version}"',
                content,
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

        context = self._base_context(author_name, author_email)

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
    # Docker files
    # ------------------------------------------------------------------

    def create_docker_files(self, author_name: str = "", author_email: str = "") -> None:
        """Create Docker-related files for a reproducible project environment.

        Generates:
          - Dockerfile
          - .dockerignore
          - docker-compose.yml
          - README_DOCKER.md
          - .github/workflows/docker-publish.yml (if .github/workflows/ exists)

        Args:
            author_name: Author's full name (included in template context).
            author_email: Author's email address (included in template context).
        """
        console.print("Creating Docker files...", style="bold blue")

        context = self._base_context(author_name, author_email)

        # Dockerfile
        dockerfile_content = self._render_template("Dockerfile.jinja2", **context)
        (self.project_path / "Dockerfile").write_text(dockerfile_content)

        # .dockerignore
        dockerignore_content = self._render_template("dockerignore.jinja2", **context)
        (self.project_path / ".dockerignore").write_text(dockerignore_content)

        # docker-compose.yml
        compose_content = self._render_template("docker-compose.yml.jinja2", **context)
        (self.project_path / "docker-compose.yml").write_text(compose_content)

        # README_DOCKER.md
        readme_docker_content = self._render_template("README_DOCKER.md.jinja2", **context)
        (self.project_path / "README_DOCKER.md").write_text(readme_docker_content)

        # .github/workflows/docker-publish.yml — only when the workflows dir exists
        workflows_dir = self.project_path / ".github" / "workflows"
        if workflows_dir.exists():
            publish_content = self._render_template("docker-publish.yml.jinja2", **context)
            (workflows_dir / "docker-publish.yml").write_text(publish_content)
        else:
            console.print(
                "  Skipping docker-publish.yml (no .github/workflows/ directory). "
                "Use --project-type full or create the directory manually.",
                style="dim",
            )

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
# ProjectScanner — classify files in an unstructured project
# ==========================================================================


class ProjectScanner:
    """Scan an existing unstructured Python project and classify its files.

    Walks the source directory, ignores hidden/build artefacts, and assigns
    every file to one of these categories: ``tests``, ``notebooks``,
    ``data``, ``scripts``, ``source``, ``docs``, ``config``, ``images``,
    ``other``.

    Args:
        source_path: Root of the existing project to scan.
    """

    DATA_EXTENSIONS: frozenset[str] = frozenset(
        {
            ".h5",
            ".hdf5",
            ".npz",
            ".npy",
            ".csv",
            ".json",
            ".pkl",
            ".pickle",
            ".mat",
            ".nc",
            ".zarr",
            ".parquet",
            ".feather",
            ".xlsx",
            ".xls",
        }
    )
    NOTEBOOK_EXTENSIONS: frozenset[str] = frozenset({".ipynb"})
    DOC_EXTENSIONS: frozenset[str] = frozenset({".md", ".rst", ".tex", ".pdf"})
    CONFIG_EXTENSIONS: frozenset[str] = frozenset(
        {
            ".yml",
            ".yaml",
            ".cfg",
            ".ini",
            ".toml",
            ".env",
        }
    )
    IMAGE_EXTENSIONS: frozenset[str] = frozenset(
        {
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".eps",
            ".gif",
        }
    )
    IGNORE_DIRS: frozenset[str] = frozenset(
        {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            ".env",
            "node_modules",
            ".mypy_cache",
            ".ruff_cache",
            ".pytest_cache",
            ".tox",
            ".nox",
            "dist",
            "build",
            "site-packages",
        }
    )
    IGNORE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo", ".pyd"})

    def __init__(self, source_path: Path) -> None:
        self.source_path = Path(source_path).resolve()

    def scan(self) -> dict[str, list[Path]]:
        """Scan and classify all files in the source directory.

        Returns:
            Dictionary mapping category name → list of absolute Paths.
            Categories: ``tests``, ``notebooks``, ``data``, ``scripts``,
            ``source``, ``docs``, ``config``, ``images``, ``other``.
        """
        classified: dict[str, list[Path]] = {
            "tests": [],
            "notebooks": [],
            "data": [],
            "scripts": [],
            "source": [],
            "docs": [],
            "config": [],
            "images": [],
            "other": [],
        }
        for path in self._iter_files():
            cat = self._classify(path)
            classified.setdefault(cat, []).append(path)
        return classified

    def _iter_files(self):
        """Yield all non-ignored files under source_path, sorted."""
        for path in sorted(self.source_path.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.source_path)
            # Skip if any parent directory is in the ignore set
            if any(
                part in self.IGNORE_DIRS or part.endswith(".egg-info") for part in rel.parts[:-1]
            ):
                continue
            if path.suffix in self.IGNORE_SUFFIXES:
                continue
            yield path

    def _classify(self, path: Path) -> str:
        """Classify a single file into a category string."""
        ext = path.suffix.lower()
        name = path.name

        if ext in self.NOTEBOOK_EXTENSIONS:
            return "notebooks"
        if ext in self.DATA_EXTENSIONS:
            return "data"
        if ext in self.IMAGE_EXTENSIONS:
            return "images"
        if name.lower() in {
            "readme.md",
            "readme.rst",
            "readme.txt",
            "changelog.md",
            "contributing.md",
            "license",
            "licence",
        }:
            return "docs"
        if ext in self.DOC_EXTENSIONS:
            return "docs"
        if name in {".gitignore", ".gitattributes", "Makefile", "makefile"}:
            return "config"
        if ext in self.CONFIG_EXTENSIONS:
            return "config"
        if name in {
            "requirements.txt",
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "MANIFEST.in",
            "tox.ini",
        }:
            return "config"
        if ext == ".py":
            return self._classify_python_file(path)
        if ext in {".sh", ".bash", ".bat", ".ps1"}:
            return "scripts"
        return "other"

    def _classify_python_file(self, path: Path) -> str:
        """Classify a ``.py`` file as ``tests``, ``scripts``, or ``source``.

        Uses filename patterns first, then content heuristics.

        Args:
            path: Absolute path to the Python file.

        Returns:
            Category string: ``"tests"``, ``"scripts"``, or ``"source"``.
        """
        name = path.name
        # Name-based test detection
        if name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
            return "tests"

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, PermissionError):
            return "source"

        # Content-based test detection
        _test_patterns = (
            r"\bdef test_\w+",
            r"\bclass Test\w+",
            r"\bimport pytest\b",
            r"\bimport unittest\b",
            r"@pytest\.mark\.",
        )
        if any(re.search(p, content) for p in _test_patterns):
            return "tests"

        # Script indicators: executable entry point or CLI framework
        _script_patterns = (
            r"if\s+__name__\s*==\s*['\"]__main__['\"]",
            r"\bimport click\b",
            r"\bimport argparse\b",
            r"\bimport optparse\b",
        )
        if any(re.search(p, content) for p in _script_patterns):
            return "scripts"

        # Source indicators: at least one top-level function or class definition
        if re.search(r"^(?:def |class )", content, re.MULTILINE):
            return "source"

        return "scripts"

    def print_summary(self, classified: dict[str, list[Path]]) -> None:
        """Print a Rich table summarising the scan results.

        Args:
            classified: Output from :meth:`scan`.
        """
        from rich.table import Table

        table = Table(
            title="Scanned Files",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Category", style="cyan", width=16)
        table.add_column("Files", justify="right", width=6)
        table.add_column("Examples", style="dim")

        total = 0
        for cat in (
            "tests",
            "notebooks",
            "data",
            "scripts",
            "source",
            "docs",
            "config",
            "images",
            "other",
        ):
            files = classified.get(cat, [])
            if not files:
                continue
            total += len(files)
            sample = [f.relative_to(self.source_path) for f in files[:3]]
            sample_str = ", ".join(str(s) for s in sample)
            if len(files) > 3:
                sample_str += f"  (+{len(files) - 3} more)"
            table.add_row(CATEGORY_DESCRIPTIONS.get(cat, cat), str(len(files)), sample_str)

        console.print(table)
        console.print(f"[bold]{total} files found[/bold]")


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


@click.group()
@click.version_option(version=__version__, prog_name="pywatson")
def cli() -> None:
    """PyWatson -- Python scientific project manager.

    Use 'pywatson init PROJECT_NAME' to scaffold a new project.
    """


@cli.command("init")
@click.argument("project_name")
@click.option(
    "--path",
    "-p",
    type=click.Path(),
    default=".",
    help="Directory to create the project in.",
)
@click.option(
    "--author-name",
    prompt="Author name",
    default=lambda: _git_config("user.name"),
    show_default="git config user.name",
    help="Author name.",
)
@click.option(
    "--author-email",
    prompt="Author email",
    default=lambda: _git_config("user.email"),
    show_default="git config user.email",
    help="Author email.",
)
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
    "--python-version",
    default="3.12",
    show_default=True,
    help="Target Python version (e.g. 3.11, 3.12).",
)
@click.option(
    "--linting",
    "linting_mode",
    type=click.Choice(LINTING_MODES, case_sensitive=False),
    default="minimal",
    show_default=True,
    help="Ruff ruleset: minimal (E,F,W,I) or strict (adds D,N,B,SIM,RUF,UP).",
)
@click.option(
    "--type-checker",
    type=click.Choice(TYPE_CHECKERS, case_sensitive=False),
    default="ty",
    show_default=True,
    help="Type checker for the generated project (ty, mypy, or none).",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    help="Environment file (environment.yml) to import dependencies from.",
)
@click.option("--force", is_flag=True, help="Overwrite existing directory.")
@click.option(
    "--docker",
    is_flag=True,
    default=False,
    help="Scaffold Docker + docker-compose files for Zenodo reproducibility.",
)
def init_project(
    project_name: str,
    path: str,
    author_name: str,
    author_email: str,
    description: str,
    project_type: str,
    license_type: str,
    python_version: str,
    linting_mode: str,
    type_checker: str,
    env_file: str | None,
    force: bool,
    docker: bool,
) -> None:
    """Create a new Python project with modern tooling and best practices.

    This tool creates a complete project structure similar to DrWatson.jl
    with uv for dependency management, comprehensive documentation,
    example code, and tests.

    PROJECT_NAME is the name for your new project (e.g. 'my-simulation').
    """
    console.print(f"Creating project: [bold blue]{project_name}[/bold blue]")
    console.print(f"  Type         : [cyan]{project_type}[/cyan] ({PROJECT_TYPES[project_type]})")
    console.print(f"  License      : [cyan]{license_type}[/cyan]")
    console.print(f"  Python       : [cyan]{python_version}[/cyan]")
    console.print(f"  Linting      : [cyan]{linting_mode}[/cyan]")
    console.print(f"  Type checker : [cyan]{type_checker}[/cyan]")
    console.print(f"  Docker       : [cyan]{docker}[/cyan]")
    console.print(f"  Working dir  : [dim]{Path.cwd()}[/dim]")

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

    # Add the chosen type checker as a dev dependency
    if type_checker == "ty":
        dev_dependencies.append("ty>=0.0.1")
    elif type_checker == "mypy":
        dev_dependencies.append("mypy>=1.13.0")

    # Create scaffolder and build project
    scaffolder = ProjectScaffolder(
        project_name,
        project_path,
        project_type=project_type,
        license_type=license_type,
        python_version=python_version,
        linting_mode=linting_mode,
        type_checker=type_checker,
        docker=docker,
    )

    try:
        # 1. Directory structure
        scaffolder.create_project_structure()

        # 2. uv init
        scaffolder.initialize_uv_project()

        # 3. Dependencies
        scaffolder.add_dependencies(dependencies, dev_dependencies)

        # 4. Source files (includes pywatson_utils.py copy)
        scaffolder.create_source_files(author_name, author_email)

        # 5. Tests
        scaffolder.create_test_files()

        # 6. Example scripts (includes pywatson_showcase.py)
        scaffolder.create_example_script()

        # 7. README
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

        # 13. Docker files (optional, any project type)
        if docker:
            scaffolder.create_docker_files(author_name, author_email)

        console.print("\nProject created successfully!", style="bold green")
        console.print(f"\nProject location: [blue]{project_path.absolute()}[/blue]")

        console.print("\nNext steps:")
        console.print(f"   cd {project_name}")
        console.print("   uv sync                                       # Install dependencies")
        console.print("   uv run pytest                                 # Run tests")
        console.print("   uv run python scripts/pywatson_showcase.py    # Run API showcase")
        console.print("   uv run python scripts/generate_data.py        # Generate example data")
        if project_type == "full":
            console.print(
                "   make check                                    # Run all quality checks"
            )

    except Exception as e:
        console.print(f"Error creating project: {e}", style="bold red")
        sys.exit(1)


# Backward-compatible entry point alias for the `pywatson-init` script.
# Allows the old entry point (`pywatson.core:create_project`) to keep working
# while the canonical invocation is now `pywatson init PROJECT_NAME`.
create_project = init_project


# ==========================================================================
# Additional CLI subcommands
# ==========================================================================


@cli.command("status")
def status_command() -> None:
    """Show an overview of the current PyWatson project."""
    from pathlib import Path

    # Try to find project root
    cwd = Path.cwd()
    root = None
    cur = cwd
    while cur != cur.parent:
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            root = cur
            break
        cur = cur.parent

    if root is None:
        console.print("[bold red]Not inside a PyWatson project.[/bold red]")
        console.print("Hint: run 'pywatson init PROJECT_NAME' to create one.")
        return

    console.print(f"[bold green]PyWatson project[/bold green]: {root}")

    # Read project name from pyproject.toml if possible
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        import re as _re

        m = _re.search(r'name\s*=\s*"([^"]+)"', content)
        if m:
            console.print(f"  Name       : [cyan]{m.group(1)}[/cyan]")

    # Directory summary
    dirs_of_interest = ["data", "plots", "scripts", "notebooks", "tests", "_research"]
    console.print("\n[bold]Directories:[/bold]")
    for d in dirs_of_interest:
        p = root / d
        if p.exists():
            n_files = sum(1 for _ in p.rglob("*") if _.is_file())
            console.print(f"  [green]✓[/green] {d:<14} ({n_files} files)")
        else:
            console.print(f"  [dim]– {d}[/dim]")

    # Data files
    data_dir = root / "data"
    if data_dir.exists():
        h5_files = list(data_dir.rglob("*.h5"))
        npz_files = list(data_dir.rglob("*.npz"))
        zarr_stores = list(data_dir.rglob("*.zarr"))
        console.print("\n[bold]Data files:[/bold]")
        console.print(f"  HDF5  (.h5) : {len(h5_files)}")
        console.print(f"  NumPy (.npz): {len(npz_files)}")
        console.print(f"  Zarr  (.zarr): {len(zarr_stores)}")

    # Git status
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False
        ).stdout.strip()
        console.print("\n[bold]Git:[/bold]")
        console.print(f"  Branch  : {branch}")
        console.print(f"  Commit  : {commit}")
        clean = "[green]yes[/green]" if not dirty else "[yellow]no (uncommitted changes)[/yellow]"
        console.print(f"  Clean   : {clean}")
    except Exception:
        pass


@cli.command("sweep")
@click.argument("params", nargs=-1, metavar="KEY=VAL[,VAL...] ...")
@click.option("--suffix", default=".h5", show_default=True, help="File suffix.")
@click.option(
    "--connector", default="_", show_default=True, help="Connector between key=value pairs."
)
def sweep_command(params: tuple, suffix: str, connector: str) -> None:
    """Print filenames for a parameter sweep.

    Pass KEY=VAL or KEY=VAL1,VAL2,... arguments to generate all combinations.

    \b
    Example:
      pywatson sweep alpha=0.1,0.5,1.0 N=100,1000 --suffix .h5
    """
    import itertools

    if not params:
        console.print("Provide at least one KEY=VAL argument.", style="yellow")
        console.print("Example: pywatson sweep alpha=0.1,0.5 N=100,1000")
        return

    param_dict: dict = {}
    for token in params:
        if "=" not in token:
            console.print(f"[red]Invalid token '{token}'. Expected KEY=VAL or KEY=V1,V2,...[/red]")
            return
        key, _, raw = token.partition("=")
        vals_raw = raw.split(",")
        coerced: list[int | float | str] = []
        for v in vals_raw:
            try:
                coerced.append(int(v))
            except ValueError:
                try:
                    coerced.append(float(v))
                except ValueError:
                    coerced.append(v)
        param_dict[key] = coerced

    keys = list(param_dict.keys())
    combos = list(itertools.product(*param_dict.values()))

    from pywatson.utils import savename

    console.print(f"[bold]{len(combos)} combinations:[/bold]")
    for combo in combos:
        d = dict(zip(keys, combo))
        console.print(f"  {savename(d, suffix=suffix, connector=connector)}")


@cli.command("summary")
@click.option("--subdir", default=None, help="Subdirectory within data/ to summarise.")
@click.option("--recursive", is_flag=True, default=True, help="Search recursively.")
def summary_command(subdir: str | None, recursive: bool) -> None:
    """Summarise HDF5 data files in the project data directory."""
    from pywatson.utils import collect_results

    try:
        results = collect_results(subdir=subdir, recursive=recursive)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        return

    if not results:
        console.print("[yellow]No HDF5 files found.[/yellow]")
        return

    console.print(f"[bold green]{len(results)} file(s) found:[/bold green]")
    for row in results:
        fp = row.get("_filepath", "?")
        meta = row.get("_metadata", {})
        created = meta.get("created_at", "")
        keys = [k for k in row if not k.startswith("_")]
        console.print(f"  [cyan]{fp}[/cyan]")
        if created:
            console.print(f"    created : {created}")
        if keys:
            console.print(f"    datasets: {', '.join(keys)}")


# ==========================================================================
# adopt command — import an existing unstructured project
# ==========================================================================


@cli.command("adopt")
@click.argument("source_path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--project-name",
    "-n",
    default=None,
    help="Name for the new project (default: source directory name).",
)
@click.option(
    "--output-path",
    "-o",
    type=click.Path(),
    default=None,
    help="Parent directory for the new project (default: alongside source with _pywatson suffix).",
)
@click.option(
    "--auto",
    is_flag=True,
    default=False,
    help="Accept all classification defaults without interactive prompts.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would happen without writing any files.",
)
@click.option(
    "--copy/--move",
    "do_copy",
    default=True,
    help="Copy files (default) or move them from the source.",
)
@click.option(
    "--no-uv",
    is_flag=True,
    default=False,
    help="Skip 'uv init' (structure + files only, useful for offline/testing).",
)
@click.option(
    "--author-name",
    default=lambda: _git_config("user.name"),
    help="Author name (defaults to git config user.name).",
)
@click.option(
    "--author-email",
    default=lambda: _git_config("user.email"),
    help="Author email (defaults to git config user.email).",
)
@click.option("--description", default="", help="Short project description.")
@click.option(
    "--project-type",
    "-t",
    type=click.Choice(list(PROJECT_TYPES.keys()), case_sensitive=False),
    default="default",
    show_default=True,
    help="Target pywatson project type.",
)
@click.option(
    "--license",
    "license_type",
    type=click.Choice(list(LICENSE_TEMPLATES.keys()), case_sensitive=False),
    default="MIT",
    show_default=True,
    help="License type.",
)
@click.option(
    "--python-version",
    default="3.12",
    show_default=True,
    help="Target Python version (e.g. 3.11, 3.12).",
)
def adopt_command(
    source_path: str,
    project_name: str | None,
    output_path: str | None,
    auto: bool,
    dry_run: bool,
    do_copy: bool,
    no_uv: bool,
    author_name: str,
    author_email: str,
    description: str,
    project_type: str,
    license_type: str,
    python_version: str,
) -> None:
    """Adopt an existing unstructured project into a pywatson layout.

    Scans SOURCE_PATH (default: current directory) for Python scripts, data
    files, notebooks, tests, and configuration.  Each file group is shown with
    its proposed destination and the user is prompted for confirmation.

    Use --auto to accept all defaults without prompts (good for scripting).
    Use --dry-run to preview the plan without writing anything.
    Use --no-uv to skip 'uv init' (structure only, full offline operation).

    \b
    Examples:
      pywatson adopt ./old_project --auto
      pywatson adopt ./old_project --project-name my_sim --output-path ~/projects
      pywatson adopt ./old_project --dry-run
    """
    import shutil

    source = Path(source_path).resolve()
    proj_name = project_name or source.name
    package_name = proj_name.lower().replace("-", "_").replace(" ", "_")

    # Compute destination root
    if output_path:
        dest_root = Path(output_path).resolve() / proj_name
    elif project_name and project_name != source.name:
        dest_root = source.parent / proj_name
    else:
        dest_root = source.parent / f"{proj_name}_pywatson"

    # Guard: refuse to overwrite the source with itself
    if dest_root.resolve() == source.resolve():
        console.print(
            "[bold red]Error:[/bold red] destination is the same as source. "
            "Use --project-name or --output-path to set a different target.",
        )
        sys.exit(1)

    if dry_run:
        action = "[yellow]dry-run[/yellow]"
    elif do_copy:
        action = "[dim]copy[/dim]"
    else:
        action = "[dim]move[/dim]"
    console.print("\n[bold blue]PyWatson Adopt[/bold blue]")
    console.print(f"  Source  : [dim]{source}[/dim]")
    console.print(f"  Target  : [green]{dest_root}[/green]")
    console.print(f"  Mode    : {'[dim]auto[/dim]' if auto else '[cyan]interactive[/cyan]'}")
    console.print(f"  Action  : {action}")

    if dest_root.exists() and not dry_run:
        if not auto:
            if not Confirm.ask(f"Destination {dest_root} already exists. Continue?"):
                console.print("Aborted.")
                return

    # ------------------------------------------------------------------ scan
    console.print("\n[bold]Scanning project...[/bold]")
    scanner = ProjectScanner(source)
    classified = scanner.scan()
    scanner.print_summary(classified)

    # ------------------------------------------------------------------ build plan
    # List of (src_absolute, dest_absolute) pairs
    plan: list[tuple[Path, Path]] = []
    skipped_regen: list[str] = []

    for cat, files in classified.items():
        if not files:
            continue

        default_subdir = CATEGORY_DEFAULT_DIRS.get(cat, "_research")
        if "{package_name}" in default_subdir:
            default_subdir = default_subdir.replace("{package_name}", package_name)

        target_dir = dest_root / default_subdir if default_subdir else dest_root

        if not auto:
            suffix = f"[green]{target_dir.name}[/green]" if default_subdir else "[green].[/green]"
            console.print(
                f"\n[bold cyan]{CATEGORY_DESCRIPTIONS.get(cat, cat)}[/bold cyan] "
                f"({len(files)} files) → {suffix}"
            )
            for f in files:
                rel = f.relative_to(source)
                marker = (
                    "  [dim italic](regenerated by pywatson)[/dim italic]"
                    if f.name in _REGENERATED_FILES
                    else ""
                )
                console.print(f"  [dim]{rel}[/dim]{marker}")

            choice = click.prompt(
                "  [y]es / [s]kip / [r]ename target",
                default="y",
                type=click.Choice(["y", "s", "r"], case_sensitive=False),
                show_choices=False,
            )
            if choice == "s":
                continue
            if choice == "r":
                new_sub = click.prompt("  New target (relative to project root)")
                target_dir = dest_root / new_sub

        for f in files:
            if f.name in _REGENERATED_FILES:
                skipped_regen.append(f.name)
                continue
            # Skip files that are inside dest_root to avoid same-file copies
            try:
                f.resolve().relative_to(dest_root.resolve())
                continue  # this file is already inside the destination
            except ValueError:
                pass
            # Flatten: place file directly in target_dir (no source subdirectory preserved)
            dest_file = target_dir / f.name
            plan.append((f, dest_file))

    # ------------------------------------------------------------------ dry run output
    if dry_run:
        console.print(
            f"\n[bold yellow]Dry run — {len(plan)} file(s) would be "
            f"{'copied' if do_copy else 'moved'}:[/bold yellow]"
        )
        for src_f, dst_f in plan:
            src_rel = src_f.relative_to(source)
            dst_rel = dst_f.relative_to(dest_root)
            console.print(f"  [dim]{src_rel}[/dim]  →  [green]{dst_rel}[/green]")
        if skipped_regen:
            console.print(f"\n  [dim]Skipped (regenerated): {', '.join(set(skipped_regen))}[/dim]")
        return  # ← exit here, nothing written

    # ------------------------------------------------------------------ confirm
    if not auto:
        if not Confirm.ask(f"\nCreate project at {dest_root}?"):
            console.print("Aborted.")
            return

    # ------------------------------------------------------------------ scaffold
    scaffolder = ProjectScaffolder(
        proj_name,
        dest_root,
        project_type=project_type,
        license_type=license_type,
        python_version=python_version,
    )
    scaffolder.create_project_structure()

    # Pywatson boilerplate (placed first so user files can overwrite on collision)
    scaffolder.create_gitignore()
    scaffolder.create_license(author_name)
    scaffolder._copy_utils_file()

    # Minimal __init__.py and tests/__init__.py to make packages importable
    pkg_init = dest_root / "src" / package_name / "__init__.py"
    if not pkg_init.exists():
        pkg_init.write_text(f'"""Package {proj_name}."""\n')

    tests_init = dest_root / "tests" / "__init__.py"
    if not tests_init.exists():
        tests_init.write_text("# Tests package\n")

    # Generate README only if source has no README (docs category gets copied next)
    has_source_readme = any(
        f.name.lower() in {"readme.md", "readme.rst", "readme.txt"}
        for f in classified.get("docs", [])
    )
    if not has_source_readme:
        scaffolder.create_readme(author_name, author_email, [], description)

    # ------------------------------------------------------------------ copy files
    n_copied = 0
    for src_f, dst_f in plan:
        dst_f.parent.mkdir(parents=True, exist_ok=True)
        try:
            if do_copy:
                shutil.copy2(src_f, dst_f)
            else:
                shutil.move(str(src_f), str(dst_f))
            n_copied += 1
        except shutil.SameFileError:
            # Source and destination resolved to the same inode — skip silently
            continue

    # ------------------------------------------------------------------ optional uv
    if not no_uv:
        console.print("\n[bold blue]Initialising uv project...[/bold blue]")
        scaffolder.initialize_uv_project()

    # ------------------------------------------------------------------ finish
    console.print(f"\n[bold green]✓ Project adopted at {dest_root}[/bold green]")
    console.print(f"  Files copied : {n_copied}")
    if skipped_regen:
        console.print(
            f"  Skipped      : {', '.join(set(skipped_regen))} "
            f"[dim](regenerated by pywatson)[/dim]"
        )
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  cd {dest_root.name}")
    if no_uv:
        console.print("  uv sync       # install dependencies")
    console.print("  uv run pytest")


if __name__ == "__main__":
    cli()

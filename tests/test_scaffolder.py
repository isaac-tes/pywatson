"""
Integration tests for project scaffolding functionality.

Tests the ProjectScaffolder class with all three project types
(default, minimal, full) and license options.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from pywatson.core import ProjectScaffolder, PROJECT_TYPES, LICENSE_TEMPLATES


class TestProjectScaffolder:
    """Test the ProjectScaffolder class."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for test projects."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def scaffolder(self, temp_project_dir):
        """Create a ProjectScaffolder instance for testing (default type)."""
        project_path = temp_project_dir / "test_project"
        project_path.mkdir()
        return ProjectScaffolder("test-project", project_path)

    # ------------------------------------------------------------------
    # Initialization tests
    # ------------------------------------------------------------------

    def test_scaffolder_initialization(self, scaffolder):
        """Test that scaffolder initializes correctly with defaults."""
        assert scaffolder.project_name == "test-project"
        assert scaffolder.package_name == "test_project"
        assert scaffolder.project_type == "default"
        assert scaffolder.license_type == "MIT"
        assert scaffolder.jinja_env is not None

    def test_scaffolder_with_project_type(self, temp_project_dir):
        """Test scaffolder initialization with explicit project type."""
        for ptype in PROJECT_TYPES:
            project_path = temp_project_dir / f"test_{ptype}"
            project_path.mkdir(exist_ok=True)
            s = ProjectScaffolder("test-project", project_path, project_type=ptype)
            assert s.project_type == ptype

    def test_scaffolder_with_license_type(self, temp_project_dir):
        """Test scaffolder initialization with explicit license type."""
        for ltype in LICENSE_TEMPLATES:
            project_path = temp_project_dir / f"test_{ltype.replace('-', '_')}"
            project_path.mkdir(exist_ok=True)
            s = ProjectScaffolder("test-project", project_path, license_type=ltype)
            assert s.license_type == ltype

    def test_invalid_project_type_raises(self, temp_project_dir):
        """Test that an invalid project type raises ValueError."""
        project_path = temp_project_dir / "bad_type"
        project_path.mkdir()
        with pytest.raises(ValueError, match="Unknown project type"):
            ProjectScaffolder("test-project", project_path, project_type="nonexistent")

    def test_invalid_license_type_raises(self, temp_project_dir):
        """Test that an invalid license type raises ValueError."""
        project_path = temp_project_dir / "bad_license"
        project_path.mkdir()
        with pytest.raises(ValueError, match="Unknown license type"):
            ProjectScaffolder("test-project", project_path, license_type="WTFPL")

    def test_package_name_sanitization(self, temp_project_dir):
        """Test that package names are sanitized correctly."""
        test_cases = [
            ("my-project", "my_project"),
            ("My Project", "my_project"),
            ("my_project", "my_project"),
            ("My-Cool-Project", "my_cool_project"),
        ]

        for project_name, expected_package_name in test_cases:
            project_path = temp_project_dir / project_name
            project_path.mkdir(exist_ok=True)
            scaffolder = ProjectScaffolder(project_name, project_path)
            assert scaffolder.package_name == expected_package_name

    # ------------------------------------------------------------------
    # Directory structure tests per project type
    # ------------------------------------------------------------------

    def test_create_project_structure_default(self, temp_project_dir):
        """Test default project type creates DrWatson.jl-style directories."""
        project_path = temp_project_dir / "default_project"
        project_path.mkdir()
        scaffolder = ProjectScaffolder("default-project", project_path, project_type="default")
        scaffolder.create_project_structure()

        expected_dirs = [
            "src",
            f"src/{scaffolder.package_name}",
            "scripts",
            "notebooks",
            "tests",
            "plots",
            "data",
            "data/sims",
            "data/exp_raw",
            "data/exp_pro",
            "docs",
            "_research",
            "_research/tmp",
        ]

        for dir_path in expected_dirs:
            full_path = project_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"
            assert full_path.is_dir(), f"{dir_path} is not a directory"

    def test_create_project_structure_minimal(self, temp_project_dir):
        """Test minimal project type creates only essential directories."""
        project_path = temp_project_dir / "minimal_project"
        project_path.mkdir()
        scaffolder = ProjectScaffolder("minimal-project", project_path, project_type="minimal")
        scaffolder.create_project_structure()

        expected_dirs = [
            "src",
            f"src/{scaffolder.package_name}",
            "scripts",
            "tests",
            "data",
            "docs",
        ]

        for dir_path in expected_dirs:
            full_path = project_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"

        # Minimal should NOT have these
        absent_dirs = ["notebooks", "plots", "_research", "config"]
        for dir_path in absent_dirs:
            full_path = project_path / dir_path
            assert not full_path.exists(), f"Directory {dir_path} should not exist in minimal"

    def test_create_project_structure_full(self, temp_project_dir):
        """Test full project type creates all directories including config/ and CI."""
        project_path = temp_project_dir / "full_project"
        project_path.mkdir()
        scaffolder = ProjectScaffolder("full-project", project_path, project_type="full")
        scaffolder.create_project_structure()

        # Full includes everything from default plus extras
        expected_dirs = [
            "src",
            f"src/{scaffolder.package_name}",
            "scripts",
            "notebooks",
            "tests",
            "plots",
            "data",
            "data/sims",
            "data/exp_raw",
            "data/exp_pro",
            "docs",
            "_research",
            "_research/tmp",
            "config",
            ".github",
            ".github/workflows",
        ]

        for dir_path in expected_dirs:
            full_path = project_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------

    def test_render_template(self, scaffolder):
        """Test the _render_template helper method."""
        context = {
            "project_name": "test-project",
            "project_name_title": "Test Project",
            "package_name": "test_project",
            "author_name": "Test Author",
            "author_email": "test@example.com",
        }

        content = scaffolder._render_template("__init__.py.jinja2", **context)

        assert isinstance(content, str)
        assert len(content) > 0
        assert "from .core import" in content
        assert "Test Author" in content

    # ------------------------------------------------------------------
    # Source file creation
    # ------------------------------------------------------------------

    def test_create_source_files(self, scaffolder):
        """Test that source files are created correctly."""
        scaffolder.create_project_structure()
        scaffolder.create_source_files("Test Author", "test@example.com")

        src_dir = scaffolder.project_path / "src" / scaffolder.package_name
        assert (src_dir / "__init__.py").exists()
        assert (src_dir / "core.py").exists()
        assert (src_dir / "drwatson.py").exists()

        init_content = (src_dir / "__init__.py").read_text()
        assert "Test Author" in init_content
        assert "test@example.com" in init_content
        assert "from .core import" in init_content
        assert "from .drwatson import" in init_content
        assert "load_selective" in init_content

        core_content = (src_dir / "core.py").read_text()
        assert "def hello_world()" in core_content
        assert "def create_example_data(" in core_content
        assert "def analyze_data(" in core_content

    def test_create_test_files(self, scaffolder):
        """Test that test files are created correctly."""
        scaffolder.create_project_structure()
        scaffolder.create_test_files()

        tests_dir = scaffolder.project_path / "tests"
        assert (tests_dir / "__init__.py").exists()
        assert (tests_dir / "test_core.py").exists()

        test_content = (tests_dir / "test_core.py").read_text()
        assert "def test_hello_world()" in test_content
        assert "def test_create_example_data_random()" in test_content
        assert "def test_analyze_data_basic()" in test_content
        assert scaffolder.package_name in test_content

    def test_create_example_script(self, scaffolder):
        """Test that example scripts are created correctly."""
        scaffolder.create_project_structure()
        scaffolder.create_example_script()

        scripts_dir = scaffolder.project_path / "scripts"
        assert (scripts_dir / "generate_data.py").exists()
        assert (scripts_dir / "analyze_data.py").exists()

        generate_content = (scripts_dir / "generate_data.py").read_text()
        assert "def main():" in generate_content
        assert "create_example_data" in generate_content
        assert scaffolder.package_name in generate_content

        analyze_content = (scripts_dir / "analyze_data.py").read_text()
        assert "def main():" in analyze_content
        assert "load_data" in analyze_content
        assert scaffolder.package_name in analyze_content

    # ------------------------------------------------------------------
    # .gitignore
    # ------------------------------------------------------------------

    def test_create_gitignore(self, scaffolder):
        """Test that .gitignore is created with DrWatson-style entries."""
        scaffolder.create_gitignore()

        gitignore_path = scaffolder.project_path / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert "__pycache__/" in content
        assert ".venv/" in content
        assert ".pytest_cache/" in content
        assert "data/" in content
        # DrWatson-specific entries
        assert "_research/tmp/" in content
        assert "papers/" in content or "papers/*.aux" in content

    # ------------------------------------------------------------------
    # License
    # ------------------------------------------------------------------

    def test_create_license_mit(self, temp_project_dir):
        """Test that MIT LICENSE file is created correctly."""
        project_path = temp_project_dir / "license_test"
        project_path.mkdir()
        scaffolder = ProjectScaffolder("license-test", project_path, license_type="MIT")
        scaffolder.create_license("Test Author")

        license_path = project_path / "LICENSE"
        assert license_path.exists()

        content = license_path.read_text()
        assert "MIT License" in content
        assert "Test Author" in content

    def test_create_license_all_types(self, temp_project_dir):
        """Test that all license types render correctly."""
        for ltype in LICENSE_TEMPLATES:
            project_path = temp_project_dir / f"license_{ltype.replace('-', '_')}"
            project_path.mkdir()
            scaffolder = ProjectScaffolder("test", project_path, license_type=ltype)
            scaffolder.create_license("Test Author")

            license_path = project_path / "LICENSE"
            assert license_path.exists(), f"LICENSE not created for {ltype}"
            content = license_path.read_text()
            assert "Test Author" in content, f"Author not in {ltype} license"
            assert len(content) > 50, f"{ltype} license is too short"

    # ------------------------------------------------------------------
    # Full extras
    # ------------------------------------------------------------------

    def test_create_full_extras(self, temp_project_dir):
        """Test that full project extras are created correctly."""
        project_path = temp_project_dir / "full_extras_test"
        project_path.mkdir()
        scaffolder = ProjectScaffolder("full-extras", project_path, project_type="full")
        scaffolder.create_project_structure()
        scaffolder.create_full_extras("Test Author", "test@example.com")

        # Verify all extra files exist
        expected_files = [
            "config/ruff.toml",
            "config/pytest.ini",
            "Makefile",
            ".github/workflows/ci.yml",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
        ]

        for file_path in expected_files:
            full_path = project_path / file_path
            assert full_path.exists(), f"File {file_path} was not created"
            content = full_path.read_text()
            assert len(content) > 0, f"File {file_path} is empty"

        # Verify content quality
        makefile = (project_path / "Makefile").read_text()
        assert "uv run pytest" in makefile
        assert "uv run ruff" in makefile

        ci = (project_path / ".github" / "workflows" / "ci.yml").read_text()
        assert "pytest" in ci
        assert "ruff" in ci

    # ------------------------------------------------------------------
    # Copy drwatson.py
    # ------------------------------------------------------------------

    def test_copy_drwatson_file(self, scaffolder):
        """Test that drwatson.py is copied correctly."""
        scaffolder.create_project_structure()
        scaffolder._copy_drwatson_file()

        drwatson_path = scaffolder.project_path / "src" / scaffolder.package_name / "drwatson.py"
        assert drwatson_path.exists()

        content = drwatson_path.read_text()
        assert "def datadir(" in content
        assert "def save_data(" in content
        assert "def load_data(" in content
        assert "def load_selective(" in content

    # ------------------------------------------------------------------
    # Notebook (only for default/full, not minimal)
    # ------------------------------------------------------------------

    def test_notebook_not_created_for_minimal(self, temp_project_dir):
        """Test that notebooks are skipped for minimal project type."""
        project_path = temp_project_dir / "minimal_no_notebook"
        project_path.mkdir()
        scaffolder = ProjectScaffolder("test", project_path, project_type="minimal")
        scaffolder.create_project_structure()
        scaffolder.create_example_notebook()

        notebooks_dir = project_path / "notebooks"
        assert not notebooks_dir.exists()


class TestFullProjectGeneration:
    """Integration tests for full project generation across all types."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for test projects."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_complete_default_project(self, temp_project_dir):
        """Test creating a complete default project with all components."""
        project_path = temp_project_dir / "full_default"
        project_path.mkdir()

        scaffolder = ProjectScaffolder(
            "full-default",
            project_path,
            project_type="default",
            license_type="MIT",
        )

        scaffolder.create_project_structure()
        scaffolder.create_source_files("Integration Test", "integration@test.com")
        scaffolder.create_test_files()
        scaffolder.create_example_script()
        scaffolder.create_gitignore()
        scaffolder.create_license("Integration Test")

        expected_files = [
            "src/full_default/__init__.py",
            "src/full_default/core.py",
            "src/full_default/drwatson.py",
            "tests/__init__.py",
            "tests/test_core.py",
            "scripts/generate_data.py",
            "scripts/analyze_data.py",
            ".gitignore",
            "LICENSE",
        ]

        for file_path in expected_files:
            full_path = project_path / file_path
            assert full_path.exists(), f"File {file_path} was not created"

        expected_dirs = [
            "notebooks",
            "plots",
            "data",
            "data/sims",
            "data/exp_raw",
            "data/exp_pro",
            "docs",
            "_research",
            "_research/tmp",
        ]

        for dir_path in expected_dirs:
            full_path = project_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"

    def test_complete_full_project(self, temp_project_dir):
        """Test creating a complete full project with all extras."""
        project_path = temp_project_dir / "full_project"
        project_path.mkdir()

        scaffolder = ProjectScaffolder(
            "full-project",
            project_path,
            project_type="full",
            license_type="BSD-3-Clause",
        )

        scaffolder.create_project_structure()
        scaffolder.create_source_files("Full Test", "full@test.com")
        scaffolder.create_test_files()
        scaffolder.create_example_script()
        scaffolder.create_gitignore()
        scaffolder.create_license("Full Test")
        scaffolder.create_full_extras("Full Test", "full@test.com")

        # Check full-specific files
        full_files = [
            "config/ruff.toml",
            "config/pytest.ini",
            "Makefile",
            ".github/workflows/ci.yml",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "LICENSE",
        ]

        for file_path in full_files:
            full_path = project_path / file_path
            assert full_path.exists(), f"Full-type file {file_path} was not created"

        # Verify BSD-3-Clause license was used
        license_content = (project_path / "LICENSE").read_text()
        assert "BSD 3-Clause" in license_content
        assert "Full Test" in license_content

    def test_complete_minimal_project(self, temp_project_dir):
        """Test creating a complete minimal project."""
        project_path = temp_project_dir / "minimal_project"
        project_path.mkdir()

        scaffolder = ProjectScaffolder(
            "minimal-project",
            project_path,
            project_type="minimal",
            license_type="ISC",
        )

        scaffolder.create_project_structure()
        scaffolder.create_source_files("Minimal Test", "minimal@test.com")
        scaffolder.create_test_files()
        scaffolder.create_example_script()
        scaffolder.create_gitignore()
        scaffolder.create_license("Minimal Test")
        scaffolder.create_example_notebook()  # Should be a no-op

        # Verify minimal files exist
        assert (project_path / "src" / "minimal_project" / "__init__.py").exists()
        assert (project_path / "tests" / "test_core.py").exists()
        assert (project_path / "LICENSE").exists()

        # Verify minimal doesn't have extras
        assert not (project_path / "notebooks").exists()
        assert not (project_path / "plots").exists()
        assert not (project_path / "_research").exists()
        assert not (project_path / "config").exists()
        assert not (project_path / "Makefile").exists()

        # Verify ISC license
        license_content = (project_path / "LICENSE").read_text()
        assert "ISC License" in license_content

    def test_generated_code_is_valid_python(self, temp_project_dir):
        """Test that all generated Python files have valid syntax."""
        project_path = temp_project_dir / "syntax_test_project"
        project_path.mkdir()

        scaffolder = ProjectScaffolder("syntax-test", project_path)
        scaffolder.create_project_structure()
        scaffolder.create_source_files("Syntax Test", "syntax@test.com")
        scaffolder.create_test_files()
        scaffolder.create_example_script()

        # Collect all Python files
        python_files = list(project_path.rglob("*.py"))
        assert len(python_files) > 0, "No Python files were generated"

        # Try to compile each file
        for py_file in python_files:
            content = py_file.read_text()
            try:
                compile(content, str(py_file), "exec")
            except SyntaxError as e:
                pytest.fail(f"Generated file {py_file} has invalid Python syntax: {e}")

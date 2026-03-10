"""
Integration tests for project scaffolding functionality.

Tests the ProjectScaffolder class with all three project types
(default, minimal, full) and license options.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from pywatson.core import LICENSE_TEMPLATES, PROJECT_TYPES, ProjectScaffolder


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

    def test_scaffolder_new_params_defaults(self, scaffolder):
        """Test that new params (python_version, linting_mode, type_checker) default correctly."""
        assert scaffolder.python_version == "3.12"
        assert scaffolder.linting_mode == "minimal"
        assert scaffolder.type_checker == "ty"

    def test_scaffolder_new_params_custom(self, temp_project_dir):
        """Test scaffolder with custom python_version, linting_mode, type_checker."""
        project_path = temp_project_dir / "custom_params"
        project_path.mkdir()
        s = ProjectScaffolder(
            "custom-project",
            project_path,
            python_version="3.11",
            linting_mode="strict",
            type_checker="mypy",
        )
        assert s.python_version == "3.11"
        assert s.linting_mode == "strict"
        assert s.type_checker == "mypy"

    def test_invalid_linting_mode_raises(self, temp_project_dir):
        """Test that an invalid linting mode raises ValueError."""
        project_path = temp_project_dir / "bad_linting"
        project_path.mkdir()
        with pytest.raises(ValueError, match="Unknown linting mode"):
            ProjectScaffolder("test-project", project_path, linting_mode="ultra")

    def test_invalid_type_checker_raises(self, temp_project_dir):
        """Test that an invalid type checker raises ValueError."""
        project_path = temp_project_dir / "bad_checker"
        project_path.mkdir()
        with pytest.raises(ValueError, match="Unknown type checker"):
            ProjectScaffolder("test-project", project_path, type_checker="pyright")

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
        """Test default project type creates PyWatson directories."""
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
        assert (src_dir / "pywatson_utils.py").exists()

        init_content = (src_dir / "__init__.py").read_text()
        assert "Test Author" in init_content
        assert "test@example.com" in init_content
        assert "from .core import" in init_content
        assert "from .pywatson_utils import" in init_content
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
        assert (scripts_dir / "pywatson_showcase.py").exists()

        generate_content = (scripts_dir / "generate_data.py").read_text()
        assert "def main():" in generate_content
        assert "create_example_data" in generate_content
        assert scaffolder.package_name in generate_content

        analyze_content = (scripts_dir / "analyze_data.py").read_text()
        assert "def main():" in analyze_content
        assert "load_data" in analyze_content
        assert scaffolder.package_name in analyze_content

        showcase_content = (scripts_dir / "pywatson_showcase.py").read_text()
        assert "produce_or_load" in showcase_content
        assert "savename" in showcase_content
        assert "run_heat_diffusion" in showcase_content

    # ------------------------------------------------------------------
    # .gitignore
    # ------------------------------------------------------------------

    def test_create_gitignore(self, scaffolder):
        """Test that .gitignore is created with PyWatson entries."""
        scaffolder.create_gitignore()

        gitignore_path = scaffolder.project_path / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert "__pycache__/" in content
        assert ".venv/" in content
        assert ".pytest_cache/" in content
        assert "data/" in content
        # PyWatson-specific entries
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
    # Copy pywatson_utils.py
    # ------------------------------------------------------------------

    def test_copy_utils_file(self, scaffolder):
        """Test that pywatson_utils.py is copied correctly."""
        scaffolder.create_project_structure()
        scaffolder._copy_utils_file()

        utils_path = (
            scaffolder.project_path / "src" / scaffolder.package_name / "pywatson_utils.py"
        )
        assert utils_path.exists()

        content = utils_path.read_text()
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
            "src/full_default/pywatson_utils.py",
            "tests/__init__.py",
            "tests/test_core.py",
            "scripts/generate_data.py",
            "scripts/analyze_data.py",
            "scripts/pywatson_showcase.py",
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


class TestDockerScaffolding:
    """Tests for Docker-related scaffolding functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for test projects."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def project_path(self, temp_project_dir):
        """Create a project directory with expected structure for Docker tests."""
        path = temp_project_dir / "docker_test_project"
        path.mkdir()
        return path

    def test_docker_flag_defaults_false(self, project_path):
        """Test that the docker flag defaults to False."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        assert scaffolder.docker is False

    def test_docker_flag_true(self, project_path):
        """Test that docker=True is stored on the scaffolder."""
        scaffolder = ProjectScaffolder("docker-test", project_path, docker=True)
        assert scaffolder.docker is True

    def test_create_docker_files_without_workflows_dir(self, project_path):
        """Test that core Docker files are created when .github/workflows/ is absent."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        assert (project_path / "Dockerfile").exists()
        assert (project_path / ".dockerignore").exists()
        assert (project_path / "docker-compose.yml").exists()
        assert (project_path / "README_DOCKER.md").exists()
        # docker-publish.yml must NOT be created when workflows dir is absent
        assert not (project_path / ".github" / "workflows" / "docker-publish.yml").exists()

    def test_create_docker_files_with_workflows_dir(self, project_path):
        """Test that docker-publish.yml is created when .github/workflows/ exists."""
        workflows_dir = project_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        scaffolder = ProjectScaffolder("docker-test", project_path, project_type="full")
        scaffolder.create_docker_files("Test Author", "test@example.com")

        assert (project_path / "Dockerfile").exists()
        assert (project_path / ".dockerignore").exists()
        assert (project_path / "docker-compose.yml").exists()
        assert (project_path / "README_DOCKER.md").exists()
        assert (workflows_dir / "docker-publish.yml").exists()

    def test_dockerfile_contains_python_version(self, project_path):
        """Test that the Dockerfile references the configured python_version."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "Dockerfile").read_text()
        assert scaffolder.python_version in content

    def test_dockerfile_contains_uv(self, project_path):
        """Test that the Dockerfile installs uv."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "Dockerfile").read_text()
        assert "uv" in content

    def test_docker_compose_contains_volume_mounts(self, project_path):
        """Test that docker-compose.yml mounts data/ and plots/ volumes."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "docker-compose.yml").read_text()
        assert "data" in content
        assert "plots" in content

    def test_readme_docker_contains_zenodo(self, project_path):
        """Test that README_DOCKER.md contains Zenodo instructions."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "README_DOCKER.md").read_text()
        assert "Zenodo" in content

    def test_readme_docker_contains_project_name(self, project_path):
        """Test that README_DOCKER.md references the project name."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "README_DOCKER.md").read_text()
        assert "docker-test" in content

    def test_docker_publish_yml_is_valid_yaml(self, project_path):
        """Test that the rendered docker-publish.yml is valid YAML."""
        import yaml

        workflows_dir = project_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        scaffolder = ProjectScaffolder("docker-test", project_path, project_type="full")
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (workflows_dir / "docker-publish.yml").read_text()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)
        assert "jobs" in parsed

    def test_dockerignore_excludes_data_and_plots(self, project_path):
        """Test that .dockerignore excludes data/ and plots/ directories."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / ".dockerignore").read_text()
        assert "data/" in content
        assert "plots/" in content

    def test_docker_files_created_via_full_project_pipeline(self, temp_project_dir):
        """Test Docker files are created correctly via create_full_extras + docker flag."""
        project_path = temp_project_dir / "full_docker_project"
        project_path.mkdir()

        scaffolder = ProjectScaffolder(
            "full-docker",
            project_path,
            project_type="full",
            docker=True,
        )
        scaffolder.create_project_structure()
        scaffolder.create_full_extras("Test Author", "test@example.com")
        scaffolder.create_docker_files("Test Author", "test@example.com")

        # Full project creates .github/workflows/, so docker-publish.yml should exist
        assert (project_path / "Dockerfile").exists()
        assert (project_path / ".dockerignore").exists()
        assert (project_path / "docker-compose.yml").exists()
        assert (project_path / "README_DOCKER.md").exists()
        assert (project_path / ".github" / "workflows" / "docker-publish.yml").exists()

    # ------------------------------------------------------------------
    # Dockerfile content
    # ------------------------------------------------------------------

    def test_dockerfile_entrypoint_is_analyze_data(self, project_path):
        """Test that the Dockerfile ENTRYPOINT runs analyze_data.py."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "Dockerfile").read_text()
        assert "analyze_data.py" in content
        assert "ENTRYPOINT" in content

    def test_dockerfile_copies_lock_file(self, project_path):
        """Test that the Dockerfile copies uv.lock so --frozen can succeed."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "Dockerfile").read_text()
        assert "uv.lock" in content
        assert "README.md" in content

    def test_dockerfile_uses_frozen_sync(self, project_path):
        """Test that the Dockerfile uses --frozen for exact reproducibility."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "Dockerfile").read_text()
        assert "--frozen" in content

    def test_dockerfile_creates_runtime_dirs(self, project_path):
        """Test that the Dockerfile creates data/ and plots/ at build time."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "Dockerfile").read_text()
        assert "data" in content
        assert "plots" in content

    # ------------------------------------------------------------------
    # docker-compose.yml content
    # ------------------------------------------------------------------

    def test_docker_compose_data_mount_is_readonly(self, project_path):
        """Test that the data volume mount is read-only (:ro) in docker-compose.yml."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "docker-compose.yml").read_text()
        assert ":ro" in content

    def test_docker_compose_has_shell_service(self, project_path):
        """Test that docker-compose.yml includes a shell service for debugging."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "docker-compose.yml").read_text()
        assert "shell:" in content

    def test_docker_compose_reproduce_service_present(self, project_path):
        """Test that docker-compose.yml has a reproduce service."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "docker-compose.yml").read_text()
        assert "reproduce:" in content

    def test_docker_compose_is_valid_yaml(self, project_path):
        """Test that docker-compose.yml renders as valid YAML."""
        import yaml

        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "docker-compose.yml").read_text()
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)
        assert "services" in parsed
        assert "reproduce" in parsed["services"]

    # ------------------------------------------------------------------
    # README_DOCKER.md content
    # ------------------------------------------------------------------

    def test_readme_docker_has_three_step_workflow(self, project_path):
        """Test that README_DOCKER.md contains pull / download / run steps."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "README_DOCKER.md").read_text()
        assert "docker pull" in content or "docker compose" in content
        assert "Zenodo" in content
        assert "reproduce" in content

    def test_readme_docker_references_ghcr(self, project_path):
        """Test that README_DOCKER.md tells readers where to pull the image from."""
        scaffolder = ProjectScaffolder("docker-test", project_path)
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (project_path / "README_DOCKER.md").read_text()
        assert "ghcr.io" in content

    # ------------------------------------------------------------------
    # docker-publish.yml content
    # ------------------------------------------------------------------

    def test_docker_publish_yml_has_smoke_test(self, temp_project_dir):
        """Test that the GH Actions workflow includes a smoke-test step."""
        project_path = temp_project_dir / "smoke_test_project"
        project_path.mkdir()
        workflows_dir = project_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        scaffolder = ProjectScaffolder("docker-test", project_path, project_type="full")
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (workflows_dir / "docker-publish.yml").read_text()
        assert "smoke" in content.lower() or "test" in content.lower()

    def test_docker_publish_yml_pushes_to_ghcr(self, temp_project_dir):
        """Test that the GH Actions workflow pushes to GHCR."""
        project_path = temp_project_dir / "ghcr_push_project"
        project_path.mkdir()
        workflows_dir = project_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        scaffolder = ProjectScaffolder("docker-test", project_path, project_type="full")
        scaffolder.create_docker_files("Test Author", "test@example.com")

        content = (workflows_dir / "docker-publish.yml").read_text()
        assert "ghcr.io" in content

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
            "justfile",
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
        justfile = (project_path / "justfile").read_text()
        assert "uv run pytest" in justfile
        assert "uv run ruff" in justfile

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
            "justfile",
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
        assert not (project_path / "justfile").exists()

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


# ===========================================================================
# Zenodo scaffolding
# ===========================================================================


class TestZenodoScaffolding:
    """Tests for Zenodo metadata scaffolding functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for Zenodo test projects."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def project_path(self, temp_project_dir):
        """Create a project directory for Zenodo tests."""
        path = temp_project_dir / "zenodo_test_project"
        path.mkdir()
        return path

    # ------------------------------------------------------------------
    # Scaffolder initialisation
    # ------------------------------------------------------------------

    def test_zenodo_flag_defaults_false(self, project_path):
        """Test that the zenodo flag defaults to False."""
        scaffolder = ProjectScaffolder("zenodo-test", project_path)
        assert scaffolder.zenodo is False

    def test_zenodo_flag_true(self, project_path):
        """Test that zenodo=True is stored on the scaffolder."""
        scaffolder = ProjectScaffolder("zenodo-test", project_path, zenodo=True)
        assert scaffolder.zenodo is True

    # ------------------------------------------------------------------
    # File creation
    # ------------------------------------------------------------------

    def test_create_zenodo_files_creates_zenodo_json(self, project_path):
        """Test that .zenodo.json is created in the project root."""
        scaffolder = ProjectScaffolder("zenodo-test", project_path)
        scaffolder.create_zenodo_files("Test Author", "test@example.com", "A test project")

        assert (project_path / ".zenodo.json").exists()

    def test_zenodo_json_is_valid_json(self, project_path):
        """Test that .zenodo.json renders as valid JSON."""
        import json

        scaffolder = ProjectScaffolder("zenodo-test", project_path)
        scaffolder.create_zenodo_files("Test Author", "test@example.com", "A test project")

        content = (project_path / ".zenodo.json").read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_zenodo_json_contains_required_fields(self, project_path):
        """Test that .zenodo.json contains title, creators, license, upload_type."""
        import json

        scaffolder = ProjectScaffolder(
            "my-analysis", project_path, license_type="MIT"
        )
        scaffolder.create_zenodo_files("Jane Doe", "jane@lab.org", "My analysis project")

        parsed = json.loads((project_path / ".zenodo.json").read_text())
        assert "title" in parsed
        assert "creators" in parsed
        assert "license" in parsed
        assert "upload_type" in parsed
        assert parsed["upload_type"] == "software"

    def test_zenodo_json_creator_name(self, project_path):
        """Test that the creator name in .zenodo.json matches the author."""
        import json

        scaffolder = ProjectScaffolder("zenodo-test", project_path)
        scaffolder.create_zenodo_files("Jane Doe", "jane@lab.org")

        parsed = json.loads((project_path / ".zenodo.json").read_text())
        assert parsed["creators"][0]["name"] == "Jane Doe"

    def test_zenodo_json_title_matches_project(self, project_path):
        """Test that the title in .zenodo.json matches the project name."""
        import json

        scaffolder = ProjectScaffolder("my-special-project", project_path)
        scaffolder.create_zenodo_files("Test Author", "test@example.com")

        parsed = json.loads((project_path / ".zenodo.json").read_text())
        assert parsed["title"] == "my-special-project"

    def test_zenodo_json_license_matches_scaffolder(self, project_path):
        """Test that the license field in .zenodo.json reflects the chosen license."""
        import json

        scaffolder = ProjectScaffolder(
            "zenodo-test", project_path, license_type="Apache-2.0"
        )
        scaffolder.create_zenodo_files("Test Author", "test@example.com")

        parsed = json.loads((project_path / ".zenodo.json").read_text())
        assert "apache" in parsed["license"].lower()

    def test_zenodo_json_access_right_open(self, project_path):
        """Test that the access_right is 'open' by default."""
        import json

        scaffolder = ProjectScaffolder("zenodo-test", project_path)
        scaffolder.create_zenodo_files("Test Author", "test@example.com")

        parsed = json.loads((project_path / ".zenodo.json").read_text())
        assert parsed.get("access_right") == "open"

    # ------------------------------------------------------------------
    # Integration: zenodo via full pipeline
    # ------------------------------------------------------------------

    def test_zenodo_flag_in_run_scaffolder(self, temp_project_dir):
        """Test that zenodo=True in the scaffolder param is reflected in .zenodo flag."""
        project_path = temp_project_dir / "zenodo_full"
        project_path.mkdir()

        scaffolder = ProjectScaffolder(
            "zenodo-full",
            project_path,
            zenodo=True,
        )
        assert scaffolder.zenodo is True
        scaffolder.create_zenodo_files("Full Author", "full@example.com", "Full desc")
        assert (project_path / ".zenodo.json").exists()


# ===========================================================================
# Docker in adopt command (CLI integration)
# ===========================================================================


class TestDockerAndZenodoInAdopt:
    """Tests for --docker and --zenodo flags in the adopt command."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary workspace for adopt tests."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    def _make_source(self, base: Path, name: str = "old_project") -> Path:
        """Create a minimal source project to adopt."""
        src = base / name
        src.mkdir(parents=True)
        (src / "main.py").write_text('"""Main script."""\nprint("hello")\n')
        return src

    def test_adopt_docker_flag_creates_dockerfile(self, temp_dir):
        """adopt --docker should create a Dockerfile in the new project."""
        from click.testing import CliRunner

        from pywatson.core import cli

        source = self._make_source(temp_dir)
        output = temp_dir / "adopted"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(source),
                "--project-name",
                "adopted",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
                "--docker",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (output / "Dockerfile").exists()
        assert (output / "docker-compose.yml").exists()
        assert (output / ".dockerignore").exists()

    def test_adopt_zenodo_flag_creates_zenodo_json(self, temp_dir):
        """adopt --zenodo should create a .zenodo.json in the new project."""
        from click.testing import CliRunner

        from pywatson.core import cli

        source = self._make_source(temp_dir)
        output = temp_dir / "adopted_zen"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(source),
                "--project-name",
                "adopted_zen",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
                "--zenodo",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (output / ".zenodo.json").exists()

    def test_adopt_both_docker_and_zenodo(self, temp_dir):
        """adopt --docker --zenodo should create both Dockerfile and .zenodo.json."""
        from click.testing import CliRunner

        from pywatson.core import cli

        source = self._make_source(temp_dir)
        output = temp_dir / "adopted_both"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(source),
                "--project-name",
                "adopted_both",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
                "--docker",
                "--zenodo",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (output / "Dockerfile").exists()
        assert (output / ".zenodo.json").exists()

    def test_adopt_no_docker_no_zenodo_by_default(self, temp_dir):
        """adopt without flags should not create Docker or Zenodo files."""
        from click.testing import CliRunner

        from pywatson.core import cli

        source = self._make_source(temp_dir)
        output = temp_dir / "adopted_plain"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(source),
                "--project-name",
                "adopted_plain",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
            ],
        )
        assert result.exit_code == 0, result.output
        assert not (output / "Dockerfile").exists()
        assert not (output / ".zenodo.json").exists()


class TestProjectScannerAndAdoptFixes:
    """Tests for ProjectScanner robustness and adopt path-preservation fixes."""

    @pytest.fixture
    def temp_dir(self):
        temp = Path(tempfile.mkdtemp())
        yield temp
        if temp.exists():
            shutil.rmtree(temp)

    def _make_messy_source(self, base: Path, name: str = "messy_project") -> Path:
        """Create a messy (unstructured, no pyproject.toml) project tree."""
        src = base / name
        src.mkdir(parents=True)
        # Scripts at root
        (src / "run_sim.py").write_text(
            'import argparse\nif __name__ == "__main__":\n    pass\n'
        )
        # Module package
        pkg = src / "mymodule"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "core.py").write_text("class Solver:\n    pass\n")
        # Data with nested parameter dirs (like scientific output)
        data_a = src / "Data" / "phi_0.5_N_10" / "run_001"
        data_a.mkdir(parents=True)
        (data_a / "results.npz").write_text("fake npz")
        data_b = src / "Data" / "phi_0.5_N_10" / "run_002"
        data_b.mkdir(parents=True)
        (data_b / "results.npz").write_text("fake npz")
        # IDE dirs that should be ignored
        (src / ".idea").mkdir()
        (src / ".idea" / "workspace.xml").write_text("<workspace/>")
        (src / ".vscode").mkdir()
        (src / ".vscode" / "settings.json").write_text("{}")
        (src / ".specstory").mkdir()
        (src / ".specstory" / "history.json").write_text("{}")
        # macOS junk
        (src / ".DS_Store").write_bytes(b"\x00" * 32)
        (src / "Data" / ".DS_Store").write_bytes(b"\x00" * 32)
        # Notebooks
        nb_dir = src / "notebooks"
        nb_dir.mkdir()
        (nb_dir / "analysis.ipynb").write_text('{"cells":[]}')
        # _research/ dir with Python files that look like scripts / source
        research = src / "_research"
        research.mkdir()
        (research / "scratch.py").write_text('if __name__ == "__main__":\n    pass\n')
        (research / "explore.py").write_text("import click\n")
        (research / "wip_analysis.py").write_text("def helper(): pass\n")
        # plots/ dir with PDF files (should be images, not docs)
        plots = src / "plots"
        plots.mkdir()
        (plots / "figure1.pdf").write_bytes(b"%PDF-1.4")
        (plots / "figure2.pdf").write_bytes(b"%PDF-1.4")
        # .github/ dir (should be ignored entirely)
        github = src / ".github"
        github.mkdir()
        (github / "copilot-instructions.md").write_text("# instructions\n")
        return src

    # ---------------------------------------------------------------------- #
    # Scanner: IDE dirs and .DS_Store ignored                                 #
    # ---------------------------------------------------------------------- #

    def test_scanner_ignores_idea_dir(self, temp_dir):
        """ProjectScanner must not include files from .idea/."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()
        all_files = [f for files in classified.values() for f in files]
        idea_files = [f for f in all_files if ".idea" in f.parts]
        assert idea_files == [], f"Expected no .idea files, got: {idea_files}"

    def test_scanner_ignores_vscode_dir(self, temp_dir):
        """ProjectScanner must not include files from .vscode/."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()
        all_files = [f for files in classified.values() for f in files]
        vscode_files = [f for f in all_files if ".vscode" in f.parts]
        assert vscode_files == [], f"Expected no .vscode files, got: {vscode_files}"

    def test_scanner_ignores_specstory_dir(self, temp_dir):
        """ProjectScanner must not include files from .specstory/."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()
        all_files = [f for files in classified.values() for f in files]
        specstory_files = [f for f in all_files if ".specstory" in f.parts]
        assert specstory_files == [], f"Expected no .specstory files, got: {specstory_files}"

    def test_scanner_ignores_ds_store(self, temp_dir):
        """ProjectScanner must not include .DS_Store files."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()
        all_files = [f for files in classified.values() for f in files]
        ds_files = [f for f in all_files if f.name == ".DS_Store"]
        assert ds_files == [], f"Expected no .DS_Store files, got: {ds_files}"

    # ---------------------------------------------------------------------- #
    # Adopt: path structure preserved (no flattening / no collisions)         #
    # ---------------------------------------------------------------------- #

    def test_adopt_preserves_data_subdirectory_structure(self, temp_dir):
        """adopt must preserve nested data paths so parameter dirs are not collapsed."""
        from click.testing import CliRunner

        from pywatson.core import cli

        src = self._make_messy_source(temp_dir)
        output = temp_dir / "adopted"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(src),
                "--project-name",
                "adopted",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
                "--copy",
            ],
        )
        assert result.exit_code == 0, result.output
        # Both run_001 and run_002 results.npz must be present with distinct paths
        npz_files = list(output.rglob("results.npz"))
        assert len(npz_files) == 2, (
            f"Expected 2 distinct results.npz files, got {len(npz_files)}: {npz_files}"
        )
        # Their paths must differ (not collapsed to same file)
        assert npz_files[0] != npz_files[1]

    def test_adopt_preserves_module_package_structure(self, temp_dir):
        """adopt must keep __init__.py and sibling source files in the same dir."""
        from click.testing import CliRunner

        from pywatson.core import cli

        src = self._make_messy_source(temp_dir)
        output = temp_dir / "adopted"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(src),
                "--project-name",
                "adopted",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
                "--copy",
            ],
        )
        assert result.exit_code == 0, result.output
        # core.py and __init__.py from mymodule/ must both be present
        source_files = list(output.rglob("core.py"))
        assert source_files, "core.py missing from adopted project"
        # __init__.py must be adjacent to core.py (same directory)
        core_parent = source_files[0].parent
        assert (core_parent / "__init__.py").exists(), (
            f"__init__.py not found next to core.py in {core_parent}"
        )

    def test_scanner_classifies_research_dir_as_other(self, temp_dir):
        """Python files inside _research/ must be classified as 'other', not 'scripts'."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()

        scripts_research = [
            f for f in classified.get("scripts", [])
            if "_research" in f.parts
        ]
        source_research = [
            f for f in classified.get("source", [])
            if "_research" in f.parts
        ]
        other_research = [
            f for f in classified.get("other", [])
            if "_research" in f.parts
        ]
        assert scripts_research == [], (
            f"_research/ files misclassified as scripts: {scripts_research}"
        )
        assert source_research == [], (
            f"_research/ files misclassified as source: {source_research}"
        )
        assert len(other_research) == 3, (
            f"Expected 3 _research/ files in 'other', got: {other_research}"
        )

    def test_scanner_classifies_plots_pdf_as_images(self, temp_dir):
        """PDF files inside plots/ must be classified as 'images', not 'docs'."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()

        docs_pdfs = [
            f for f in classified.get("docs", [])
            if f.suffix == ".pdf" and "plots" in f.parts
        ]
        image_pdfs = [
            f for f in classified.get("images", [])
            if f.suffix == ".pdf" and "plots" in f.parts
        ]
        assert docs_pdfs == [], f"plots/ PDFs misclassified as docs: {docs_pdfs}"
        assert len(image_pdfs) == 2, (
            f"Expected 2 plots/ PDFs in 'images', got: {image_pdfs}"
        )

    def test_scanner_ignores_github_dir(self, temp_dir):
        """ProjectScanner must not include files from .github/."""
        from pywatson.core import ProjectScanner

        src = self._make_messy_source(temp_dir)
        scanner = ProjectScanner(src)
        classified = scanner.scan()
        all_files = [f for files in classified.values() for f in files]
        github_files = [f for f in all_files if ".github" in f.parts]
        assert github_files == [], f"Expected no .github files, got: {github_files}"

    def test_adopt_does_not_include_ide_files(self, temp_dir):
        """adopt must not copy .idea / .vscode / .specstory files into target."""
        from click.testing import CliRunner

        from pywatson.core import cli

        src = self._make_messy_source(temp_dir)
        output = temp_dir / "adopted"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(src),
                "--project-name",
                "adopted",
                "--output-path",
                str(temp_dir),
                "--auto",
                "--no-uv",
                "--copy",
            ],
        )
        assert result.exit_code == 0, result.output
        idea_files = list(output.rglob(".idea/**/*"))
        vscode_files = list(output.rglob(".vscode/**/*"))
        assert not idea_files, f".idea files adopted: {idea_files}"
        assert not vscode_files, f".vscode files adopted: {vscode_files}"

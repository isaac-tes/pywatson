"""
Tests for template rendering functionality.

Verifies that all Jinja2 templates can be loaded, rendered, and produce
valid content. Python templates are additionally checked for valid syntax.
"""

from pathlib import Path

import pytest
from jinja2 import Environment, PackageLoader, select_autoescape


class TestTemplateRendering:
    """Test that all templates can be loaded and rendered."""

    @pytest.fixture
    def jinja_env(self):
        """Create a Jinja2 environment for testing."""
        return Environment(
            loader=PackageLoader("pywatson", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            keep_trailing_newline=True,
        )

    @pytest.fixture
    def template_context(self):
        """Standard context for template rendering."""
        return {
            "project_name": "test-project",
            "project_name_title": "Test Project",
            "package_name": "test_project",
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "python_version": "3.12",
            "python_version_nodot": "312",
            "linting_mode": "minimal",
            "type_checker": "ty",
            "project_type": "default",
            "license_type": "MIT",
        }

    # ------------------------------------------------------------------
    # Original templates
    # ------------------------------------------------------------------

    def test_init_template_renders(self, jinja_env, template_context):
        """Test that __init__.py template renders without errors."""
        template = jinja_env.get_template("__init__.py.jinja2")
        content = template.render(**template_context)

        assert "Test Project" in content
        assert "Test Author" in content
        assert "test@example.com" in content
        assert "from .core import" in content
        assert "from .pywatson_utils import" in content
        assert "hello_world" in content
        assert "load_selective" in content

    def test_core_template_renders(self, jinja_env, template_context):
        """Test that core.py template renders without errors."""
        template = jinja_env.get_template("core.py.jinja2")
        content = template.render(**template_context)

        assert "test-project" in content
        assert "test_project" in content
        assert "def hello_world()" in content
        assert "def create_example_data(" in content
        assert "def analyze_data(" in content

    def test_test_core_template_renders(self, jinja_env, template_context):
        """Test that test_core.py template renders without errors."""
        template = jinja_env.get_template("test_core.py.jinja2")
        content = template.render(**template_context)

        assert "test_project" in content
        assert "def test_hello_world()" in content
        assert "def test_create_example_data_random()" in content
        assert "def test_analyze_data_basic()" in content

    def test_generate_data_script_template_renders(self, jinja_env, template_context):
        """Test that generate_data.py script template renders without errors."""
        template = jinja_env.get_template("generate_data.py.jinja2")
        content = template.render(**template_context)

        assert "test_project" in content
        assert "from test_project import" in content
        assert "def main():" in content
        assert "create_example_data" in content

    def test_analyze_data_script_template_renders(self, jinja_env, template_context):
        """Test that analyze_data.py script template renders without errors."""
        template = jinja_env.get_template("analyze_data.py.jinja2")
        content = template.render(**template_context)

        assert "test_project" in content
        assert "from test_project import" in content
        assert "def main():" in content
        assert "load_data" in content
        assert "analyze_data" in content

    def test_gitignore_template_renders(self, jinja_env):
        """Test that gitignore template renders with PyWatson-style entries."""
        template = jinja_env.get_template("gitignore.jinja2")
        content = template.render()

        assert "__pycache__/" in content
        assert ".venv/" in content
        assert ".pytest_cache/" in content
        assert "data/" in content
        # PyWatson-specific entries
        assert "_research/tmp/" in content
        assert "papers/" in content or "papers/*.aux" in content

    # ------------------------------------------------------------------
    # New templates (C3)
    # ------------------------------------------------------------------

    def test_makefile_template_renders(self, jinja_env, template_context):
        """Test that Makefile template renders correctly."""
        template = jinja_env.get_template("Makefile.jinja2")
        content = template.render(**template_context)

        assert "uv run pytest" in content
        assert "uv run ruff" in content
        assert "test_project" in content
        assert "help:" in content
        assert "setup:" in content
        assert "clean:" in content

    def test_ruff_toml_template_renders(self, jinja_env, template_context):
        """Test that ruff.toml template renders correctly."""
        template = jinja_env.get_template("ruff.toml.jinja2")
        content = template.render(**template_context)

        assert "line-length" in content
        assert "test_project" in content
        assert "google" in content.lower()

    def test_pytest_ini_template_renders(self, jinja_env, template_context):
        """Test that pytest.ini template renders correctly."""
        template = jinja_env.get_template("pytest.ini.jinja2")
        content = template.render(**template_context)

        assert "[pytest]" in content
        assert "testpaths" in content
        assert "test_project" in content

    def test_ci_yml_template_renders(self, jinja_env, template_context):
        """Test that ci.yml template renders valid YAML-like content."""
        template = jinja_env.get_template("ci.yml.jinja2")
        content = template.render(**template_context)

        assert "name: CI" in content
        assert "uv run pytest" in content
        assert "uv run ruff" in content
        assert "test_project" in content
        assert "actions/checkout" in content

    def test_contributing_md_template_renders(self, jinja_env, template_context):
        """Test that CONTRIBUTING.md template renders correctly."""
        template = jinja_env.get_template("CONTRIBUTING.md.jinja2")
        content = template.render(**template_context)

        assert "Contributing" in content
        assert "test-project" in content
        assert "uv sync" in content
        assert "PyWatson" in content

    def test_changelog_md_template_renders(self, jinja_env, template_context):
        """Test that CHANGELOG.md template renders correctly."""
        template = jinja_env.get_template("CHANGELOG.md.jinja2")
        content = template.render(**template_context)

        assert "Changelog" in content
        assert "Test Project" in content
        assert "[Unreleased]" in content

    def test_pywatson_showcase_template_renders(self, jinja_env, template_context):
        """Test that pywatson_showcase.py template renders valid Python."""
        template = jinja_env.get_template("pywatson_showcase.py.jinja2")
        content = template.render(**template_context)

        assert "produce_or_load" in content
        assert "savename" in content
        assert "save_data" in content
        assert "tagsave" in content
        assert "load_data" in content
        assert "load_selective" in content
        assert "run_heat_diffusion" in content
        assert "def main()" in content
        assert "test_project" in content

        try:
            compile(content, "<pywatson_showcase.py.jinja2>", "exec")
        except SyntaxError as e:
            pytest.fail(f"pywatson_showcase.py.jinja2 renders invalid Python: {e}")

    # ------------------------------------------------------------------
    # License templates
    # ------------------------------------------------------------------

    def test_license_mit_template_renders(self, jinja_env):
        """Test that MIT license template renders correctly."""
        template = jinja_env.get_template("LICENSE_MIT.jinja2")
        content = template.render(author_name="Test Author", year="2025")

        assert "MIT License" in content
        assert "Test Author" in content
        assert "2025" in content

    def test_license_bsd3_template_renders(self, jinja_env):
        """Test that BSD-3-Clause license template renders correctly."""
        template = jinja_env.get_template("LICENSE_BSD3.jinja2")
        content = template.render(author_name="Test Author", year="2025")

        assert "BSD 3-Clause" in content
        assert "Test Author" in content

    def test_license_apache2_template_renders(self, jinja_env):
        """Test that Apache-2.0 license template renders correctly."""
        template = jinja_env.get_template("LICENSE_APACHE2.jinja2")
        content = template.render(author_name="Test Author", year="2025")

        assert "Apache License" in content
        assert "Test Author" in content

    def test_license_isc_template_renders(self, jinja_env):
        """Test that ISC license template renders correctly."""
        template = jinja_env.get_template("LICENSE_ISC.jinja2")
        content = template.render(author_name="Test Author", year="2025")

        assert "ISC License" in content
        assert "Test Author" in content

    # ------------------------------------------------------------------
    # README template with project_type and license_type
    # ------------------------------------------------------------------

    def test_readme_template_renders_default(self, jinja_env, template_context):
        """Test that README.md template renders for default project type."""
        context = template_context.copy()
        context["description"] = "A test project description"
        context["deps_list"] = "- **numpy**: numpy>=1.24.0\n- **matplotlib**: matplotlib>=3.7.0"
        context["project_type"] = "default"
        context["license_type"] = "MIT"

        template = jinja_env.get_template("README.md.jinja2")
        content = template.render(**context)

        assert "# Test Project" in content
        assert "A test project description" in content
        assert "test-project" in content
        assert "test_project" in content
        assert "sims/" in content
        assert "exp_raw/" in content
        assert "PyWatson" in content
        assert "MIT License" in content

    def test_readme_template_renders_minimal(self, jinja_env, template_context):
        """Test that README.md template renders for minimal project type."""
        context = template_context.copy()
        context["description"] = "Minimal project"
        context["deps_list"] = ""
        context["project_type"] = "minimal"
        context["license_type"] = "ISC"

        template = jinja_env.get_template("README.md.jinja2")
        content = template.render(**context)

        assert "# Test Project" in content
        # Minimal should not show data subdirectories
        assert "data/sims" not in content
        assert "ISC License" in content

    def test_readme_template_renders_full(self, jinja_env, template_context):
        """Test that README.md template renders for full project type."""
        context = template_context.copy()
        context["description"] = "Full project"
        context["deps_list"] = ""
        context["project_type"] = "full"
        context["license_type"] = "Apache-2.0"

        template = jinja_env.get_template("README.md.jinja2")
        content = template.render(**context)

        assert "# Test Project" in content
        assert "Makefile" in content
        assert "CONTRIBUTING" in content
        assert "CHANGELOG" in content
        assert "make" in content.lower()
        assert "Apache License" in content

    # ------------------------------------------------------------------
    # Template existence
    # ------------------------------------------------------------------

    def test_all_templates_exist(self):
        """Test that all expected template files exist."""
        template_dir = Path(__file__).parent.parent / "src" / "pywatson" / "templates"

        expected_templates = [
            # Original templates
            "__init__.py.jinja2",
            "core.py.jinja2",
            "test_core.py.jinja2",
            "generate_data.py.jinja2",
            "analyze_data.py.jinja2",
            "gitignore.jinja2",
            "README.md.jinja2",
            "notebook.ipynb.jinja2",
            # New templates (C3)
            "Makefile.jinja2",
            "ruff.toml.jinja2",
            "pytest.ini.jinja2",
            "ci.yml.jinja2",
            "CONTRIBUTING.md.jinja2",
            "CHANGELOG.md.jinja2",
            # Showcase script
            "pywatson_showcase.py.jinja2",
            # License templates
            "LICENSE_MIT.jinja2",
            "LICENSE_BSD3.jinja2",
            "LICENSE_APACHE2.jinja2",
            "LICENSE_ISC.jinja2",
        ]

        for template_file in expected_templates:
            template_path = template_dir / template_file
            assert template_path.exists(), f"Template {template_file} does not exist"

    # ------------------------------------------------------------------
    # Syntax validation
    # ------------------------------------------------------------------

    def test_rendered_templates_are_valid_python(self, jinja_env, template_context):
        """Test that rendered Python templates have valid syntax."""
        python_templates = [
            "__init__.py.jinja2",
            "core.py.jinja2",
            "test_core.py.jinja2",
            "generate_data.py.jinja2",
            "analyze_data.py.jinja2",
            "pywatson_showcase.py.jinja2",
        ]

        for template_name in python_templates:
            template = jinja_env.get_template(template_name)
            content = template.render(**template_context)

            try:
                compile(content, f"<{template_name}>", "exec")
            except SyntaxError as e:
                pytest.fail(f"Template {template_name} renders invalid Python: {e}")

    def test_notebook_template_renders(self, jinja_env, template_context):
        """Test that notebook.ipynb template renders valid JSON."""
        import json

        template = jinja_env.get_template("notebook.ipynb.jinja2")
        content = template.render(**template_context)

        try:
            notebook_data = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"Template notebook.ipynb.jinja2 renders invalid JSON: {e}")

        assert "cells" in notebook_data
        assert "metadata" in notebook_data
        assert "nbformat" in notebook_data
        assert notebook_data["nbformat"] == 4

        cells_source = "".join(str(cell.get("source", "")) for cell in notebook_data["cells"])
        assert "test_project" in cells_source
        assert "Test Project" in cells_source
        assert "PyWatson" in cells_source

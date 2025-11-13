"""
Integration tests for project scaffolding functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from pywatson.core import ProjectScaffolder


class TestProjectScaffolder:
    """Test the ProjectScaffolder class."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for test projects."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup after test
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def scaffolder(self, temp_project_dir):
        """Create a ProjectScaffolder instance for testing."""
        project_path = temp_project_dir / "test_project"
        project_path.mkdir()
        return ProjectScaffolder("test-project", project_path)
    
    def test_scaffolder_initialization(self, scaffolder):
        """Test that scaffolder initializes correctly."""
        assert scaffolder.project_name == "test-project"
        assert scaffolder.package_name == "test_project"
        assert scaffolder.jinja_env is not None
    
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
    
    def test_create_project_structure(self, scaffolder):
        """Test that project directory structure is created."""
        scaffolder.create_project_structure()
        
        expected_dirs = [
            "src",
            f"src/{scaffolder.package_name}",
            "scripts",
            "notebooks",
            "tests",
            "plots",
            "data",
            "docs",
        ]
        
        for dir_path in expected_dirs:
            full_path = scaffolder.project_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"
            assert full_path.is_dir(), f"{dir_path} is not a directory"
    
    def test_render_template(self, scaffolder):
        """Test the _render_template helper method."""
        context = {
            'project_name': 'test-project',
            'project_name_title': 'Test Project',
            'package_name': 'test_project',
            'author_name': 'Test Author',
            'author_email': 'test@example.com',
        }
        
        content = scaffolder._render_template('__init__.py.jinja2', **context)
        
        assert isinstance(content, str)
        assert len(content) > 0
        assert 'from .core import' in content
        assert 'Test Author' in content
    
    def test_create_source_files(self, scaffolder):
        """Test that source files are created correctly."""
        scaffolder.create_project_structure()
        scaffolder.create_source_files("Test Author", "test@example.com")
        
        # Check that files were created
        src_dir = scaffolder.project_path / "src" / scaffolder.package_name
        assert (src_dir / "__init__.py").exists()
        assert (src_dir / "core.py").exists()
        assert (src_dir / "drwatson.py").exists()
        
        # Verify content
        init_content = (src_dir / "__init__.py").read_text()
        assert "Test Author" in init_content
        assert "test@example.com" in init_content
        assert "from .core import" in init_content
        assert "from .drwatson import" in init_content
        
        core_content = (src_dir / "core.py").read_text()
        assert "def hello_world()" in core_content
        assert "def create_example_data(" in core_content
        assert "def analyze_data(" in core_content
    
    def test_create_test_files(self, scaffolder):
        """Test that test files are created correctly."""
        scaffolder.create_project_structure()
        scaffolder.create_test_files()
        
        # Check that files were created
        tests_dir = scaffolder.project_path / "tests"
        assert (tests_dir / "__init__.py").exists()
        assert (tests_dir / "test_core.py").exists()
        
        # Verify content
        test_content = (tests_dir / "test_core.py").read_text()
        assert "def test_hello_world()" in test_content
        assert "def test_create_example_data_random()" in test_content
        assert "def test_analyze_data_basic()" in test_content
        assert scaffolder.package_name in test_content
    
    def test_create_example_script(self, scaffolder):
        """Test that example scripts are created correctly."""
        scaffolder.create_project_structure()
        scaffolder.create_example_script()
        
        # Check that files were created
        scripts_dir = scaffolder.project_path / "scripts"
        assert (scripts_dir / "generate_data.py").exists()
        assert (scripts_dir / "analyze_data.py").exists()
        
        # Verify content
        generate_content = (scripts_dir / "generate_data.py").read_text()
        assert "def main():" in generate_content
        assert "create_example_data" in generate_content
        assert scaffolder.package_name in generate_content
        
        analyze_content = (scripts_dir / "analyze_data.py").read_text()
        assert "def main():" in analyze_content
        assert "load_data" in analyze_content
        assert scaffolder.package_name in analyze_content
    
    def test_create_gitignore(self, scaffolder):
        """Test that .gitignore is created correctly."""
        scaffolder.create_gitignore()
        
        gitignore_path = scaffolder.project_path / ".gitignore"
        assert gitignore_path.exists()
        
        content = gitignore_path.read_text()
        assert "__pycache__/" in content
        assert ".venv" in content
        assert ".pytest_cache/" in content
        assert "data/" in content
    
    def test_copy_drwatson_file(self, scaffolder):
        """Test that drwatson.py is copied correctly."""
        scaffolder.create_project_structure()
        scaffolder._copy_drwatson_file()
        
        drwatson_path = scaffolder.project_path / "src" / scaffolder.package_name / "drwatson.py"
        assert drwatson_path.exists()
        
        # Verify it's a valid Python file with expected functions
        content = drwatson_path.read_text()
        assert "def datadir(" in content
        assert "def save_data(" in content
        assert "def load_data(" in content


class TestFullProjectGeneration:
    """Integration tests for full project generation."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for test projects."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup after test
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    def test_complete_project_creation(self, temp_project_dir):
        """Test creating a complete project with all components."""
        project_path = temp_project_dir / "full_test_project"
        project_path.mkdir()
        
        scaffolder = ProjectScaffolder("full-test-project", project_path)
        
        # Create all components
        scaffolder.create_project_structure()
        scaffolder.create_source_files("Integration Test", "integration@test.com")
        scaffolder.create_test_files()
        scaffolder.create_example_script()
        scaffolder.create_gitignore()
        
        # Verify complete structure
        expected_files = [
            "src/full_test_project/__init__.py",
            "src/full_test_project/core.py",
            "src/full_test_project/drwatson.py",
            "tests/__init__.py",
            "tests/test_core.py",
            "scripts/generate_data.py",
            "scripts/analyze_data.py",
            ".gitignore",
        ]
        
        for file_path in expected_files:
            full_path = project_path / file_path
            assert full_path.exists(), f"File {file_path} was not created"
        
        expected_dirs = [
            "notebooks",
            "plots",
            "data",
            "docs",
        ]
        
        for dir_path in expected_dirs:
            full_path = project_path / dir_path
            assert full_path.exists(), f"Directory {dir_path} was not created"
    
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
                compile(content, str(py_file), 'exec')
            except SyntaxError as e:
                pytest.fail(f"Generated file {py_file} has invalid Python syntax: {e}")

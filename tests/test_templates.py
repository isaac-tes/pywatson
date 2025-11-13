"""
Tests for template rendering functionality.
"""

import pytest
from pathlib import Path
from jinja2 import Environment, PackageLoader, select_autoescape


class TestTemplateRendering:
    """Test that all templates can be loaded and rendered."""
    
    @pytest.fixture
    def jinja_env(self):
        """Create a Jinja2 environment for testing."""
        return Environment(
            loader=PackageLoader('pywatson', 'templates'),
            autoescape=select_autoescape(['html', 'xml']),
            keep_trailing_newline=True
        )
    
    @pytest.fixture
    def template_context(self):
        """Standard context for template rendering."""
        return {
            'project_name': 'test-project',
            'project_name_title': 'Test Project',
            'package_name': 'test_project',
            'author_name': 'Test Author',
            'author_email': 'test@example.com',
        }
    
    def test_init_template_renders(self, jinja_env, template_context):
        """Test that __init__.py template renders without errors."""
        template = jinja_env.get_template('__init__.py.jinja2')
        content = template.render(**template_context)
        
        assert 'Test Project' in content
        assert 'Test Author' in content
        assert 'test@example.com' in content
        assert 'from .core import' in content
        assert 'from .drwatson import' in content
        assert 'hello_world' in content
    
    def test_core_template_renders(self, jinja_env, template_context):
        """Test that core.py template renders without errors."""
        template = jinja_env.get_template('core.py.jinja2')
        content = template.render(**template_context)
        
        assert 'test-project' in content
        assert 'test_project' in content
        assert 'def hello_world()' in content
        assert 'def create_example_data(' in content
        assert 'def analyze_data(' in content
    
    def test_test_core_template_renders(self, jinja_env, template_context):
        """Test that test_core.py template renders without errors."""
        template = jinja_env.get_template('test_core.py.jinja2')
        content = template.render(**template_context)
        
        assert 'test_project' in content
        assert 'def test_hello_world()' in content
        assert 'def test_create_example_data_random()' in content
        assert 'def test_analyze_data_basic()' in content
    
    def test_generate_data_script_template_renders(self, jinja_env, template_context):
        """Test that generate_data.py script template renders without errors."""
        template = jinja_env.get_template('generate_data.py.jinja2')
        content = template.render(**template_context)
        
        assert 'test_project' in content
        assert 'from test_project import' in content
        assert 'def main():' in content
        assert 'create_example_data' in content
    
    def test_analyze_data_script_template_renders(self, jinja_env, template_context):
        """Test that analyze_data.py script template renders without errors."""
        template = jinja_env.get_template('analyze_data.py.jinja2')
        content = template.render(**template_context)
        
        assert 'test_project' in content
        assert 'from test_project import' in content
        assert 'def main():' in content
        assert 'load_data' in content
        assert 'analyze_data' in content
    
    def test_gitignore_template_renders(self, jinja_env):
        """Test that gitignore template renders without errors."""
        template = jinja_env.get_template('gitignore.jinja2')
        content = template.render()
        
        assert '__pycache__/' in content
        assert '.venv' in content
        assert '.pytest_cache/' in content
        assert 'data/' in content
    
    def test_all_templates_exist(self):
        """Test that all expected template files exist."""
        template_dir = Path(__file__).parent.parent / 'src' / 'pywatson' / 'templates'
        
        expected_templates = [
            '__init__.py.jinja2',
            'core.py.jinja2',
            'test_core.py.jinja2',
            'generate_data.py.jinja2',
            'analyze_data.py.jinja2',
            'gitignore.jinja2',
        ]
        
        for template_file in expected_templates:
            template_path = template_dir / template_file
            assert template_path.exists(), f"Template {template_file} does not exist"
    
    def test_rendered_templates_are_valid_python(self, jinja_env, template_context):
        """Test that rendered Python templates have valid syntax."""
        python_templates = [
            '__init__.py.jinja2',
            'core.py.jinja2',
            'test_core.py.jinja2',
            'generate_data.py.jinja2',
            'analyze_data.py.jinja2',
        ]
        
        for template_name in python_templates:
            template = jinja_env.get_template(template_name)
            content = template.render(**template_context)
            
            # Try to compile the rendered content as Python
            try:
                compile(content, f'<{template_name}>', 'exec')
            except SyntaxError as e:
                pytest.fail(f"Template {template_name} renders invalid Python: {e}")

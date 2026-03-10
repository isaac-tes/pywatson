"""
Tests for the `pywatson adopt` command and the ProjectScanner class.

Covers:
  - ProjectScanner classifying files from 4 distinct dummy-repo layouts
  - `pywatson adopt` CLI in --auto mode on each dummy repo
  - --dry-run produces no files
  - --project-name renames the output directory
  - Generated boilerplate is present (.gitignore, src/__init__.py, etc.)
  - Files pywatson regenerates (requirements.txt, setup.py, …) are skipped
"""

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from pywatson.core import (
    _REGENERATED_FILES,
    CATEGORY_DEFAULT_DIRS,
    CATEGORY_DESCRIPTIONS,
    ProjectScanner,
    cli,
)

# ===========================================================================
# Dummy project fixtures
# ===========================================================================


@pytest.fixture
def flat_project(tmp_path: Path) -> Path:
    """All files dumped in the project root — no sub-directories."""
    root = tmp_path / "flat_project"
    root.mkdir()

    # Scripts — have if __name__ == "__main__"
    (root / "main.py").write_text(
        "import numpy as np\n\n"
        "data = np.random.rand(100)\n\n"
        "if __name__ == '__main__':\n"
        "    print(data.mean())\n"
    )
    (root / "plot_results.py").write_text(
        "import matplotlib.pyplot as plt\n\n"
        "def plot(x, y):\n"
        "    plt.plot(x, y)\n\n"
        "if __name__ == '__main__':\n"
        "    plot([], [])\n"
    )

    # Source — has only def/class, no __main__
    (root / "utils.py").write_text(
        "def compute_mean(data: list) -> float:\n"
        "    return sum(data) / len(data)\n\n"
        "def normalize(data: list) -> list:\n"
        "    m = max(data)\n"
        "    return [x / m for x in data]\n"
    )

    # Test — name-based detection
    (root / "test_utils.py").write_text(
        "import pytest\n"
        "from flat_project.utils import compute_mean\n\n"
        "def test_compute_mean():\n"
        "    assert compute_mean([1, 2, 3]) == 2.0\n"
    )

    # Data
    (root / "data.csv").write_text("x,y\n1,2\n3,4\n")
    (root / "results.json").write_text('{"result": 42}\n')

    # Docs
    (root / "README.md").write_text("# My Analysis\nA flat research project.\n")

    # Config — should be skipped (in _REGENERATED_FILES)
    (root / "requirements.txt").write_text("numpy\nmatplotlib\n")

    return root


@pytest.fixture
def structured_wrong_project(tmp_path: Path) -> Path:
    """Project with plausible structure but wrong layout for pywatson."""
    root = tmp_path / "messy_sim"
    root.mkdir()

    # Script in root
    (root / "simulation.py").write_text(
        "import numpy as np\n\n"
        "def run_simulation(N: int = 1000, beta: float = 0.5) -> list:\n"
        "    return list(np.random.rand(N))\n\n"
        "if __name__ == '__main__':\n"
        "    run_simulation()\n"
    )

    # Analysis sub-directory (mix of source and scripts)
    analysis = root / "analysis"
    analysis.mkdir()
    (analysis / "analyze.py").write_text(
        "import numpy as np\n\n"
        "def analyze(data: list) -> float:\n"
        "    return float(np.mean(data))\n"
    )
    (analysis / "plot.py").write_text(
        "import matplotlib.pyplot as plt\n\n"
        "def plot_results(data: list) -> None:\n"
        "    plt.plot(data)\n\n"
        "if __name__ == '__main__':\n"
        "    plot_results([])\n"
    )

    # Data directory
    data_dir = root / "data"
    data_dir.mkdir()
    (data_dir / "params.json").write_text('{"N": 1000, "beta": 0.5}\n')
    (data_dir / "raw_data.csv").write_text("t,value\n0,1.0\n1,2.0\n")

    # Notebooks
    nb_dir = root / "notebooks"
    nb_dir.mkdir()
    nb_content = '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'
    (nb_dir / "exploration.ipynb").write_text(nb_content)

    # Tests
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_sim.py").write_text("def test_run_simulation():\n    assert True\n")

    # Shell script
    (root / "run_all.sh").write_text("#!/bin/bash\npython simulation.py\n")

    # Skipped config
    (root / "requirements.txt").write_text("numpy\nscipy\n")

    return root


@pytest.fixture
def notebook_heavy_project(tmp_path: Path) -> Path:
    """Project dominated by Jupyter notebooks with minimal Python files."""
    root = tmp_path / "notebook_project"
    root.mkdir()

    nb_content = (
        '{"cells": [], "metadata": {"kernelspec": '
        '{"display_name": "Python 3", "language": "python", "name": "python3"}}, '
        '"nbformat": 4, "nbformat_minor": 5}'
    )
    (root / "Experiment_1.ipynb").write_text(nb_content)
    (root / "Experiment_2.ipynb").write_text(nb_content)
    (root / "Experiment_3.ipynb").write_text(nb_content)

    # Source helper
    (root / "helper_functions.py").write_text(
        "import json\n\n"
        "def load_data(path: str) -> dict:\n"
        "    with open(path) as f:\n"
        "        return json.load(f)\n\n"
        "def process(data: dict) -> dict:\n"
        "    return data\n"
    )

    # Data
    (root / "data.json").write_text('{"values": [1, 2, 3]}\n')

    # Config — skip
    (root / "requirements.txt").write_text("jupyter\nnumpy\n")

    return root


@pytest.fixture
def nested_research_project(tmp_path: Path) -> Path:
    """Deep nested research code with src/, experiments/, and results/."""
    root = tmp_path / "research_code"
    root.mkdir()

    src = root / "src"
    src.mkdir()
    (src / "model.py").write_text(
        "class Model:\n"
        "    def __init__(self, hidden: int = 64) -> None:\n"
        "        self.hidden = hidden\n\n"
        "    def forward(self, x: list) -> list:\n"
        "        return x\n"
    )
    (src / "data_loader.py").write_text(
        "class DataLoader:\n"
        "    def __init__(self, path: str) -> None:\n"
        "        self.path = path\n\n"
        "    def load(self) -> list:\n"
        "        return []\n"
    )

    experiments = root / "experiments"
    experiments.mkdir()
    (experiments / "run_exp1.py").write_text(
        "from src.model import Model\n\n"
        "def main() -> None:\n"
        "    model = Model(hidden=128)\n"
        "    print('Running experiment 1')\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    (experiments / "run_exp2.py").write_text(
        "from src.model import Model\n\n"
        "def main() -> None:\n"
        "    model = Model(hidden=256)\n"
        "    print('Running experiment 2')\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    (experiments / "config.yaml").write_text("model:\n  hidden: 64\ntraining:\n  lr: 0.001\n")

    results = root / "results"
    results.mkdir()
    (results / "exp1_output.csv").write_text("epoch,loss\n1,0.5\n2,0.3\n")
    (results / "exp2_output.csv").write_text("epoch,loss\n1,0.4\n2,0.2\n")
    (results / "summary.json").write_text('{"best_model": "exp2"}\n')

    (root / "README.md").write_text("# Research Code\nDeep learning experiments.\n")

    return root


# ===========================================================================
# Helper: invoke adopt in --auto --no-uv mode
# ===========================================================================


def _adopt(
    runner: CliRunner,
    source: Path,
    out: Path,
    *extra_args: str,
) -> Result:
    """Invoke `pywatson adopt --auto --no-uv` on *source*, writing to *out/output/source.name*.

    The output is placed in ``out / "output"`` to guarantee the destination
    never coincides with the source (which lives directly under ``out``).
    """
    dest_parent = out / "output"
    dest_parent.mkdir(exist_ok=True)
    return runner.invoke(
        cli,
        [
            "adopt",
            str(source),
            "--output-path",
            str(dest_parent),
            "--auto",
            "--no-uv",
            "--author-name",
            "Test User",
            "--author-email",
            "test@example.com",
            *extra_args,
        ],
    )


# ===========================================================================
# ProjectScanner unit tests
# ===========================================================================


class TestProjectScanner:
    """Unit tests for ProjectScanner file classification."""

    # ------------------------------------------------------------------
    # flat_project
    # ------------------------------------------------------------------

    def test_flat_project_finds_test_files(self, flat_project: Path) -> None:
        """Name-pattern test detection: test_utils.py → tests."""
        classified = ProjectScanner(flat_project).scan()
        names = {f.name for f in classified["tests"]}
        assert "test_utils.py" in names

    def test_flat_project_finds_data_files(self, flat_project: Path) -> None:
        classified = ProjectScanner(flat_project).scan()
        data_names = {f.name for f in classified["data"]}
        assert "data.csv" in data_names
        assert "results.json" in data_names

    def test_flat_project_finds_source(self, flat_project: Path) -> None:
        """utils.py has only def/class → classified as source."""
        classified = ProjectScanner(flat_project).scan()
        source_names = {f.name for f in classified["source"]}
        assert "utils.py" in source_names

    def test_flat_project_finds_scripts(self, flat_project: Path) -> None:
        """main.py has if __name__ == '__main__' → script."""
        classified = ProjectScanner(flat_project).scan()
        script_names = {f.name for f in classified["scripts"]}
        assert "main.py" in script_names
        assert "plot_results.py" in script_names

    def test_flat_project_readme_goes_to_docs(self, flat_project: Path) -> None:
        classified = ProjectScanner(flat_project).scan()
        doc_names = {f.name for f in classified["docs"]}
        assert "README.md" in doc_names

    def test_flat_project_requirements_is_config(self, flat_project: Path) -> None:
        classified = ProjectScanner(flat_project).scan()
        config_names = {f.name for f in classified["config"]}
        assert "requirements.txt" in config_names

    # ------------------------------------------------------------------
    # structured_wrong_project
    # ------------------------------------------------------------------

    def test_structured_wrong_finds_notebooks(self, structured_wrong_project: Path) -> None:
        classified = ProjectScanner(structured_wrong_project).scan()
        nb_names = {f.name for f in classified["notebooks"]}
        assert "exploration.ipynb" in nb_names

    def test_structured_wrong_finds_tests(self, structured_wrong_project: Path) -> None:
        classified = ProjectScanner(structured_wrong_project).scan()
        names = {f.name for f in classified["tests"]}
        assert "test_sim.py" in names

    def test_structured_wrong_finds_data(self, structured_wrong_project: Path) -> None:
        classified = ProjectScanner(structured_wrong_project).scan()
        data_names = {f.name for f in classified["data"]}
        assert "raw_data.csv" in data_names
        assert "params.json" in data_names

    def test_structured_wrong_shell_script_is_script(self, structured_wrong_project: Path) -> None:
        classified = ProjectScanner(structured_wrong_project).scan()
        script_names = {f.name for f in classified["scripts"]}
        assert "run_all.sh" in script_names

    # ------------------------------------------------------------------
    # notebook_heavy_project
    # ------------------------------------------------------------------

    def test_notebook_heavy_finds_all_notebooks(self, notebook_heavy_project: Path) -> None:
        classified = ProjectScanner(notebook_heavy_project).scan()
        nb_names = {f.name for f in classified["notebooks"]}
        assert nb_names == {
            "Experiment_1.ipynb",
            "Experiment_2.ipynb",
            "Experiment_3.ipynb",
        }

    def test_notebook_heavy_helper_is_source(self, notebook_heavy_project: Path) -> None:
        classified = ProjectScanner(notebook_heavy_project).scan()
        source_names = {f.name for f in classified["source"]}
        assert "helper_functions.py" in source_names

    # ------------------------------------------------------------------
    # nested_research_project
    # ------------------------------------------------------------------

    def test_nested_source_files_classified_as_source(self, nested_research_project: Path) -> None:
        """model.py and data_loader.py have class definitions → source."""
        classified = ProjectScanner(nested_research_project).scan()
        source_names = {f.name for f in classified["source"]}
        assert "model.py" in source_names
        assert "data_loader.py" in source_names

    def test_nested_experiment_scripts_are_scripts(self, nested_research_project: Path) -> None:
        """run_exp*.py have if __name__ == '__main__' → scripts."""
        classified = ProjectScanner(nested_research_project).scan()
        script_names = {f.name for f in classified["scripts"]}
        assert "run_exp1.py" in script_names
        assert "run_exp2.py" in script_names

    def test_nested_csv_files_are_data(self, nested_research_project: Path) -> None:
        classified = ProjectScanner(nested_research_project).scan()
        data_names = {f.name for f in classified["data"]}
        assert "exp1_output.csv" in data_names
        assert "exp2_output.csv" in data_names
        assert "summary.json" in data_names

    def test_nested_yaml_config_is_config(self, nested_research_project: Path) -> None:
        classified = ProjectScanner(nested_research_project).scan()
        config_names = {f.name for f in classified["config"]}
        assert "config.yaml" in config_names

    def test_nested_readme_is_docs(self, nested_research_project: Path) -> None:
        classified = ProjectScanner(nested_research_project).scan()
        doc_names = {f.name for f in classified["docs"]}
        assert "README.md" in doc_names

    # ------------------------------------------------------------------
    # Ignore rules
    # ------------------------------------------------------------------

    def test_ignores_pycache(self, tmp_path: Path) -> None:
        root = tmp_path / "myproject"
        root.mkdir()
        pycache = root / "__pycache__"
        pycache.mkdir()
        (pycache / "utils.cpython-312.pyc").write_bytes(b"")
        (root / "utils.py").write_text("def foo(): pass\n")

        classified = ProjectScanner(root).scan()
        all_files = [f for files in classified.values() for f in files]
        assert not any(".pyc" in f.name for f in all_files)
        assert not any("__pycache__" in str(f) for f in all_files)

    def test_ignores_venv(self, tmp_path: Path) -> None:
        root = tmp_path / "myproject"
        root.mkdir()
        venv_bin = root / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "activate").write_text("# activate script\n")
        (root / "main.py").write_text("print('hello')\n")

        classified = ProjectScanner(root).scan()
        all_files = [f for files in classified.values() for f in files]
        assert not any(".venv" in str(f) for f in all_files)

    def test_ignores_dot_git(self, tmp_path: Path) -> None:
        root = tmp_path / "myproject"
        root.mkdir()
        git_dir = root / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("[core]\n    bare = false\n")
        (root / "script.py").write_text("x = 1\n")

        classified = ProjectScanner(root).scan()
        all_files = [f for files in classified.values() for f in files]
        assert not any(".git" in str(f) for f in all_files)

    # ------------------------------------------------------------------
    # Python classification heuristics
    # ------------------------------------------------------------------

    def test_classify_test_by_name_prefix(self, tmp_path: Path) -> None:
        f = tmp_path / "test_something.py"
        f.write_text("x = 1\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "tests"

    def test_classify_test_by_name_suffix(self, tmp_path: Path) -> None:
        f = tmp_path / "something_test.py"
        f.write_text("x = 1\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "tests"

    def test_classify_test_by_pytest_import(self, tmp_path: Path) -> None:
        f = tmp_path / "check.py"
        f.write_text("import pytest\n\ndef test_foo():\n    pass\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "tests"

    def test_classify_test_by_def_test(self, tmp_path: Path) -> None:
        f = tmp_path / "verification.py"
        f.write_text("def test_something():\n    assert True\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "tests"

    def test_classify_script_by_main_guard(self, tmp_path: Path) -> None:
        f = tmp_path / "runner.py"
        f.write_text("if __name__ == '__main__':\n    print('running')\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "scripts"

    def test_classify_script_by_click_import(self, tmp_path: Path) -> None:
        f = tmp_path / "cli.py"
        f.write_text("import click\n\n@click.command()\ndef main():\n    pass\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "scripts"

    def test_classify_source_by_class_def(self, tmp_path: Path) -> None:
        f = tmp_path / "model.py"
        f.write_text("class MyModel:\n    def __init__(self) -> None:\n        pass\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "source"

    def test_classify_source_by_def_only(self, tmp_path: Path) -> None:
        f = tmp_path / "helpers.py"
        f.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
        assert ProjectScanner(tmp_path)._classify_python_file(f) == "source"

    # ------------------------------------------------------------------
    # print_summary smoke test
    # ------------------------------------------------------------------

    def test_print_summary_does_not_raise(self, flat_project: Path) -> None:
        scanner = ProjectScanner(flat_project)
        classified = scanner.scan()
        # Should not raise; Rich output goes to stdout
        scanner.print_summary(classified)

    # ------------------------------------------------------------------
    # CATEGORY_DESCRIPTIONS covers all categories
    # ------------------------------------------------------------------

    def test_all_default_dir_categories_have_descriptions(self) -> None:
        for cat in CATEGORY_DEFAULT_DIRS:
            assert cat in CATEGORY_DESCRIPTIONS, (
                f"Category '{cat}' missing from CATEGORY_DESCRIPTIONS"
            )


# ===========================================================================
# adopt CLI integration tests
# ===========================================================================


def _dest(tmp_path: Path, project_name: str) -> Path:
    """Return the expected destination path for _adopt(runner, source, tmp_path).

    The _adopt helper writes to ``tmp_path / "output" / project_name``.
    """
    return tmp_path / "output" / project_name


class TestAdoptCommand:
    """Integration tests for `pywatson adopt` CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    # ------------------------------------------------------------------
    # flat_project
    # ------------------------------------------------------------------

    def test_flat_project_exit_zero(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        result = _adopt(runner, flat_project, tmp_path)
        assert result.exit_code == 0, result.output

    def test_flat_project_creates_dest_dir(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        assert dest.is_dir()

    def test_flat_project_test_file_moved_to_tests(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        assert (_dest(tmp_path, "flat_project") / "tests" / "test_utils.py").exists()

    def test_flat_project_data_files_moved_to_data(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        assert (dest / "data" / "data.csv").exists()
        assert (dest / "data" / "results.json").exists()

    def test_flat_project_source_moved_to_src(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        assert (dest / "src" / "flat_project" / "utils.py").exists()

    def test_flat_project_scripts_moved_to_scripts(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        assert (dest / "scripts" / "main.py").exists()
        assert (dest / "scripts" / "plot_results.py").exists()

    def test_flat_project_requirements_is_skipped(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        """requirements.txt is in _REGENERATED_FILES — must not be copied."""
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        assert not (dest / "requirements.txt").exists()
        # It must not appear anywhere in the new project
        all_files = {f.name for f in dest.rglob("*") if f.is_file()}
        assert "requirements.txt" not in all_files

    # ------------------------------------------------------------------
    # structured_wrong_project
    # ------------------------------------------------------------------

    def test_structured_wrong_exit_zero(
        self, runner: CliRunner, structured_wrong_project: Path, tmp_path: Path
    ) -> None:
        result = _adopt(runner, structured_wrong_project, tmp_path)
        assert result.exit_code == 0, result.output

    def test_structured_wrong_notebook_copied(
        self, runner: CliRunner, structured_wrong_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, structured_wrong_project, tmp_path)
        dest = _dest(tmp_path, "messy_sim")
        assert (dest / "notebooks" / "exploration.ipynb").exists()

    def test_structured_wrong_test_copied(
        self, runner: CliRunner, structured_wrong_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, structured_wrong_project, tmp_path)
        dest = _dest(tmp_path, "messy_sim")
        assert (dest / "tests" / "test_sim.py").exists()

    def test_structured_wrong_data_copied(
        self, runner: CliRunner, structured_wrong_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, structured_wrong_project, tmp_path)
        dest = _dest(tmp_path, "messy_sim")
        assert (dest / "data" / "raw_data.csv").exists()
        assert (dest / "data" / "params.json").exists()

    def test_structured_wrong_shell_script_in_scripts(
        self, runner: CliRunner, structured_wrong_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, structured_wrong_project, tmp_path)
        dest = _dest(tmp_path, "messy_sim")
        assert (dest / "scripts" / "run_all.sh").exists()

    # ------------------------------------------------------------------
    # notebook_heavy_project
    # ------------------------------------------------------------------

    def test_notebook_heavy_exit_zero(
        self, runner: CliRunner, notebook_heavy_project: Path, tmp_path: Path
    ) -> None:
        result = _adopt(runner, notebook_heavy_project, tmp_path)
        assert result.exit_code == 0, result.output

    def test_notebook_heavy_all_notebooks_copied(
        self, runner: CliRunner, notebook_heavy_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, notebook_heavy_project, tmp_path)
        dest = _dest(tmp_path, "notebook_project")
        for name in ("Experiment_1.ipynb", "Experiment_2.ipynb", "Experiment_3.ipynb"):
            assert (dest / "notebooks" / name).exists(), f"Missing {name}"

    def test_notebook_heavy_helper_in_src(
        self, runner: CliRunner, notebook_heavy_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, notebook_heavy_project, tmp_path)
        dest = _dest(tmp_path, "notebook_project")
        assert (dest / "src" / "notebook_project" / "helper_functions.py").exists()

    def test_notebook_heavy_data_json_in_data(
        self, runner: CliRunner, notebook_heavy_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, notebook_heavy_project, tmp_path)
        dest = _dest(tmp_path, "notebook_project")
        assert (dest / "data" / "data.json").exists()

    # ------------------------------------------------------------------
    # nested_research_project
    # ------------------------------------------------------------------

    def test_nested_exit_zero(
        self, runner: CliRunner, nested_research_project: Path, tmp_path: Path
    ) -> None:
        result = _adopt(runner, nested_research_project, tmp_path)
        assert result.exit_code == 0, result.output

    def test_nested_source_files_in_src(
        self, runner: CliRunner, nested_research_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, nested_research_project, tmp_path)
        dest = _dest(tmp_path, "research_code")
        assert (dest / "src" / "research_code" / "model.py").exists()
        assert (dest / "src" / "research_code" / "data_loader.py").exists()

    def test_nested_experiment_scripts_in_scripts(
        self, runner: CliRunner, nested_research_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, nested_research_project, tmp_path)
        dest = _dest(tmp_path, "research_code")
        assert (dest / "scripts" / "run_exp1.py").exists()
        assert (dest / "scripts" / "run_exp2.py").exists()

    def test_nested_csv_results_in_data(
        self, runner: CliRunner, nested_research_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, nested_research_project, tmp_path)
        dest = _dest(tmp_path, "research_code")
        assert (dest / "data" / "exp1_output.csv").exists()
        assert (dest / "data" / "exp2_output.csv").exists()

    def test_nested_readme_in_docs(
        self, runner: CliRunner, nested_research_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, nested_research_project, tmp_path)
        dest = _dest(tmp_path, "research_code")
        assert (dest / "docs" / "README.md").exists()

    # ------------------------------------------------------------------
    # Boilerplate generation
    # ------------------------------------------------------------------

    def test_adopt_generates_gitignore(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        assert (_dest(tmp_path, "flat_project") / ".gitignore").exists()

    def test_adopt_generates_src_package_init(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        assert (_dest(tmp_path, "flat_project") / "src" / "flat_project" / "__init__.py").exists()

    def test_adopt_generates_tests_init(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        assert (_dest(tmp_path, "flat_project") / "tests" / "__init__.py").exists()

    def test_adopt_generates_license(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        assert (_dest(tmp_path, "flat_project") / "LICENSE").exists()

    def test_adopt_generates_pywatson_utils(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        """pywatson_utils.py should be created in src/<pkg>/ even for adopted projects."""
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        assert (dest / "src" / "flat_project" / "pywatson_utils.py").exists()

    def test_adopt_generates_standard_dirs(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path)
        dest = _dest(tmp_path, "flat_project")
        for d in ("src", "tests", "scripts", "data", "docs", "notebooks", "plots"):
            assert (dest / d).is_dir(), f"{d}/ missing"

    # ------------------------------------------------------------------
    # --dry-run
    # ------------------------------------------------------------------

    def test_dry_run_reports_files(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        result = _adopt(runner, flat_project, tmp_path, "--dry-run")
        assert result.exit_code == 0, result.output
        assert "dry run" in result.output.lower() or "would be" in result.output.lower()

    def test_dry_run_creates_no_directory(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, flat_project, tmp_path, "--dry-run")
        # Nothing should be created under tmp_path
        assert not _dest(tmp_path, "flat_project").exists()

    def test_dry_run_nested_creates_nothing(
        self, runner: CliRunner, nested_research_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, nested_research_project, tmp_path, "--dry-run")
        assert not _dest(tmp_path, "research_code").exists()

    # ------------------------------------------------------------------
    # --project-name
    # ------------------------------------------------------------------

    def test_custom_project_name_creates_correct_dir(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        result = runner.invoke(
            cli,
            [
                "adopt",
                str(flat_project),
                "--output-path",
                str(tmp_path),
                "--project-name",
                "clean_analysis",
                "--auto",
                "--no-uv",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "clean_analysis").is_dir()

    def test_custom_project_name_uses_as_package_name(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        runner.invoke(
            cli,
            [
                "adopt",
                str(flat_project),
                "--output-path",
                str(tmp_path),
                "--project-name",
                "clean_analysis",
                "--auto",
                "--no-uv",
            ],
        )
        dest = tmp_path / "clean_analysis"
        assert (dest / "src" / "clean_analysis").is_dir()

    # ------------------------------------------------------------------
    # Source-file preservation integrity
    # ------------------------------------------------------------------

    def test_adopted_file_content_preserved(
        self, runner: CliRunner, flat_project: Path, tmp_path: Path
    ) -> None:
        """The content of copied files must be identical to the originals."""
        _adopt(runner, flat_project, tmp_path)
        src_csv = flat_project / "data.csv"
        dst_csv = _dest(tmp_path, "flat_project") / "data" / "data.csv"
        assert dst_csv.read_text() == src_csv.read_text()

    def test_adopted_notebook_content_preserved(
        self, runner: CliRunner, notebook_heavy_project: Path, tmp_path: Path
    ) -> None:
        _adopt(runner, notebook_heavy_project, tmp_path)
        src_nb = notebook_heavy_project / "Experiment_1.ipynb"
        dst_nb = _dest(tmp_path, "notebook_project") / "notebooks" / "Experiment_1.ipynb"
        assert dst_nb.read_text() == src_nb.read_text()

    # ------------------------------------------------------------------
    # _REGENERATED_FILES constant sanity checks
    # ------------------------------------------------------------------

    def test_regenerated_files_includes_requirements(self) -> None:
        assert "requirements.txt" in _REGENERATED_FILES

    def test_regenerated_files_includes_setup_py(self) -> None:
        assert "setup.py" in _REGENERATED_FILES

    def test_regenerated_files_includes_pyproject_toml(self) -> None:
        assert "pyproject.toml" in _REGENERATED_FILES

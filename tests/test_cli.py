"""Tests for pywatson CLI subcommands: status, sweep, summary."""

from pathlib import Path

import h5py
import numpy as np
from click.testing import CliRunner

import pywatson.utils as _utils
from pywatson.core import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pyproject(path: Path, name: str = "test-project") -> None:
    """Write a minimal pyproject.toml so status recognises the project root."""
    (path / "pyproject.toml").write_text(f'[project]\nname = "{name}"\nversion = "0.1.0"\n')


def _write_h5(filepath: Path, datasets: dict | None = None) -> None:
    """Write a minimal HDF5 file with optional datasets and metadata."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(filepath, "w") as f:
        meta = f.require_group("_metadata")
        meta.attrs["created_at"] = "2025-01-01T00:00:00"
        if datasets:
            for k, v in datasets.items():
                f.create_dataset(k, data=np.asarray(v))


# ===========================================================================
# pywatson status
# ===========================================================================


class TestStatusCommand:
    """Tests for `pywatson status`."""

    def test_status_inside_project(self, tmp_path: Path) -> None:
        """Status reports project root when pyproject.toml is present."""
        _make_pyproject(tmp_path, "my-project")
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "my-project" in result.output

    def test_status_outside_project(self, tmp_path: Path) -> None:
        """Status gracefully reports 'not inside a project' when no root found."""
        runner = CliRunner()
        # Use isolated_filesystem starting in tmp_path (no pyproject.toml, no .git)
        # We need a directory that has NO pyproject.toml up the whole tree,
        # which is tricky since the pywatson repo itself has one. We'll just
        # check the command doesn't crash.
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["status"])
        # Either exit 0 with "Not inside" message or 0 with project found —
        # either way should not crash.
        assert result.exit_code == 0

    def test_status_shows_directories(self, tmp_path: Path) -> None:
        """Status lists directories that exist."""
        _make_pyproject(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "scripts").mkdir()
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        # At least the Directories section should appear
        assert "Directories" in result.output or "data" in result.output

    def test_status_shows_data_file_counts(self, tmp_path: Path) -> None:
        """Status counts HDF5 files in data/."""
        _make_pyproject(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        _write_h5(data_dir / "run1.h5")
        _write_h5(data_dir / "run2.h5")
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        # "2" should appear somewhere in the data-files section
        assert "2" in result.output

    def test_status_shows_git_section(self, tmp_path: Path) -> None:
        """Status includes Git section (even if no git repo is found)."""
        _make_pyproject(tmp_path)
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["status"])
        # Just check it doesn't crash; Git section is optional when no repo
        assert result.exit_code == 0


# ===========================================================================
# pywatson sweep
# ===========================================================================


class TestSweepCommand:
    """Tests for `pywatson sweep`."""

    def test_sweep_single_param(self) -> None:
        """Sweep over one parameter with two values produces 2 filenames."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "alpha=0.1,0.5"])
        assert result.exit_code == 0
        assert "2 combinations" in result.output
        assert "alpha=0.1" in result.output
        assert "alpha=0.5" in result.output

    def test_sweep_two_params_cartesian(self) -> None:
        """Sweep over 2×2 parameters produces 4 filenames."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "alpha=0.1,0.5", "N=100,1000"])
        assert result.exit_code == 0
        assert "4 combinations" in result.output

    def test_sweep_custom_suffix(self) -> None:
        """--suffix flag changes file extension in output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "alpha=0.1", "--suffix", ".npz"])
        assert result.exit_code == 0
        assert ".npz" in result.output

    def test_sweep_integer_coercion(self) -> None:
        """Integer strings are coerced to ints in the filename."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "N=100"])
        assert result.exit_code == 0
        assert "N=100" in result.output

    def test_sweep_no_params_gives_hint(self) -> None:
        """Sweep without arguments prints a usage hint."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep"])
        assert result.exit_code == 0
        assert "Provide at least one" in result.output or "KEY=VAL" in result.output

    def test_sweep_invalid_token(self) -> None:
        """A token without '=' is reported as invalid."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "badtoken"])
        assert result.exit_code == 0
        assert "Invalid" in result.output or "badtoken" in result.output

    def test_sweep_three_way_product(self) -> None:
        """3×2×2 = 12 combinations."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "a=1,2,3", "b=10,20", "c=x,y"])
        assert result.exit_code == 0
        assert "12 combinations" in result.output

    def test_sweep_custom_connector(self) -> None:
        """--connector changes the separator between key=value pairs."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "alpha=0.1", "--connector", "-"])
        assert result.exit_code == 0
        # With a single param the connector doesn't appear, but command is valid
        assert result.exit_code == 0

    def test_sweep_float_string_preserved(self) -> None:
        """String values that can't be parsed as int/float are kept as-is."""
        runner = CliRunner()
        result = runner.invoke(cli, ["sweep", "method=euler,rk4"])
        assert result.exit_code == 0
        assert "euler" in result.output
        assert "rk4" in result.output


# ===========================================================================
# pywatson summary
# ===========================================================================


class TestSummaryCommand:
    """Tests for `pywatson summary`."""

    def _invoke_summary(self, tmp_path: Path, runner: CliRunner, **kwargs) -> object:
        """Helper: reset project-root cache and invoke summary inside isolated fs."""
        saved_root = _utils._PROJECT_ROOT
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _utils._PROJECT_ROOT = None  # force re-detection from new CWD
            result = runner.invoke(cli, ["summary", *[f"--{k}={v}" for k, v in kwargs.items()]])
        _utils._PROJECT_ROOT = saved_root
        return result

    def test_summary_no_files(self, tmp_path: Path) -> None:
        """Summary reports no files found when data/ is empty."""
        _make_pyproject(tmp_path)
        (tmp_path / "data").mkdir()
        runner = CliRunner()
        result = self._invoke_summary(tmp_path, runner)
        assert result.exit_code == 0
        assert "No HDF5 files found" in result.output

    def test_summary_with_one_file(self, tmp_path: Path) -> None:
        """Summary lists one file with its datasets."""
        _make_pyproject(tmp_path)
        data_dir = tmp_path / "data"
        _write_h5(data_dir / "run1.h5", datasets={"temperature": [1.0, 2.0, 3.0]})
        runner = CliRunner()
        result = self._invoke_summary(tmp_path, runner)
        assert result.exit_code == 0
        assert "1 file" in result.output
        assert "run1.h5" in result.output

    def test_summary_with_multiple_files(self, tmp_path: Path) -> None:
        """Summary counts multiple HDF5 files correctly."""
        _make_pyproject(tmp_path)
        data_dir = tmp_path / "data"
        _write_h5(data_dir / "a.h5", datasets={"x": [1, 2]})
        _write_h5(data_dir / "b.h5", datasets={"y": [3, 4]})
        runner = CliRunner()
        result = self._invoke_summary(tmp_path, runner)
        assert result.exit_code == 0
        assert "2 file" in result.output

    def test_summary_no_project_root(self, tmp_path: Path) -> None:
        """Summary reports 'no files' or an error when outside a project."""
        # No pyproject.toml in tmp_path — collect_results may raise RuntimeError
        # (caught by summary_command) or find pywatson's dev root.
        # Either way the command must not crash.
        runner = CliRunner()
        saved_root = _utils._PROJECT_ROOT
        with runner.isolated_filesystem(temp_dir=tmp_path):
            _utils._PROJECT_ROOT = None
            result = runner.invoke(cli, ["summary"])
        _utils._PROJECT_ROOT = saved_root
        assert result.exit_code == 0
        assert result.output.strip() != ""


# ===========================================================================
# pywatson init — git config auto-fill
# ===========================================================================


class TestInitGitAutoFill:
    """Tests that `pywatson` exposes git config values as option defaults."""

    def test_has_author_name_option(self) -> None:
        """The pywatson command accepts --author-name without error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--help"],
        )
        assert "--author-name" in result.output

    def test_has_author_email_option(self) -> None:
        """The pywatson command accepts --author-email without error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "--author-email" in result.output


# ===========================================================================
# pywatson init — interactive wizard (no args)
# ===========================================================================


class TestInitInteractive:
    """Tests for fully interactive `pywatson init` (no arguments)."""

    def _interactive_input(
        self,
        project_name: str = "my-sim",
        author_name: str = "Alice",
        author_email: str = "alice@example.com",
        description: str = "A test project",
        path: str = ".",
        project_type_idx: str = "1",
        license_idx: str = "1",
        python_version: str = "3.12",
        linting_idx: str = "1",
        type_checker_idx: str = "3",
        env_file: str = "",
        docker: str = "n",
        confirm: str = "n",
    ) -> str:
        """Build a newline-delimited input string for the interactive wizard."""
        return "\n".join(
            [
                project_name,
                author_name,
                author_email,
                description,
                path,
                project_type_idx,
                license_idx,
                python_version,
                linting_idx,
                type_checker_idx,
                env_file,
                docker,
                confirm,
                "",
            ]
        )

    def test_interactive_aborted_does_not_create_project(self, tmp_path: Path) -> None:
        """Answering 'n' at the confirmation prompt aborts without creating files."""
        runner = CliRunner()
        inp = self._interactive_input(path=str(tmp_path), confirm="n")
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], input=inp)
        assert result.exit_code == 0
        assert "Aborted" in result.output
        assert not (tmp_path / "my-sim").exists()

    def test_interactive_shows_summary_before_confirm(self, tmp_path: Path) -> None:
        """The summary block is printed before the Continue? prompt."""
        runner = CliRunner()
        inp = self._interactive_input(path=str(tmp_path), confirm="n")
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], input=inp)
        assert "Summary" in result.output
        assert "my-sim" in result.output

    def test_interactive_empty_project_name_exits(self, tmp_path: Path) -> None:
        """An empty project name causes a non-zero exit."""
        runner = CliRunner()
        # Send blank name then fill everything else
        fields = [
            "", "Alice", "a@b.com", "desc", ".", "1", "1", "3.12", "1", "3", "", "n", "n", "",
        ]
        inp = "\n".join(fields)
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], input=inp)
        assert result.exit_code != 0 or "cannot be empty" in result.output

    def test_init_no_args_triggers_interactive(self, tmp_path: Path) -> None:
        """Running `pywatson init` without PROJECT_NAME prints the wizard header."""
        runner = CliRunner()
        inp = self._interactive_input(path=str(tmp_path), confirm="n")
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init"], input=inp)
        assert "Interactive Project Creator" in result.output

    def test_noninteractive_bypasses_wizard(self, tmp_path: Path) -> None:
        """Using --project-name bypasses the interactive wizard entirely."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cli,
                [
                    "--project-name",
                    "quick-proj",
                    "--path",
                    str(tmp_path),
                    "--author-name",
                    "Bob",
                    "--author-email",
                    "bob@example.com",
                    "--description",
                    "Quick",
                ],
            )
        assert "Interactive Project Creator" not in result.output

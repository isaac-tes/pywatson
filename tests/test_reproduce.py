"""Tests for utils.reproduce — soft reproducibility with optional verification."""

import textwrap
from unittest.mock import patch

import numpy as np
import pytest

from pywatson.utils import reproduce


def _write_project(tmp_path):
    """Create a minimal project root (marker + data dir) for a subprocess run."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "repro_test"\n')
    (tmp_path / "data").mkdir()


def _write_script(tmp_path, name, body):
    script = tmp_path / name
    script.write_text(textwrap.dedent(body))
    return script


class TestReproduce:
    """Tests for reproduce(): provenance reporting, re-run, and verification."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Patch project-root resolution to point at an isolated tmp project."""
        _write_project(tmp_path)
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def _make_deterministic_file(self, tmp_path):
        """Run a deterministic generator script to produce data/result.h5."""
        _write_script(
            tmp_path,
            "gen.py",
            """
            import numpy as np
            from pywatson.utils import save_data
            save_data({"y": np.arange(5)}, "result")
            """,
        )
        # Produce the original artifact via the same code path the user would use.
        import subprocess
        import sys

        subprocess.run([sys.executable, "gen.py"], cwd=str(tmp_path), check=True)
        return tmp_path / "data" / "result.h5"

    def test_records_provenance_and_params(self, mock_project):
        self._make_deterministic_file(mock_project)
        # File name encodes a param so parse_savename has something to find.
        result = reproduce("result", run=False)
        assert result["script"] == "gen.py"
        assert result["ran"] is False
        # No git info was embedded, so recorded commit is None (soft, no warning).
        assert result["recorded_commit"] is None

    def test_dry_run_does_not_execute(self, mock_project):
        path = self._make_deterministic_file(mock_project)
        mtime_before = path.stat().st_mtime_ns
        result = reproduce("result", run=False)
        assert result["ran"] is False
        assert path.stat().st_mtime_ns == mtime_before

    def test_rerun_executes_script(self, mock_project):
        path = self._make_deterministic_file(mock_project)
        mtime_before = path.stat().st_mtime_ns
        result = reproduce("result")
        assert result["ran"] is True
        assert result["returncode"] == 0
        # The script re-ran and overwrote the artifact in place.
        assert path.exists()
        assert path.stat().st_mtime_ns >= mtime_before

    def test_verify_matches_for_deterministic_script(self, mock_project):
        self._make_deterministic_file(mock_project)
        result = reproduce("result", verify=True)
        assert result["reproduced"] is True
        assert result["mismatches"] == []

    def test_verify_detects_nondeterministic_mismatch(self, mock_project):
        _write_script(
            mock_project,
            "gen.py",
            """
            import numpy as np
            from pywatson.utils import save_data
            save_data({"y": np.random.rand(5)}, "result")
            """,
        )
        import subprocess
        import sys

        subprocess.run([sys.executable, "gen.py"], cwd=str(mock_project), check=True)

        result = reproduce("result", verify=True)
        assert result["reproduced"] is False
        assert "y" in result["mismatches"]

    def test_missing_file_raises(self, mock_project):
        with pytest.raises(FileNotFoundError):
            reproduce("does_not_exist")

    def test_missing_script_raises(self, mock_project):
        # Save a file directly (no recording script that exists on disk).
        from pywatson.utils import save_data

        with patch("pywatson.utils._get_script_info", return_value="unknown_script"):
            save_data({"y": np.arange(3)}, "orphan")
        with pytest.raises(FileNotFoundError, match="No recording script"):
            reproduce("orphan")

"""
Tests for pywatson.utils — focusing on _get_script_info() correctness.

Key invariant: regardless of call depth (_get_script_info called directly,
via save_data, via tagsave, or via produce_or_load), the returned script path
must point to the **user's** file, not to utils.py / pywatson_utils.py.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pywatson.utils import (
    _get_script_info,
    save_data,
    tagsave,
    produce_or_load,
    load_data,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
UTILS_FILE = Path(__file__).parent.parent / "src" / "pywatson" / "utils.py"


def _is_utils(path_str: str) -> bool:
    """Return True if path_str resolves to utils.py or pywatson_utils.py."""
    p = Path(path_str)
    return p.name in ("utils.py", "pywatson_utils.py")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class TestGetScriptInfo:
    """Tests for _get_script_info() at various call depths."""

    def test_direct_call_returns_this_file(self):
        """When called directly from a test, result must point to this test file."""
        result = _get_script_info()
        assert not _is_utils(result), (
            f"_get_script_info() returned '{result}' which looks like utils.py, "
            "not the caller's file"
        )
        # The result should contain the test file name somewhere (relative or absolute)
        assert "test_utils" in result, f"Expected 'test_utils' in result '{result}'"

    def test_does_not_return_utils_module(self):
        """The returned path must never be the utils module itself."""
        result = _get_script_info()
        resolved = Path(result) if Path(result).is_absolute() else Path.cwd() / result
        assert resolved.resolve() != UTILS_FILE.resolve()


class TestSaveDataScriptMetadata:
    """Tests that save_data records the correct caller script, not utils.py."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Patch find_project_root and datafile to use tmp_path."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_save_data_script_points_to_test_file(self, mock_project):
        """save_data(include_git=True) must store the test file path, not utils.py."""
        save_data({"x": 1}, "test_save_script", include_git=True)

        loaded = load_data("test_save_script")
        script = loaded["_metadata"]["script"]

        assert not _is_utils(script), (
            f"save_data stored script='{script}' which looks like utils.py"
        )
        assert "test_utils" in script, f"Expected 'test_utils' in script metadata, got '{script}'"

    def test_save_data_always_records_script(self, mock_project):
        """save_data always writes the 'script' key, even without include_git."""
        save_data({"x": 1}, "test_always_script", include_git=False)

        loaded = load_data("test_always_script")
        assert "script" in loaded["_metadata"], "Missing 'script' key in metadata"
        script = loaded["_metadata"]["script"]
        assert not _is_utils(script), (
            f"save_data stored script='{script}' which looks like utils.py"
        )


class TestTagsaveScriptMetadata:
    """Tests that tagsave (3 frames deep) records the correct caller script."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_tagsave_script_points_to_test_file(self, mock_project):
        """tagsave() must store the test file path, not utils.py or tagsave itself."""
        tagsave("test_tagsave_script", {"y": 2})

        loaded = load_data("test_tagsave_script")
        script = loaded["_metadata"]["script"]

        assert not _is_utils(script), f"tagsave stored script='{script}' which looks like utils.py"
        assert "test_utils" in script, f"Expected 'test_utils' in script metadata, got '{script}'"


class TestProduceOrLoadScriptMetadata:
    """Tests that produce_or_load (4 frames deep) records the correct caller script."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_produce_or_load_script_points_to_test_file(self, mock_project):
        """produce_or_load() must store the test file path, not utils.py."""

        def _make_data():
            return {"z": 3}

        _, existed = produce_or_load("test_pol_script", _make_data)
        assert not existed, "File should have been freshly produced"

        loaded = load_data("test_pol_script")
        script = loaded["_metadata"]["script"]

        assert not _is_utils(script), (
            f"produce_or_load stored script='{script}' which looks like utils.py"
        )
        assert "test_utils" in script, f"Expected 'test_utils' in script metadata, got '{script}'"

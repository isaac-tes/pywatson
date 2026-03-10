"""Tests for pywatson.utils — path management, HDF5 I/O, savename, and script-info.

Key invariants:
  - _get_script_info must point to the caller's file, not utils.py, at any depth.
  - Path helpers return paths relative to project root; directories are auto-created
    when create=True and left alone when create=False.
  - savename produces deterministic, sorted, human-readable filenames.
  - HDF5 round-trips preserve numeric arrays, scalars, strings, and metadata.
"""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from pywatson.utils import (
    _get_script_info,
    collect_results,
    data_info,
    datadir,
    datafile,
    dict_list,
    docsdir,
    find_project_root,
    get_project_dir,
    list_data_files,
    load_array,
    load_data,
    load_npz,
    load_selective,
    notebookfile,
    notebooksdir,
    parse_savename,
    plotfile,
    plotsdir,
    produce_or_load,
    projectdir,
    safesave,
    save_array,
    save_data,
    save_npz,
    savename,
    scriptfile,
    scriptsdir,
    set_random_seed,
    snapshot_environment,
    srcdir,
    tagsave,
    testsdir,
    tmpsave,
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
        """Mock project."""
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
        """Mock project."""
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
            """Make data."""
            return {"z": 3}

        _, filepath = produce_or_load("test_pol_script", _make_data)
        assert isinstance(filepath, Path), "Second return value must be a Path"
        assert filepath.exists(), "File should have been freshly produced"

        loaded = load_data("test_pol_script")
        script = loaded["_metadata"]["script"]

        assert not _is_utils(script), (
            f"produce_or_load stored script='{script}' which looks like utils.py"
        )
        assert "test_utils" in script, f"Expected 'test_utils' in script metadata, got '{script}'"


# ---------------------------------------------------------------------------
# Path management tests
# ---------------------------------------------------------------------------


class TestFindProjectRoot:
    """Tests for find_project_root()."""

    @pytest.fixture(autouse=True)
    def reset_cache(self, monkeypatch):
        """Reset the global _PROJECT_ROOT cache before and after each test."""
        monkeypatch.setattr("pywatson.utils._PROJECT_ROOT", None)

    def test_finds_pyproject_toml(self, tmp_path):
        """Finds pyproject toml."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_finds_git_dir(self, tmp_path):
        """Finds git dir."""
        (tmp_path / ".git").mkdir()
        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_finds_root_from_subdirectory(self, tmp_path):
        """Finds root from subdirectory."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        nested = tmp_path / "src" / "mypackage"
        nested.mkdir(parents=True)
        result = find_project_root(nested)
        assert result == tmp_path

    def test_finds_nearest_marker(self, tmp_path):
        """When both a subdir and its parent have markers, the closer one wins."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "parent"')
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "pyproject.toml").write_text('[project]\nname = "sub"')
        result = find_project_root(sub)
        assert result == sub

    def test_accepts_string_path(self, tmp_path):
        """Accepts string path."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        result = find_project_root(str(tmp_path))
        assert result == tmp_path

    def test_caches_result(self, tmp_path, monkeypatch):
        """After first call, successive calls return cached value."""
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        first = find_project_root(tmp_path)
        # Removing the marker doesn't change the result because of caching
        (tmp_path / "pyproject.toml").unlink()
        second = find_project_root(tmp_path)
        assert first == second


class TestGetProjectDir:
    """Tests for get_project_dir()."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_returns_correct_path(self, mock_project):
        """Returns correct path."""
        result = get_project_dir("data", create=False)
        assert result == mock_project / "data"

    def test_creates_dir_when_create_true(self, mock_project):
        """Creates dir when create true."""
        result = get_project_dir("newdir", create=True)
        assert result.exists()
        assert result.is_dir()

    def test_does_not_create_dir_when_create_false(self, mock_project):
        """Does not create dir when create false."""
        result = get_project_dir("newdir", create=False)
        assert not result.exists()

    def test_chains_subdirs(self, mock_project):
        """Chains subdirs."""
        result = get_project_dir("data", "sims", "run1", create=False)
        assert result == mock_project / "data" / "sims" / "run1"

    def test_creates_nested_subdirs(self, mock_project):
        """Creates nested subdirs."""
        result = get_project_dir("data", "sims", "run1", create=True)
        assert result.exists()

    def test_raises_when_no_project_root(self):
        """Raises when no project root."""
        with patch("pywatson.utils.find_project_root", return_value=None):
            with pytest.raises(RuntimeError, match="Could not find project root"):
                get_project_dir("data")


class TestProjectDirHelpers:
    """Tests for datadir, plotsdir, scriptsdir, …, projectdir."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_datadir(self, mock_project):
        """Datadir."""
        assert datadir(create=False) == mock_project / "data"

    def test_plotsdir(self, mock_project):
        """Plotsdir."""
        assert plotsdir(create=False) == mock_project / "plots"

    def test_scriptsdir(self, mock_project):
        """Scriptsdir."""
        assert scriptsdir(create=False) == mock_project / "scripts"

    def test_notebooksdir(self, mock_project):
        """Notebooksdir."""
        assert notebooksdir(create=False) == mock_project / "notebooks"

    def test_docsdir(self, mock_project):
        """Docsdir."""
        assert docsdir(create=False) == mock_project / "docs"

    def test_testsdir(self, mock_project):
        """Testsdir."""
        assert testsdir(create=False) == mock_project / "tests"

    def test_srcdir(self, mock_project):
        """Srcdir."""
        assert srcdir(create=False) == mock_project / "src"

    def test_datadir_with_subdirs(self, mock_project):
        """Datadir with subdirs."""
        result = datadir("sims", "run1", create=False)
        assert result == mock_project / "data" / "sims" / "run1"

    def test_plotsdir_with_subdirs(self, mock_project):
        """Plotsdir with subdirs."""
        result = plotsdir("paper", create=False)
        assert result == mock_project / "plots" / "paper"

    def test_plotsdir_creates_subdir(self, mock_project):
        """Plotsdir creates subdir."""
        result = plotsdir("paper", create=True)
        assert result.exists()

    def test_projectdir_returns_root(self, mock_project):
        """Projectdir returns root."""
        assert projectdir() == mock_project

    def test_projectdir_raises_when_no_root(self):
        """Projectdir raises when no root."""
        with patch("pywatson.utils.find_project_root", return_value=None):
            with pytest.raises(RuntimeError):
                projectdir()


class TestConvenienceFileHelpers:
    """Tests for datafile, plotfile, scriptfile, notebookfile."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_datafile_path(self, mock_project):
        """Datafile path."""
        result = datafile("results.h5", create_dir=False)
        assert result == mock_project / "data" / "results.h5"

    def test_datafile_creates_parent_dir(self, mock_project):
        """Datafile creates parent dir."""
        datafile("results.h5", create_dir=True)
        assert (mock_project / "data").exists()

    def test_datafile_no_create(self, mock_project):
        """Datafile no create."""
        datafile("results.h5", create_dir=False)
        assert not (mock_project / "data").exists()

    def test_plotfile(self, mock_project):
        """Plotfile."""
        result = plotfile("fig1.png", create_dir=False)
        assert result == mock_project / "plots" / "fig1.png"

    def test_scriptfile(self, mock_project):
        """Scriptfile."""
        result = scriptfile("run.py", create_dir=False)
        assert result == mock_project / "scripts" / "run.py"

    def test_notebookfile(self, mock_project):
        """Notebookfile."""
        result = notebookfile("analysis.ipynb", create_dir=False)
        assert result == mock_project / "notebooks" / "analysis.ipynb"


# ---------------------------------------------------------------------------
# savename tests
# ---------------------------------------------------------------------------


class TestSavename:
    """Tests for the savename() parameter-to-filename helper."""

    def test_basic_params(self):
        """Basic params."""
        result = savename({"alpha": 0.5, "n": 100})
        assert result == "alpha=0.5_n=100.h5"

    def test_keys_are_sorted(self):
        """Keys are sorted."""
        result = savename({"z": 1, "a": 2}, suffix="")
        assert result == "a=2_z=1"

    def test_custom_suffix(self):
        """Custom suffix."""
        result = savename({"lr": 0.01}, suffix=".csv")
        assert result == "lr=0.01.csv"

    def test_custom_connector(self):
        """Custom connector."""
        result = savename({"a": 1, "b": 2}, connector=",", suffix="")
        assert result == "a=1,b=2"

    def test_float_digits_rounds(self):
        """Float digits rounds."""
        result = savename({"alpha": 0.6666666}, digits=2, suffix="")
        assert result == "alpha=0.67"

    def test_float_trailing_zeros_stripped(self):
        """Float trailing zeros stripped."""
        result = savename({"x": 1.0}, suffix="")
        assert result == "x=1"

    def test_integer_value(self):
        """Integer value."""
        result = savename({"n": 100}, suffix="")
        assert result == "n=100"

    def test_bool_value(self):
        """Bool value."""
        result = savename({"flag": True}, suffix="")
        assert result == "flag=True"

    def test_string_value(self):
        """String value."""
        result = savename({"method": "euler"}, suffix="")
        assert result == "method=euler"

    def test_empty_dict_returns_only_suffix(self):
        """Empty dict returns only suffix."""
        result = savename({}, suffix=".h5")
        assert result == ".h5"

    def test_ignore_keys(self):
        """Ignore keys."""
        result = savename({"a": 1, "b": 2, "c": 3}, ignore_keys=["b"], suffix="")
        assert result == "a=1_c=3"

    def test_access_function(self):
        """Access function."""
        result = savename({"x": [1, 2, 3]}, access=len, suffix="")
        assert result == "x=3"

    def test_deterministic_across_calls(self):
        """Deterministic across calls."""
        params = {"lr": 0.01, "n": 100, "method": "euler"}
        assert savename(params) == savename(params)


# ---------------------------------------------------------------------------
# HDF5 I/O tests
# ---------------------------------------------------------------------------


class TestHDF5IO:
    """Tests for save_data, load_data, load_selective, list_data_files, data_info."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_roundtrip_numpy_array(self, mock_project):
        """Roundtrip numpy array."""
        arr = np.array([1.0, 2.0, 3.0])
        save_data({"x": arr}, "rt_array")
        loaded = load_data("rt_array")
        np.testing.assert_array_equal(loaded["x"], arr)

    def test_roundtrip_2d_array(self, mock_project):
        """Roundtrip 2d array."""
        arr = np.arange(12).reshape(3, 4)
        save_data({"matrix": arr}, "rt_2d")
        loaded = load_data("rt_2d")
        np.testing.assert_array_equal(loaded["matrix"], arr)

    def test_roundtrip_int_scalar(self, mock_project):
        """Roundtrip int scalar."""
        save_data({"count": 42}, "rt_int")
        loaded = load_data("rt_int")
        assert int(loaded["count"]) == 42

    def test_roundtrip_float_scalar(self, mock_project):
        """Roundtrip float scalar."""
        save_data({"score": 3.14}, "rt_float")
        loaded = load_data("rt_float")
        assert abs(float(loaded["score"]) - 3.14) < 1e-6

    def test_roundtrip_string(self, mock_project):
        """Roundtrip string."""
        save_data({"label": "hello"}, "rt_str")
        loaded = load_data("rt_str")
        assert loaded["label"] == "hello"

    def test_roundtrip_list(self, mock_project):
        """Roundtrip list."""
        save_data({"values": [1, 2, 3, 4]}, "rt_list")
        loaded = load_data("rt_list")
        np.testing.assert_array_equal(loaded["values"], [1, 2, 3, 4])

    def test_metadata_is_preserved(self, mock_project):
        """Metadata is preserved."""
        meta = {"param_a": "value_a", "lr": 0.01}
        save_data({"x": 1}, "meta_test", metadata=meta)
        loaded = load_data("meta_test")
        assert loaded["_metadata"]["param_a"] == "value_a"
        assert loaded["_metadata"]["lr"] == 0.01

    def test_metadata_has_created_at(self, mock_project):
        """Metadata has created at."""
        save_data({"x": 1}, "timestamp_test")
        loaded = load_data("timestamp_test")
        assert "created_at" in loaded["_metadata"]

    def test_auto_adds_h5_extension_on_save(self, mock_project):
        """Auto adds h5 extension on save."""
        save_data({"v": 1}, "noext")
        assert (mock_project / "data" / "noext.h5").exists()

    def test_auto_adds_h5_extension_on_load(self, mock_project):
        """Auto adds h5 extension on load."""
        save_data({"v": 1}, "noext2")
        loaded = load_data("noext2")  # no .h5 suffix
        assert "v" in loaded

    def test_load_with_keys_filters(self, mock_project):
        """Load with keys filters."""
        save_data({"a": np.array([1]), "b": np.array([2]), "c": np.array([3])}, "keytest")
        loaded = load_data("keytest", keys=["a"])
        assert "a" in loaded
        assert "b" not in loaded
        assert "c" not in loaded

    def test_load_selective_returns_requested_keys(self, mock_project):
        """Load selective returns requested keys."""
        save_data({"a": np.array([10]), "b": np.array([20])}, "selective")
        loaded = load_selective("selective", ["b"])
        assert "b" in loaded
        assert "a" not in loaded

    def test_load_missing_file_raises_file_not_found(self, mock_project):
        """Load missing file raises file not found."""
        with pytest.raises(FileNotFoundError):
            load_data("this_file_does_not_exist")

    def test_list_data_files_returns_saved_files(self, mock_project):
        """List data files returns saved files."""
        save_data({"x": 1}, "file_a")
        save_data({"y": 2}, "file_b")
        files = list_data_files()
        names = {f.name for f in files}
        assert "file_a.h5" in names
        assert "file_b.h5" in names

    def test_list_data_files_empty_when_no_files(self, mock_project):
        """List data files empty when no files."""
        assert list_data_files() == []

    def test_list_data_files_empty_when_no_data_dir(self, tmp_path):
        """List data files empty when no data dir."""
        # data/ doesn't exist at all
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            assert list_data_files() == []

    def test_data_info_structure(self, mock_project):
        """Data info structure."""
        save_data({"arr": np.array([1, 2, 3])}, "info_test")
        info = data_info("info_test")
        assert "filepath" in info
        assert "size_bytes" in info
        assert "modified" in info
        assert "metadata" in info
        assert "datasets" in info
        assert "arr" in info["datasets"]

    def test_data_info_dataset_shape(self, mock_project):
        """Data info dataset shape."""
        save_data({"arr": np.zeros((5, 3))}, "shape_test")
        info = data_info("shape_test")
        assert info["datasets"]["arr"]["shape"] == (5, 3)

    def test_data_info_raises_for_missing_file(self, mock_project):
        """Data info raises for missing file."""
        with pytest.raises(FileNotFoundError):
            data_info("not_there")


# ---------------------------------------------------------------------------
# Array convenience I/O tests
# ---------------------------------------------------------------------------


class TestArrayIO:
    """Tests for save_array and load_array."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_1d_array_roundtrip(self, mock_project):
        """1d array roundtrip."""
        arr = np.array([1.0, 2.0, 3.0])
        save_array(arr, "vec")
        loaded = load_array("vec")
        np.testing.assert_array_equal(loaded, arr)

    def test_2d_array_roundtrip(self, mock_project):
        """2d array roundtrip."""
        arr = np.arange(12).reshape(3, 4)
        save_array(arr, "matrix")
        loaded = load_array("matrix")
        np.testing.assert_array_equal(loaded, arr)

    def test_load_array_by_name(self, mock_project):
        """Load array by name."""
        arr = np.array([7, 8, 9])
        save_array(arr, "named")
        loaded = load_array("named", array_name="named")
        np.testing.assert_array_equal(loaded, arr)

    def test_load_array_wrong_name_raises_key_error(self, mock_project):
        """Load array wrong name raises key error."""
        arr = np.array([1])
        save_array(arr, "onekey")
        with pytest.raises(KeyError, match="wrong_key"):
            load_array("onekey", array_name="wrong_key")

    def test_load_array_first_key_by_default(self, mock_project):
        """load_array with no array_name returns the first (and only) dataset."""
        arr = np.array([42])
        save_array(arr, "singlekey")
        loaded = load_array("singlekey")
        np.testing.assert_array_equal(loaded, arr)


# ---------------------------------------------------------------------------
# collect_results tests
# ---------------------------------------------------------------------------


class TestCollectResults:
    """Tests for collect_results()."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_returns_empty_when_no_files(self, mock_project):
        """Returns empty when no files."""
        assert collect_results() == []

    def test_collects_all_h5_files(self, mock_project):
        """Collects all h5 files."""
        save_data({"x": 1.0}, "run_a")
        save_data({"x": 2.0}, "run_b")
        results = collect_results()
        assert len(results) == 2

    def test_each_result_has_filepath_key(self, mock_project):
        """Each result has filepath key."""
        save_data({"v": 42}, "single")
        results = collect_results()
        assert len(results) == 1
        assert "_filepath" in results[0]

    def test_each_result_contains_data(self, mock_project):
        """Each result contains data."""
        save_data({"value": np.array([1, 2, 3])}, "with_data")
        results = collect_results()
        assert any("value" in r for r in results)


# ---------------------------------------------------------------------------
# parse_savename tests
# ---------------------------------------------------------------------------


class TestParseSavename:
    """Tests for parse_savename() — inverse of savename()."""

    def test_parses_float_and_int(self):
        """Parses float and int values correctly."""
        result = parse_savename("alpha=0.5_N=100.h5")
        assert result == {"alpha": 0.5, "N": 100}

    def test_parses_string_value(self):
        """Non-numeric values stay as strings."""
        result = parse_savename("method=euler_N=50.h5")
        assert result["method"] == "euler"
        assert result["N"] == 50

    def test_roundtrip_with_savename(self):
        """parse_savename(savename(d)) returns equivalent dict."""
        params = {"alpha": 0.1, "N": 200, "method": "rk4"}
        fname = savename(params, suffix=".h5")
        recovered = parse_savename(fname)
        assert recovered["N"] == 200
        assert recovered["method"] == "rk4"
        assert abs(recovered["alpha"] - 0.1) < 1e-9

    def test_strips_directory_prefix(self):
        """Directory prefix is stripped."""
        result = parse_savename("/some/path/x=1_y=2.h5")
        assert result == {"x": 1, "y": 2}

    def test_strips_multiple_extensions(self):
        """Multiple extensions like .tmp.h5 are stripped."""
        result = parse_savename("a=1_b=2.tmp.h5")
        assert result == {"a": 1, "b": 2}

    def test_ignores_bare_tokens(self):
        """Tokens without '=' are silently ignored."""
        result = parse_savename("project_alpha=0.5.h5")
        assert "alpha" in result
        assert result["alpha"] == 0.5

    def test_empty_filename_returns_empty_dict(self):
        """Empty stem gives empty dict."""
        result = parse_savename(".h5")
        assert result == {}


# ---------------------------------------------------------------------------
# dict_list tests
# ---------------------------------------------------------------------------


class TestDictList:
    """Tests for dict_list() parameter grid expansion."""

    def test_single_dict_list_values(self):
        """Expands list values into combinations."""
        result = dict_list({"alpha": [0.1, 0.5], "N": [100, 1000]})
        assert len(result) == 4
        ks = [frozenset(d.items()) for d in result]
        assert frozenset({("alpha", 0.1), ("N", 100)}) in ks
        assert frozenset({("alpha", 0.5), ("N", 1000)}) in ks

    def test_scalar_values_broadcast(self):
        """Scalar values act as single-element lists."""
        result = dict_list({"mode": "euler", "dt": [0.01, 0.001]})
        assert len(result) == 2
        assert all(r["mode"] == "euler" for r in result)

    def test_multiple_dicts_merged(self):
        """Multiple input dicts are merged before expanding."""
        result = dict_list({"a": [1, 2]}, {"b": [10, 20]})
        assert len(result) == 4

    def test_later_dict_overrides_earlier(self):
        """Later dict keys override earlier ones."""
        result = dict_list({"a": [1, 2]}, {"a": [99]})
        assert all(r["a"] == 99 for r in result)
        assert len(result) == 1

    def test_single_element_lists(self):
        """Single-element lists give a single combination."""
        result = dict_list({"x": [1], "y": [2]})
        assert result == [{"x": 1, "y": 2}]

    def test_empty_dict_returns_one_empty_dict(self):
        """Empty dict expands to a list containing one empty dict."""
        result = dict_list({})
        assert result == [{}]


# ---------------------------------------------------------------------------
# savename float significant-digits tests
# ---------------------------------------------------------------------------


class TestSavenameFloatFormatting:
    """Verify savename uses significant digits (g format) not decimal places."""

    def test_significant_digits_small_number(self):
        """Very small floats use significant digits, not zero decimal places."""
        # 0.0001 with 3 sig figs should NOT become '0' (old .3f bug)
        result = savename({"eps": 0.0001}, digits=3, suffix="")
        assert result == "eps=0.0001"

    def test_significant_digits_large_number(self):
        """Large floats use g-format (may use scientific notation)."""
        result = savename({"big": 1e8}, digits=3, suffix="")
        # g format: '1e+08'
        assert "big=" in result
        assert "0" not in result.split("=")[1] or "e" in result.split("=")[1]

    def test_trailing_zeros_stripped(self):
        """Trailing zeros are removed by g format."""
        result = savename({"x": 1.0}, suffix="")
        assert result == "x=1"  # not 'x=1.000'

    def test_two_sig_figs(self):
        """digits=2 gives 2 significant figures."""
        result = savename({"alpha": 0.6666666}, digits=2, suffix="")
        assert result == "alpha=0.67"


# ---------------------------------------------------------------------------
# ProduceOrLoad return-type tests
# ---------------------------------------------------------------------------


class TestProduceOrLoad:
    """Tests for produce_or_load() — caching, return type, subdir."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project with data dir."""
        (tmp_path / "data").mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_returns_data_and_path_on_first_call(self, mock_project):
        """First call produces data and returns (data, Path)."""

        def make():
            return {"v": 42}

        data, path = produce_or_load("pol_first", make)
        assert data["v"] == 42
        assert isinstance(path, Path)
        assert path.exists()

    def test_returns_cached_data_and_same_path_on_second_call(self, mock_project):
        """Second call loads from cache and returns same path."""

        def make():
            return {"v": 99}

        _, path1 = produce_or_load("pol_cache", make)
        _, path2 = produce_or_load("pol_cache", make)
        assert path1 == path2

    def test_producing_function_not_called_on_cache_hit(self, mock_project):
        """Producing function is only called once."""
        call_count = [0]

        def make():
            call_count[0] += 1
            return {"x": 1}

        produce_or_load("pol_once", make)
        produce_or_load("pol_once", make)
        assert call_count[0] == 1

    def test_raises_type_error_for_non_dict(self, mock_project):
        """Raises TypeError if producing function doesn't return dict."""
        with pytest.raises(TypeError):
            produce_or_load("pol_bad", lambda: [1, 2, 3])


# ---------------------------------------------------------------------------
# save_data subdir tests
# ---------------------------------------------------------------------------


class TestSaveDataSubdir:
    """Tests for save_data/load_data with subdir parameter."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project with data dir."""
        (tmp_path / "data").mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_saves_to_subdir(self, mock_project):
        """File is saved inside data/subdir/."""
        path = save_data({"x": 1}, "sim", subdir="sims")
        assert path == mock_project / "data" / "sims" / "sim.h5"
        assert path.exists()

    def test_creates_subdir_automatically(self, mock_project):
        """Subdirectory is created if it does not exist."""
        save_data({"x": 2}, "run", subdir="new_subdir")
        assert (mock_project / "data" / "new_subdir").is_dir()


# ---------------------------------------------------------------------------
# safesave tests
# ---------------------------------------------------------------------------


class TestSafesave:
    """Tests for safesave() atomic write."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        (tmp_path / "data").mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_safesave_creates_file(self, mock_project):
        """safesave writes an HDF5 file at the expected path."""
        path = safesave("safe_out", {"x": np.array([1, 2, 3])})
        assert path.exists()
        assert path.suffix == ".h5"

    def test_safesave_data_readable(self, mock_project):
        """Data written by safesave round-trips via load_data."""
        safesave("safe_rt", {"score": 7.7})
        data = load_data("safe_rt")
        assert abs(float(data["score"]) - 7.7) < 1e-6

    def test_safesave_no_tmp_files_left(self, mock_project):
        """No leftover .tmp.h5 files after a successful write."""
        safesave("safe_clean", {"v": 1})
        tmp_files = list((mock_project / "data").glob("*.tmp.h5"))
        assert tmp_files == []


# ---------------------------------------------------------------------------
# tmpsave tests
# ---------------------------------------------------------------------------


class TestTmpsave:
    """Tests for tmpsave() context manager."""

    def test_file_exists_inside_context(self):
        """Temporary file exists while inside the context."""
        with tmpsave({"a": np.array([1, 2])}) as p:
            assert p.exists()

    def test_file_deleted_after_context(self):
        """Temporary file is removed after the context exits."""
        with tmpsave({"a": np.array([1, 2])}) as p:
            path = p
        assert not path.exists()

    def test_data_readable_inside_context(self):
        """HDF5 data saved by tmpsave is readable inside the context."""
        import h5py

        with tmpsave({"z": np.zeros((3, 3))}) as p:
            with h5py.File(p, "r") as f:
                assert "z" in f


# ---------------------------------------------------------------------------
# snapshot_environment tests
# ---------------------------------------------------------------------------


class TestSnapshotEnvironment:
    """Tests for snapshot_environment()."""

    def test_returns_dict(self):
        """Returns a dictionary."""
        result = snapshot_environment()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        """Dictionary has required keys."""
        result = snapshot_environment()
        assert "python_version" in result
        assert "platform" in result
        assert "packages" in result
        assert "captured_at" in result

    def test_python_version_matches_runtime(self):
        """Python version matches sys.version_info."""
        import sys

        result = snapshot_environment()
        version = result["python_version"]
        assert str(sys.version_info.major) in version
        assert str(sys.version_info.minor) in version

    def test_packages_is_list(self):
        """Packages field is a list of strings."""
        result = snapshot_environment()
        assert isinstance(result["packages"], list)


# ---------------------------------------------------------------------------
# set_random_seed tests
# ---------------------------------------------------------------------------


class TestSetRandomSeed:
    """Tests for set_random_seed()."""

    def test_returns_dict_with_seed(self):
        """Returns {"random_seed": seed}."""
        result = set_random_seed(42)
        assert result == {"random_seed": 42}

    def test_numpy_reproducibility(self):
        """Calling set_random_seed() twice gives the same numpy output."""
        set_random_seed(123)
        a = np.random.rand(5)
        set_random_seed(123)
        b = np.random.rand(5)
        np.testing.assert_array_equal(a, b)

    def test_different_seeds_give_different_output(self):
        """Different seeds produce (almost certainly) different output."""
        set_random_seed(1)
        a = np.random.rand(10)
        set_random_seed(2)
        b = np.random.rand(10)
        assert not np.array_equal(a, b)


# ---------------------------------------------------------------------------
# NPZ format tests
# ---------------------------------------------------------------------------


class TestNPZ:
    """Tests for save_npz() and load_npz()."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project with data dir."""
        (tmp_path / "data").mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_saves_and_loads_array(self, mock_project):
        """Array survives a round-trip through NPZ."""
        arr = np.array([1.0, 2.0, 3.0])
        save_npz({"arr": arr}, "npz_rt")
        loaded = load_npz("npz_rt")
        np.testing.assert_array_equal(loaded["arr"], arr)

    def test_file_has_npz_extension(self, mock_project):
        """Saved file has .npz extension."""
        path = save_npz({"x": np.eye(3)}, "npz_ext")
        assert path.suffix == ".npz"
        assert path.exists()

    def test_metadata_roundtrip(self, mock_project):
        """Metadata dict survives round-trip via _metadata_json."""
        meta = {"run": "exp1", "lr": 0.01}
        save_npz({"y": np.zeros(5)}, "npz_meta", metadata=meta)
        loaded = load_npz("npz_meta")
        assert "_metadata" in loaded
        assert loaded["_metadata"]["run"] == "exp1"

    def test_load_nonexistent_raises_file_not_found(self, mock_project):
        """load_npz raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_npz("definitely_missing")

    def test_save_with_subdir(self, mock_project):
        """Files can be saved in a subdirectory."""
        path = save_npz({"z": np.ones(4)}, "npz_sub", subdir="arrays")
        assert path.exists()
        assert "arrays" in str(path)


# ---------------------------------------------------------------------------
# collect_results as_dataframe tests
# ---------------------------------------------------------------------------


class TestCollectResultsDataFrame:
    """Tests for collect_results(as_dataframe=True)."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Mock project."""
        (tmp_path / "data").mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_returns_dataframe(self, mock_project):
        """Returns a pandas DataFrame when as_dataframe=True."""
        pd = pytest.importorskip("pandas")
        save_data({"score": 1.0}, "df_a", metadata={"run": "a"})
        save_data({"score": 2.0}, "df_b", metadata={"run": "b"})
        df = collect_results(as_dataframe=True)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_dataframe_has_filepath_column(self, mock_project):
        """DataFrame includes _filepath column."""
        pytest.importorskip("pandas")
        save_data({"x": 1.0}, "df_fp")
        df = collect_results(as_dataframe=True)
        assert "_filepath" in df.columns


# ---------------------------------------------------------------------------
# Zarr tests
# ---------------------------------------------------------------------------


class TestZarr:
    """Tests for save_zarr() and load_zarr()."""

    @pytest.fixture()
    def mock_project(self, tmp_path):
        """Set up a mock project root with a data/ directory."""
        (tmp_path / "data").mkdir()
        with (
            patch("pywatson.utils._PROJECT_ROOT", tmp_path),
            patch("pywatson.utils.find_project_root", return_value=tmp_path),
        ):
            yield tmp_path

    def test_save_creates_store(self, mock_project):
        """save_zarr creates a .zarr directory."""
        from pywatson.utils import save_zarr

        path = save_zarr({"values": np.arange(10)}, "test_store")
        assert path.exists()
        assert path.suffix == ".zarr"

    def test_roundtrip(self, mock_project):
        """Saved arrays can be loaded back exactly."""
        from pywatson.utils import load_zarr, save_zarr

        arr = np.linspace(0, 1, 50)
        save_zarr({"signal": arr}, "zarr_rt")
        loaded = load_zarr("zarr_rt")
        np.testing.assert_array_almost_equal(loaded["signal"], arr)

    def test_metadata_roundtrip(self, mock_project):
        """Metadata is preserved through save/load."""
        from pywatson.utils import load_zarr, save_zarr

        meta = {"run": "exp42", "temperature": 300}
        save_zarr({"x": np.zeros(5)}, "zarr_meta", metadata=meta)
        loaded = load_zarr("zarr_meta")
        assert "_metadata" in loaded
        assert loaded["_metadata"]["run"] == "exp42"

    def test_selective_key_loading(self, mock_project):
        """Only requested keys are returned when keys= is given."""
        from pywatson.utils import load_zarr, save_zarr

        save_zarr({"a": np.ones(3), "b": np.zeros(3)}, "zarr_keys")
        loaded = load_zarr("zarr_keys", keys=["a"])
        assert "a" in loaded
        assert "b" not in loaded

    def test_save_with_subdir(self, mock_project):
        """Store can be placed in a subdirectory."""
        from pywatson.utils import save_zarr

        path = save_zarr({"z": np.eye(2)}, "zarr_sub", subdir="arrays")
        assert path.exists()
        assert "arrays" in str(path)

    def test_load_nonexistent_raises(self, mock_project):
        """load_zarr raises FileNotFoundError for absent stores."""
        from pywatson.utils import load_zarr

        with pytest.raises(FileNotFoundError):
            load_zarr("no_such_store")

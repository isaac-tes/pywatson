"""
End-to-end Docker reproducibility tests — the Zenodo scenario.

What these tests verify
-----------------------
These tests simulate the two-actor Zenodo reproducibility workflow:

  RESEARCHER
    1. ``pywatson init --docker`` to scaffold the project
    2. Generate data with ``scripts/generate_data.py``
    3. ``docker build`` and push the image to GHCR

  READER
    4. Pull the image (or build locally)
    5. Download data archive from Zenodo, unpack into ``./data/``
    6. ``docker run --rm -v ./data:/workspace/data:ro -v ./plots:/workspace/plots <image>``
       (or equivalently ``docker compose run reproduce``)
    7. Plots appear in ``./plots/``

The tests here exercise steps 1–3 (build) and 4–7 (run) in a temporary
project created on the fly.

Running
-------
These tests are marked ``@pytest.mark.docker`` and are **skipped** during the
normal ``uv run pytest`` run so the CI suite stays fast.  Run them explicitly:

    uv run pytest tests/test_docker_e2e.py -m docker -v

They require the Docker daemon to be running.  On macOS, start Docker Desktop
first:

    open -a Docker

Requirements
------------
- Docker ≥ 20 (``docker build``, ``docker run``, ``docker rmi``)
- Internet access (to pull ``python:<version>-slim`` and install uv)
- ~500 MB of free disk space for the image layers
"""

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Generator

import pytest

# ---------------------------------------------------------------------------
# Helper: is the Docker daemon reachable?
# ---------------------------------------------------------------------------


def _docker_daemon_running() -> bool:
    """Return True if the Docker daemon responds to ``docker info``."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


_SKIP_DOCKER = not _docker_daemon_running()
_docker = pytest.mark.skipif(_SKIP_DOCKER, reason="Docker daemon not reachable")

# Apply both the `docker` mark (for -m docker selection) and the skipif guard
# to every test in this module automatically.
pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(_SKIP_DOCKER, reason="Docker daemon not reachable"),
]


# ---------------------------------------------------------------------------
# Module-scoped fixtures (build the image once for all tests in this module)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scaffolded_project() -> Generator[Path, None, None]:
    """
    Scaffold a complete 'full' project with ``--docker`` via the ``pywatson init``
    CLI, which also runs ``uv init`` + ``uv add`` so ``pyproject.toml`` and
    ``uv.lock`` are present (required by ``Dockerfile RUN uv sync --frozen``).

    After scaffolding, runs ``scripts/generate_data.py`` inside the project to
    populate ``data/`` — simulating the researcher creating their dataset.

    Module-scoped so the expensive scaffolding + package installation step runs
    only once for the entire E2E test module.

    The temp directory is placed under ``~/.cache/pywatson-e2e`` so that colima
    can access it via its default ``$HOME`` mount.  Pytest's ``tmp_path_factory``
    creates dirs in ``/private/var/folders/…`` which is outside colima's mount.

    Yields
    ------
    Path
        Root directory of the scaffolded project.
    """
    # Place under $HOME so colima's default $HOME virtiofs mount can see the path.
    e2e_base = Path.home() / ".cache" / "pywatson-e2e"
    e2e_base.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=e2e_base))
    project_name = "e2e-docker-proj"

    # Use the full CLI so uv init / uv add / uv sync all run and uv.lock is created.
    # Run via `uv run pywatson` so the installed entry-point is resolved correctly.
    pywatson_root = Path(__file__).parent.parent  # repo root
    result = subprocess.run(
        [
            "uv", "run", "pywatson", "init", project_name,
            "--author-name", "E2E Test",
            "--author-email", "e2e@test.com",
            "--description", "E2E Docker reproducibility test project",
            "--project-type", "full",
            "--docker",
            "--path", str(tmp_dir),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=pywatson_root,
    )
    assert result.returncode == 0, (
        f"pywatson init failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    project_path = tmp_dir / project_name
    assert project_path.exists(), f"Project directory not created at {project_path}"
    assert (project_path / "pyproject.toml").exists(), "pyproject.toml missing after init"
    assert (project_path / "uv.lock").exists(), "uv.lock missing after init"

    # Generate data — simulates the researcher creating their dataset
    run_result = subprocess.run(
        ["uv", "run", "python", "scripts/generate_data.py"],
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run_result.returncode == 0, (
        f"generate_data.py failed:\n{run_result.stdout}\n{run_result.stderr}"
    )

    # Verify data was produced
    data_files = list((project_path / "data").rglob("*.h5"))
    assert len(data_files) > 0, "generate_data.py produced no HDF5 files"

    yield project_path

    # Teardown: remove the temporary project directory
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def docker_image(scaffolded_project: Path) -> Generator[str, None, None]:
    """
    Build the Docker image from the scaffolded project.

    This fixture is module-scoped so the image is built only once.
    The image is removed after all tests in the module have run.

    Yields
    ------
    str
        The Docker image tag (``pywatson-e2e-<hex>:latest``).
    """
    tag = f"pywatson-e2e-{uuid.uuid4().hex[:8]}:latest"
    # Also tag with the project name so ``docker compose run reproduce --no-build``
    # can find the pre-built image without triggering a second build.
    project_name = scaffolded_project.name  # e.g. "e2e-docker-proj"
    compose_tag = f"{project_name}:latest"

    result = subprocess.run(
        ["docker", "build", "-t", tag, "-t", compose_tag, "."],
        cwd=scaffolded_project,
        capture_output=True,
        text=True,
        timeout=600,  # 10 min — pulling python:slim + installing uv + packages
    )

    assert result.returncode == 0, (
        f"docker build failed.\n\n"
        f"=== STDOUT ===\n{result.stdout}\n\n"
        f"=== STDERR ===\n{result.stderr}"
    )

    yield tag

    # Teardown: remove both test images from the local daemon
    subprocess.run(["docker", "rmi", "-f", tag, compose_tag], capture_output=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDockerBuild:
    """Tests that ``docker build`` produces a functional image."""


    def test_image_tag_exists_after_build(self, docker_image):
        """The image must appear in ``docker images`` output after building."""
        result = subprocess.run(
            ["docker", "images", "-q", docker_image],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() != "", (
            f"Image '{docker_image}' not found after build"
        )


    def test_image_has_correct_entrypoint(self, docker_image):
        """The image ENTRYPOINT must reference analyze_data.py."""
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{json .Config.Entrypoint}}", docker_image],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "analyze_data.py" in result.stdout, (
            f"Expected analyze_data.py in ENTRYPOINT, got: {result.stdout.strip()}"
        )


    def test_image_working_dir_is_workspace(self, docker_image):
        """The image WORKDIR must be /workspace."""
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.Config.WorkingDir}}", docker_image],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "/workspace", (
            f"Expected WorkingDir=/workspace, got: {result.stdout.strip()}"
        )


    def test_uv_is_available_inside_image(self, docker_image):
        """uv must be on PATH inside the container."""
        # Override ENTRYPOINT so we run ``uv --version`` directly rather than
        # having the args appended to the default ENTRYPOINT.
        result = subprocess.run(
            ["docker", "run", "--rm", "--entrypoint", "uv", docker_image, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"uv not found inside image:\n{result.stderr}"
        )
        assert "uv" in result.stdout.lower(), result.stdout


class TestDockerReproduceScenario:
    """
    The Zenodo reader scenario: mount data (read-only) + empty plots dir,
    run the container, verify plots are produced.
    """


    def test_docker_run_reproduce_produces_plots(self, scaffolded_project, docker_image):
        """
        Core Zenodo scenario test.

        Steps
        -----
        1. Ensure data/ has HDF5 files (generated by the scaffolded_project fixture).
        2. Clear any existing plots so we can be sure the container created them.
        3. Run the container with data/ mounted read-only and plots/ mounted rw.
        4. Assert exit code 0.
        5. Assert that at least one ``.png`` file was created in plots/.
        """
        data_dir = scaffolded_project / "data"
        plots_dir = scaffolded_project / "plots"
        plots_dir.mkdir(exist_ok=True)

        # Clear existing plots to prove the container creates them
        for existing in plots_dir.glob("*.png"):
            existing.unlink()

        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{data_dir}:/workspace/data:ro",
                "-v", f"{plots_dir}:/workspace/plots",
                docker_image,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, (
            f"docker run failed.\n\n"
            f"=== STDOUT ===\n{result.stdout}\n\n"
            f"=== STDERR ===\n{result.stderr}"
        )

        plot_files = list(plots_dir.glob("*.png"))
        assert len(plot_files) > 0, (
            f"Container ran successfully but no .png files in plots/.\n"
            f"Container stdout:\n{result.stdout}"
        )


    def test_docker_run_fails_gracefully_without_data(self, scaffolded_project, docker_image):
        """
        Without data files, analyze_data.py should exit non-zero or print an
        error — not silently produce empty plots.

        This guards against regressions where missing data goes undetected.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as empty_data_dir:
            with tempfile.TemporaryDirectory() as tmp_plots_dir:
                result = subprocess.run(
                    [
                        "docker", "run", "--rm",
                        "-v", f"{empty_data_dir}:/workspace/data:ro",
                        "-v", f"{tmp_plots_dir}:/workspace/plots",
                        docker_image,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

        # analyze_data.py prints an error message and returns early (exit 0)
        # OR exits with non-zero — either is acceptable; what matters is that no
        # plots were silently generated from non-existent data.
        combined_output = result.stdout + result.stderr
        assert (
            "not found" in combined_output.lower()
            or "error" in combined_output.lower()
            or "FileNotFoundError" in combined_output
            or result.returncode != 0
        ), (
            "Container should report missing data files, but produced no error.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


    def test_docker_compose_reproduce_service_runs(self, scaffolded_project, docker_image):
        """
        ``docker compose run reproduce`` must exit 0 and produce plots.

        This exercises the exact command documented in README_DOCKER.md.
        The compose file's reproduce service mounts data/:ro and plots/:rw.
        """
        plots_dir = scaffolded_project / "plots"
        plots_dir.mkdir(exist_ok=True)

        # Clear plots
        for f in plots_dir.glob("*.png"):
            f.unlink()

        result = subprocess.run(
            # The compose file's reproduce service uses image: e2e-docker-proj:latest.
            # The docker_image fixture already built and tagged with that name, so
            # compose finds the pre-built image without rebuilding.
            ["docker", "compose", "run", "--rm", "reproduce"],
            cwd=scaffolded_project,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, (
            f"docker compose run reproduce failed.\n\n"
            f"=== STDOUT ===\n{result.stdout}\n\n"
            f"=== STDERR ===\n{result.stderr}"
        )

        plot_files = list(plots_dir.glob("*.png"))
        assert len(plot_files) > 0, (
            f"docker compose run reproduce succeeded but plots/ is empty.\n"
            f"stdout:\n{result.stdout}"
        )

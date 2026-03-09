# Docker Guide for Scientists

> **Who this is for** — researchers comfortable with Python and the command
> line who have never used Docker before, and want to understand what it is,
> why it helps reproducibility, and how to use the files PyWatson generates.

---

## Table of Contents

1. [What is Docker and why should I care?](#what-is-docker-and-why-should-i-care)
2. [Installing Docker](#installing-docker)
   - [macOS](#macos)
   - [Linux](#linux)
   - [Windows](#windows)
3. [Core concepts in plain language](#core-concepts-in-plain-language)
4. [Files PyWatson generates](#files-pywatson-generates)
5. [Building your image (researcher workflow)](#building-your-image-researcher-workflow)
6. [Running the analysis (reader workflow)](#running-the-analysis-reader-workflow)
7. [Publishing to GitHub Container Registry](#publishing-to-github-container-registry)
8. [Common problems and fixes](#common-problems-and-fixes)
9. [Cheat sheet](#cheat-sheet)

---

## What is Docker and why should I care?

Imagine you send a collaborator your Python analysis script. They run it and
get different numbers. Why? They have a different NumPy version, a different
SciPy, maybe even a different OS. Debugging takes days.

**Docker solves this by shipping the entire environment along with the code.**

A Docker *image* is like a snapshot of a computer with:
- a specific version of Python
- every library pinned to an exact version
- your scripts, pre-installed and ready

You build the image once. A reviewer can run it a year later on any machine
and get identical results — no `pip install`, no conda, no version headaches.

### The Zenodo connection

Journals and funders increasingly require that analysis results be
reproducible. A common pattern is:

```
Code + environment  →  Docker image     →  Published on GHCR (free)
Data                →  Zenodo deposit   →  Citable DOI, long-term storage
                          ↓
                   Reader runs:
                   docker compose run reproduce
                   → identical plots appear
```

PyWatson's `--docker` flag scaffolds everything needed for this workflow.

---

## Installing Docker

### macOS

There are two good options:

#### Option A — Docker Desktop (official, GUI)

1. Download from <https://www.docker.com/products/docker-desktop>
2. Open the `.dmg` and drag Docker to Applications
3. Launch Docker — a whale icon appears in the menu bar when it's running
4. Verify:

   ```bash
   docker --version
   docker run --rm hello-world
   ```

#### Option B — colima (lightweight, CLI only, recommended for servers/CI)

[colima](https://github.com/abiosoft/colima) is a minimal macOS container
runtime with no GUI and no licence restrictions.

```bash
# Install both the Docker CLI and colima
brew install docker colima docker-compose

# Tell the Docker CLI where to find the colima compose plugin
python3 - <<'EOF'
import json, pathlib
cfg = pathlib.Path.home() / ".docker" / "config.json"
config = json.loads(cfg.read_text()) if cfg.exists() else {}
dirs = config.setdefault("cliPluginsExtraDirs", [])
plugin = "/opt/homebrew/lib/docker/cli-plugins"
if plugin not in dirs:
    dirs.append(plugin)
cfg.write_text(json.dumps(config, indent=2))
print("Done:", cfg)
EOF

# Start the VM (run once; persists across reboots after first start)
colima start --cpu 2 --memory 4

# Verify
docker --version
docker compose version
docker run --rm hello-world
```

> `colima start` must be run after each machine reboot.  Add it to your shell
> profile or a startup script if you use Docker daily.

### Linux

Docker Engine is available as a system package:

```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose-v2
sudo usermod -aG docker $USER   # allow running docker without sudo
newgrp docker                   # apply group change immediately
```

For other distributions, follow the [official install guide](https://docs.docker.com/engine/install/).

### Windows

Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/).
Enable WSL 2 integration when prompted.

---

## Core concepts in plain language

| Term | What it means |
|------|--------------|
| **Image** | A frozen, portable snapshot of a complete environment. Like a VM, but much lighter. Built from a `Dockerfile`. |
| **Container** | A running instance of an image. Starts in milliseconds. Multiple containers can run from the same image. |
| **Dockerfile** | A recipe for building an image: which base OS, which packages to install, which files to copy. |
| **Volume / bind mount** | A bridge between a directory on your laptop and a path inside the container (`-v ./data:/workspace/data:ro`). The container can read your data without it being baked into the image. |
| **docker compose** | A tool for defining multi-container setups in a YAML file. PyWatson uses it so readers only need to type one command. |
| **Registry** | A place to store and share images. GitHub Container Registry (GHCR) is free for public images. |
| `:ro` | Read-only mount. The container can read from `data/` but cannot write to it — safe for your raw data. |

---

## Files PyWatson generates

Run `pywatson init my-project --docker` and you get these extra files:

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

# system tools required by some scientific packages
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /workspace

# copy only what uv needs to install dependencies
# (README.md is referenced by pyproject.toml as the project readme)
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --no-dev --frozen   # exact versions from uv.lock; no internet needed after this

# copy the analysis scripts
COPY scripts/ ./scripts/

# pre-create directories that will be bind-mounted at runtime
RUN mkdir -p data plots

# default action: run the analysis pipeline
ENTRYPOINT ["uv", "run", "python", "scripts/analyze_data.py"]
```

Key design decisions:
- `--frozen` means `uv.lock` is the source of truth — builds are bit-identical
- `data/` and `plots/` are **not** copied into the image; they are mounted at
  runtime, keeping the image lean and data separate
- The `ENTRYPOINT` runs your main analysis script automatically

### `docker-compose.yml`

```yaml
services:
  reproduce:
    build: .
    image: my-project:latest
    volumes:
      - ./data:/workspace/data:ro    # your Zenodo data, read-only
      - ./plots:/workspace/plots     # plots written here
    entrypoint: ["uv", "run", "python", "scripts/analyze_data.py"]

  shell:
    build: .
    image: my-project:latest
    volumes:
      - ./data:/workspace/data:ro
      - ./plots:/workspace/plots
      - ./scripts:/workspace/scripts
    entrypoint: ["/bin/bash"]
    stdin_open: true
    tty: true
```

- `reproduce` — one-command reproduction: `docker compose run reproduce`
- `shell` — interactive debug session: `docker compose run shell`

### `README_DOCKER.md`

Reader-facing instructions, filled in with your project name and GitHub
username.  Tell reviewers to read this file.

### `.github/workflows/docker-publish.yml`

Automatically builds the image and pushes it to GHCR every time you push a
git tag (e.g. `v1.0.0`).  You only need to tag a release and GitHub does the
rest.

---

## Building your image (researcher workflow)

After scaffolding with `--docker`, do this once at the start of your project
and again whenever you add or change dependencies:

```bash
cd my-project

# 1. Make sure your package list is up to date
uv sync                        # updates uv.lock

# 2. Build the Docker image
docker build -t my-project:latest .

# 3. Quick sanity check — did the analysis script start without errors?
docker run --rm \
  -v "$PWD/data":/workspace/data:ro \
  -v "$PWD/plots":/workspace/plots \
  my-project:latest
```

The first build takes a few minutes (it pulls `python:3.12-slim` and installs
all packages). Subsequent builds reuse cached layers and are much faster.

### What is layer caching?

Docker builds images in layers, one per `RUN`/`COPY` instruction.  If a layer
has not changed since the last build, Docker reuses it instantly.

PyWatson's `Dockerfile` copies `pyproject.toml`, `uv.lock`, and `README.md`
*before* copying `src/`, so that the `uv sync` step is only re-run when those
files change — not every time you edit a script.

---

## Running the analysis (reader workflow)

This is what a reviewer or collaborator does:

```bash
# Step 1 — get the image (one of the following)
docker pull ghcr.io/YOUR_GITHUB_USERNAME/my-project:v1.0.0   # from GHCR
# or build locally from the released source code:
# git clone https://... && docker build -t my-project:latest .

# Step 2 — download data from Zenodo and unpack into ./data/
#   The Zenodo DOI and download link are in README_DOCKER.md.
unzip zenodo-archive.zip           # or: tar xf data.tar.gz
ls data/                           # should show your .h5 / .csv / etc. files

# Step 3 — reproduce
mkdir -p plots
docker compose run reproduce
# → plots appear in ./plots/
```

That's it.  No Python, no conda, no version conflicts.

### Verifying the plots match

A good practice is to commit a reference copy of the expected plots in a
`plots/reference/` directory so reviewers can diff them:

```bash
ls plots/reference/        # expected figures from the paper
ls plots/                  # figures just produced by the container
```

---

## Publishing to GitHub Container Registry

The `docker-publish.yml` workflow does this automatically on every git tag.
Here is how to trigger it:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will:
1. Check out the code
2. Build the Docker image
3. Run a smoke test (calls `analyze_data.py` with empty data, checks it exits cleanly)
4. Push to `ghcr.io/YOUR_GITHUB_USERNAME/my-project:v1.0.0`

### First-time setup

The workflow uses `GITHUB_TOKEN`, which is automatic — no extra secrets
needed.  You may need to set the package visibility to "public" from the
GitHub repository → Packages → your image → Settings.

---

## Common problems and fixes

### `docker: command not found`

Docker is not installed or not on `PATH`.  See [Installing Docker](#installing-docker).

On macOS with colima: make sure `colima start` has been run this session.

```bash
colima status   # shows "running" or "stopped"
colima start    # if stopped
```

### `Cannot connect to the Docker daemon`

The Docker daemon is not running.

- **macOS Docker Desktop**: launch the app from Applications
- **macOS colima**: `colima start`
- **Linux**: `sudo systemctl start docker`

### `docker compose run reproduce` fails with "data files not found"

The `data/` directory is empty or contains files with unexpected names.
`analyze_data.py` expects specific HDF5 filenames (written by `generate_data.py`).

```bash
ls data/                              # check what's there
docker compose run shell              # open a shell inside the container
ls /workspace/data/                   # see what the container sees
```

### `uv sync --frozen` fails during build

`uv.lock` is not committed to the repository.  Make sure to commit it:

```bash
git add uv.lock
git commit -m "chore: commit uv lockfile"
```

### Build is very slow every time

Layer caching is not working.  Common cause: you edited `pyproject.toml` or
`uv.lock`, which invalidates the `uv sync` layer.  This is expected — Docker
must re-install packages when dependencies change.

If you are only editing scripts, only the `COPY scripts/` layer (and those
after it) are re-run, which is fast.

### Volume mounts show an empty directory inside the container

On **macOS with colima**, volumes must be under `$HOME` (colima's default
virtiofs mount covers `$HOME`).  Paths like `/private/var/folders/…` (used by
`pytest`'s `tmp_path`) are not visible inside the VM.

Solution: use absolute paths under your home directory:

```bash
docker run --rm \
  -v "$HOME/my-project/data":/workspace/data:ro \
  -v "$HOME/my-project/plots":/workspace/plots \
  my-project:latest
```

---

## Cheat sheet

```bash
# Build the image from the current directory
docker build -t my-project:latest .

# Run the full analysis pipeline (mount data ro, plots rw)
docker run --rm \
  -v "$PWD/data":/workspace/data:ro \
  -v "$PWD/plots":/workspace/plots \
  my-project:latest

# Same thing via docker compose
docker compose run reproduce

# Open an interactive shell inside the container
docker compose run shell

# List all local images
docker images

# Remove a specific image
docker rmi my-project:latest

# Remove all stopped containers and unused images (clean up disk)
docker system prune

# See logs from the last container run
docker logs $(docker ps -lq)

# Inspect the image metadata (ENTRYPOINT, WorkingDir, etc.)
docker inspect my-project:latest

# Pull a published image
docker pull ghcr.io/username/my-project:v1.0.0

# Push a locally built image (requires login)
docker login ghcr.io
docker push ghcr.io/username/my-project:v1.0.0
```

---

> **Further reading**
> - [Docker official docs](https://docs.docker.com/get-started/)
> - [docs/ZENODO.md](ZENODO.md) — full Zenodo deposit and DOI linking guide
> - `README_DOCKER.md` inside your generated project — reader-facing instructions

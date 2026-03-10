# Zenodo Reproducibility Guide

This guide explains how to deposit your scientific project's data and
environment on [Zenodo](https://zenodo.org) so that **anyone** can reproduce
your results from scratch — no Python installation required.

The workflow relies on:
- **Zenodo** — for long-term, DOI-citable data archiving
- **Docker** — for capturing the complete software environment
- **GitHub Container Registry (GHCR)** — for hosting the container image

---

## Table of Contents

1. [Overview](#overview)
2. [One-Time Setup: Scaffold with --docker](#one-time-setup-scaffold-with-docker)
3. [Deposit Data on Zenodo](#deposit-data-on-zenodo)
4. [Publish the Docker Image](#publish-the-docker-image)
5. [Reader Reproduction Steps](#reader-reproduction-steps)
6. [Linking Code, Data, and Software](#linking-code-data-and-software)
7. [Checklist Before Submitting a Paper](#checklist-before-submitting-a-paper)

---

## Overview

The reproducibility stack looks like this:

```
Reader
  │
  ├─ 1. Pulls Docker image from GHCR   ← contains: code + dependencies
  │       ghcr.io/you/my-analysis:v1.0.0
  │
  ├─ 2. Downloads data from Zenodo     ← contains: raw/processed data
  │       DOI: 10.5281/zenodo.XXXXXXX
  │
  └─ 3. docker compose run reproduce   ← mounts data, runs analysis, outputs plots
           ./plots/figure_1.pdf  ✓
           ./plots/figure_2.pdf  ✓
```

**Why separate image and data?**
Docker images should be lightweight and versionable via git tags.
Data (often GB+) belongs on a data repository (Zenodo) with its own DOI.
Keeping them separate means:
- The image can be rebuilt without re-uploading 10 GB of data
- Data can be updated/versioned independently

---

## One-Time Setup: Scaffold with `--docker`

When creating a new project, pass `--docker` to generate all Docker files:

```bash
pywatson init my-analysis \
  --author-name "Jane Doe" \
  --author-email "jane@university.edu" \
  --description "Spin-chain Monte Carlo study" \
  --project-type full \
  --docker
```

This generates:

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the analysis environment |
| `.dockerignore` | Excludes data/plots from image (stays lean) |
| `docker-compose.yml` | One-command reproduction workflow |
| `README_DOCKER.md` | Reader-facing reproduction instructions |
| `.github/workflows/docker-publish.yml` | Automatic image builds on push |

### Commit and push immediately

```bash
cd my-analysis
git add .
git commit -m "feat: initial project scaffold with Docker"
git push -u origin main
```

GitHub Actions will now automatically build and push the Docker image to GHCR
on every push to `main` and on every semver tag (e.g. `v1.0.0`).

---

## Deposit Data on Zenodo

### Step 1 — Connect Zenodo to GitHub (recommended)

1. Go to <https://zenodo.org/account/settings/github/>
2. Toggle ON your repository
3. Push a tag → Zenodo automatically creates a record with DOI

```bash
git tag v1.0.0
git push origin v1.0.0
```

Zenodo will create:
- A record for the **code** snapshot (the tag's zip/tarball)
- DOI: `10.5281/zenodo.XXXXXXX`

> **Important**: this archives the *code*, not your HDF5 data.  
> You still need a separate data deposit (Step 2).

### Step 2 — Create a standalone data deposit

Your raw and processed data does not live in git. Create a dedicated deposit:

1. Go to <https://zenodo.org/uploads/new>
2. Upload your data archive:

```bash
cd my-analysis
# Package only the data needed to reproduce the paper figures
tar -czf my-analysis-data-v1.0.0.tar.gz \
    data/sims/ \
    data/exp_pro/ \
    data/exp_raw/

# Optional: generate a checksum file
sha256sum my-analysis-data-v1.0.0.tar.gz > checksums.sha256
```

3. Fill in Zenodo metadata:
   - **Title**: "Data for: My Analysis Paper Title"
   - **Authors**: same as paper
   - **Description**: what the data is, how it was generated, file format
   - **Keywords**: your field, `reproducibility`, `hdf5`, `python`
   - **License**: CC-BY 4.0 (recommended for open science)
   - **Related identifiers**: link to your code DOI (from Step 1)

4. **Reserve the DOI before publishing** (Zenodo gives it to you upfront — add
   it to your paper before it's accepted)

5. **Publish** — the deposit is now permanently citable

### Step 3 — Update README_DOCKER.md with the real DOI

```bash
# In README_DOCKER.md, replace the placeholder:
sed -i 's/YOUR_ZENODO_ID/12345678/' README_DOCKER.md
sed -i 's/YOUR_GITHUB_USERNAME/your-github-handle/' README_DOCKER.md

git add README_DOCKER.md
git commit -m "docs: add Zenodo DOI and GHCR image URL"
git tag v1.0.0-final
git push origin main --tags
```

---

## Publish the Docker Image

The GitHub Actions workflow (`.github/workflows/docker-publish.yml`) does this
automatically. It:

1. Builds the image on every push to `main`
2. Runs a smoke-test (generates sample data, runs analysis inside the container,
   verifies `plots/` is non-empty)
3. Pushes to GHCR only if the smoke-test passes
4. Tags images as `:latest`, `:SHA`, and `:v1.2.3` on semver tags

**For the first push**, enable GHCR in your repository:
- Go to your GitHub repo → Settings → Packages → make it public

After that, `docker pull ghcr.io/YOUR_USERNAME/my-analysis:latest` works for
anyone.

### Manual image push (optional)

```bash
# Build locally
docker build -t ghcr.io/YOUR_USERNAME/my-analysis:v1.0.0 .

# Log in
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Push
docker push ghcr.io/YOUR_USERNAME/my-analysis:v1.0.0
docker push ghcr.io/YOUR_USERNAME/my-analysis:latest
```

---

## Reader Reproduction Steps

This is what you should document in your README and `README_DOCKER.md`:

```bash
# 1. Pull the image
docker pull ghcr.io/YOUR_USERNAME/my-analysis:v1.0.0

# 2. Download data (replace with real Zenodo URL)
curl -L "https://zenodo.org/records/XXXXXXX/files/my-analysis-data-v1.0.0.tar.gz" \
     -o data.tar.gz
tar -xzf data.tar.gz          # → ./data/sims/ etc.
mkdir -p plots

# 3. Reproduce
docker compose run reproduce  # uses docker-compose.yml

# Plots appear in ./plots/
```

Total time for a reader: ~5 minutes (mostly download time).

---

## Linking Code, Data, and Software

Zenodo supports "related identifiers" to create a web of linked records:

| Record type | Zenodo relation | Example |
|-------------|-----------------|---------|
| Paper → Code | `is_supplement_to` | `10.5281/zenodo.code-doi` |
| Paper → Data | `is_supplement_to` | `10.5281/zenodo.data-doi` |
| Code → Data | `is_documented_by` | `10.5281/zenodo.data-doi` |
| Data → Code | `is_compiled_by` | `10.5281/zenodo.code-doi` |
| Docker image → Code | `is_derived_from` | `10.5281/zenodo.code-doi` |

Add these in the "Related identifiers" section of each Zenodo deposit.

---

## Checklist Before Submitting a Paper

```
□ All scripts run from scratch against the Zenodo data
□ docker compose run reproduce produces all paper figures
□ README_DOCKER.md has correct Zenodo DOI and GHCR URL
□ Zenodo data deposit is PUBLISHED (not draft)
□ Code deposit / GitHub release is tagged and linked
□ DOIs added to paper and README
□ Docker image pushed and publicly accessible
□ Image smoke-test passes in GitHub Actions
□ uv.lock committed (pinned reproducible dependency graph)
□ git log is clean (no "fix typo" commits without messages)
```

---

## Advanced: Bit-Exact Reproducibility

For truly bit-exact reproduction (same random seeds, same OS, same library
patch versions):

```bash
# Pin to an exact image SHA (not :latest)
docker pull ghcr.io/YOUR_USERNAME/my-analysis@sha256:ABCDEF...

# Run with the exact SHA
docker run --rm \
  -v "$PWD/data":/workspace/data:ro \
  -v "$PWD/plots":/workspace/plots \
  ghcr.io/YOUR_USERNAME/my-analysis@sha256:ABCDEF...
```

Record the SHA in your paper supplementary material.
The SHA is printed in the GitHub Actions log and on the GHCR package page.

---

*Generated by [PyWatson](https://github.com/isaac-tes/pywatson) — inspired by
[DrWatson.jl](https://juliadynamics.github.io/DrWatson.jl/stable/).*

#!/bin/bash
# ==========================================================================
# PyWatson - Quick Project Creator
#
# This script provides a convenient interactive wrapper around the
# `drwatson-init` CLI for creating DrWatson-style Python projects.
#
# Usage:
#   ./create-project.sh -i           # Full interactive mode
#   ./create-project.sh my-project   # Quick mode with defaults
#   ./create-project.sh -h           # Show help
# ==========================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
ORIGINAL_CWD="$(pwd)"

echo "PyWatson - Project Creator"
echo "========================================"

# ------------------------------------------------------------------
# Check prerequisites
# ------------------------------------------------------------------
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# ------------------------------------------------------------------
# Interactive project creation
# ------------------------------------------------------------------
create_project_interactive() {
    echo
    read -p "Project name: " project_name

    if [[ -z "$project_name" ]]; then
        echo "Error: Project name cannot be empty"
        exit 1
    fi

    read -p "Author name: " author_name
    read -p "Author email: " author_email
    read -p "Project description: " description
    read -p "Project path (default: current directory): " project_path

    # --- Project type selection ---
    echo
    echo "Select project type:"
    echo "  1) default  - DrWatson.jl standard (data/{sims, exp_raw, exp_pro})"
    echo "  2) minimal  - Lightweight (src, data, scripts, tests)"
    echo "  3) full     - Everything + config/, Makefile, CI, CONTRIBUTING, CHANGELOG"
    echo
    read -p "Project type [1/2/3] (default: 1): " type_choice

    case "${type_choice:-1}" in
        1) project_type="default" ;;
        2) project_type="minimal" ;;
        3) project_type="full" ;;
        *)
            echo "Invalid choice, using 'default'"
            project_type="default"
            ;;
    esac

    # --- License selection ---
    echo
    echo "Select license:"
    echo "  1) MIT"
    echo "  2) BSD-3-Clause"
    echo "  3) Apache-2.0"
    echo "  4) ISC"
    echo
    read -p "License [1/2/3/4] (default: 1): " license_choice

    case "${license_choice:-1}" in
        1) license_type="MIT" ;;
        2) license_type="BSD-3-Clause" ;;
        3) license_type="Apache-2.0" ;;
        4) license_type="ISC" ;;
        *)
            echo "Invalid choice, using 'MIT'"
            license_type="MIT"
            ;;
    esac

    # --- Environment file (optional) ---
    read -p "Environment file (optional, .yml file): " env_file

    if [[ -z "$project_path" ]]; then
        project_path="."
    fi

    # --- Summary ---
    echo
    echo "Creating project with the following settings:"
    echo "  Name:     $project_name"
    echo "  Author:   $author_name <$author_email>"
    echo "  Desc:     $description"
    echo "  Type:     $project_type"
    echo "  License:  $license_type"
    echo "  Path:     $project_path"
    echo

    read -p "Continue? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "Aborted"
        exit 0
    fi

    # Convert relative path to absolute path based on original working directory
    if [[ "$project_path" == "." ]]; then
        project_path="$ORIGINAL_CWD"
    elif [[ "$project_path" != /* ]]; then
        project_path="$ORIGINAL_CWD/$project_path"
    fi

    # Run the command from the script directory but with absolute paths
    cd "$PROJECT_DIR"

    if [[ -n "$env_file" ]]; then
        # Convert env_file to absolute path if relative
        if [[ "$env_file" != /* ]]; then
            env_file="$ORIGINAL_CWD/$env_file"
        fi
        if [[ -f "$env_file" ]]; then
            echo "Using environment file: $env_file"
        else
            echo "Warning: Environment file not found: $env_file"
            echo "Proceeding without environment file..."
            env_file=""
        fi
    fi

    # Build the command
    cmd=(uv run drwatson-init "$project_name"
        --path "$project_path"
        --author-name "$author_name"
        --author-email "$author_email"
        --description "$description"
        --project-type "$project_type"
        --license "$license_type"
    )

    if [[ -n "$env_file" ]]; then
        cmd+=(--env-file "$env_file")
    fi

    "${cmd[@]}"

    echo
    echo "Project created successfully!"
    echo
    echo "Next steps:"
    echo "   cd $project_name"
    echo "   uv sync"
    echo "   uv run pytest"
    echo "   uv run python scripts/generate_data.py"
    if [[ "$project_type" == "full" ]]; then
        echo "   make check    # Run all quality checks"
    fi
}

# ------------------------------------------------------------------
# Usage help
# ------------------------------------------------------------------
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -i, --interactive    Create project interactively (with type & license prompts)"
    echo "  -h, --help           Show this help message"
    echo
    echo "Examples:"
    echo "  $0 -i                              # Interactive mode"
    echo "  $0 my-project                      # Quick mode (default type, MIT license)"
    echo
    echo "For advanced usage, use drwatson-init directly:"
    echo "  uv run drwatson-init --help"
    echo
    echo "Project types:"
    echo "  default   DrWatson.jl standard (data/{sims, exp_raw, exp_pro})"
    echo "  minimal   Lightweight (src, data, scripts, tests)"
    echo "  full      Everything + config/, Makefile, CI, CONTRIBUTING, CHANGELOG"
}

# ------------------------------------------------------------------
# Parse command line arguments
# ------------------------------------------------------------------
case "${1:-}" in
    -i|--interactive)
        create_project_interactive
        ;;
    -h|--help|"")
        show_usage
        ;;
    *)
        # Quick mode - just project name, default type and MIT license
        project_name="$1"
        echo "Creating project '$project_name' with default settings..."
        echo "  Type: default | License: MIT"
        echo "   (Use -i for interactive mode with type & license selection)"
        echo

        cd "$PROJECT_DIR"
        uv run drwatson-init "$project_name" \
            --path "$ORIGINAL_CWD" \
            --author-name "$(git config user.name 2>/dev/null || echo 'Your Name')" \
            --author-email "$(git config user.email 2>/dev/null || echo 'your.email@example.com')" \
            --description "A scientific computing project created with PyWatson" \
            --project-type default \
            --license MIT

        echo
        echo "Project created successfully!"
        echo
        echo "Next steps:"
        echo "   cd $project_name"
        echo "   uv sync"
        echo "   uv run pytest"
        echo "   uv run python scripts/generate_data.py"
        ;;
esac

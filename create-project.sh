#!/bin/bash
# PyScaffold DrWatson - Quick Project Creator
# 
# This script provides a convenient way to create new DrWatson-style Python projects
# without having to remember all the command-line options.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
ORIGINAL_CWD="$(pwd)"

echo "🚀 PyScaffold DrWatson - Project Creator"
echo "========================================"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Function to create a project interactively
create_project_interactive() {
    echo
    read -p "📝 Project name: " project_name
    
    if [[ -z "$project_name" ]]; then
        echo "❌ Project name cannot be empty"
        exit 1
    fi
    
    read -p "👤 Author name: " author_name
    read -p "📧 Author email: " author_email
    read -p "📄 Project description: " description
    read -p "📂 Project path (default: current directory): " project_path
    read -p "🛠️  Environment file (optional, .yml file): " env_file
    
    if [[ -z "$project_path" ]]; then
        project_path="."
    fi
    
    echo
    echo "Creating project with the following settings:"
    echo "  Name: $project_name"
    echo "  Author: $author_name <$author_email>"
    echo "  Description: $description"
    echo "  Path: $project_path"
    echo
    
    read -p "Continue? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        echo "❌ Aborted"
        exit 0
    fi
    
    # Convert relative path to absolute path based on original working directory
    if [[ "$project_path" == "." ]]; then
        project_path="$ORIGINAL_CWD"
    elif [[ "$project_path" != /* ]]; then
        # If it's a relative path, make it absolute from original working directory
        project_path="$ORIGINAL_CWD/$project_path"
    fi
    
    # Run the command from the script directory but with absolute paths
    cd "$PROJECT_DIR"
    
    if [[ -n "$env_file" ]]; then
        # Convert env_file to absolute path if it's relative
        if [[ "$env_file" != /* ]]; then
            env_file="$ORIGINAL_CWD/$env_file"
        fi
        # Check if the absolute path exists
        if [[ -f "$env_file" ]]; then
            echo "Using environment file: $env_file"
        else
            echo "Warning: Environment file not found: $env_file"
            echo "Proceeding without environment file..."
            env_file=""
        fi
    fi
    
    if [[ -n "$env_file" ]]; then
        uv run drwatson-init "$project_name" \
            --path "$project_path" \
            --author-name "$author_name" \
            --author-email "$author_email" \
            --description "$description" \
            --env-file "$env_file"
    else
        uv run drwatson-init "$project_name" \
            --path "$project_path" \
            --author-name "$author_name" \
            --author-email "$author_email" \
            --description "$description"
    fi
    
    echo
    echo "✅ Project created successfully!"
    echo
    echo "🚀 Next steps:"
    echo "   cd $project_name"
    echo "   uv sync"
    echo "   uv run pytest"
    echo "   uv run python scripts/example_analysis.py"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -i, --interactive    Create project interactively"
    echo "  -h, --help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0 -i                              # Interactive mode"
    echo "  $0 my-project                      # Quick mode with project name"
    echo
    echo "For advanced usage, use drwatson-init directly:"
    echo "  uv run drwatson-init --help"
}

# Parse command line arguments
case "${1:-}" in
    -i|--interactive)
        create_project_interactive
        ;;
    -h|--help|"")
        show_usage
        ;;
    *)
        # Quick mode - just project name
        project_name="$1"
        echo "🚀 Creating project '$project_name' with default settings..."
        echo "   (Use -i for interactive mode)"
        echo
        
        cd "$PROJECT_DIR"
        uv run drwatson-init "$project_name" \
            --path "$ORIGINAL_CWD" \
            --author-name "$(git config user.name 2>/dev/null || echo 'Your Name')" \
            --author-email "$(git config user.email 2>/dev/null || echo 'your.email@example.com')" \
            --description "A scientific computing project created with PyScaffold DrWatson"
        
        echo
        echo "✅ Project created successfully!"
        echo
        echo "🚀 Next steps:"
        echo "   cd $project_name"
        echo "   uv sync"
        echo "   uv run pytest"
        echo "   uv run python scripts/example_analysis.py"
        ;;
esac
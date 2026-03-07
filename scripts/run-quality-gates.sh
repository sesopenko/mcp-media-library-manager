#!/usr/bin/env bash
# Shared quality gate runner for mcp-media-library-manager
# Runs the full project quality gate sequence in deterministic order
# Exits with non-zero status if any gate fails

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Running quality gates..."
echo ""

# 1. Code formatting
echo "1/3 Running ruff format..."
uv run ruff format . || exit 1
echo "✓ ruff format passed"
echo ""

# 2. Linting
echo "2/3 Running ruff check..."
uv run ruff check . || exit 1
echo "✓ ruff check passed"
echo ""

# 3. Type checking
echo "3/3 Running mypy..."
uv run mypy src/ || exit 1
echo "✓ mypy passed"
echo ""

echo "All quality gates passed ✓"

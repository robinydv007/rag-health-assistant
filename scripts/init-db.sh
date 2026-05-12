#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

echo "Installing migration dependencies..."
pip install --quiet -r requirements-migrations.txt

echo "Running Alembic migrations..."
alembic upgrade head

echo "Database initialized successfully."

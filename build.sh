#!/usr/bin/env bash
# Render build script for the Athena API backend.
#
# Usage (set as Render "Build Command"):
#   ./build.sh          -- production (core only)
#   ./build.sh --dev    -- dev environment (core + dev-tools plugin)

set -euo pipefail

echo "Installing Athena core..."
pip install -e .

if [ "${1:-}" = "--dev" ]; then
    echo "Installing dev-tools plugin..."
    pip install -e dev_tools/
fi

echo "Build complete."

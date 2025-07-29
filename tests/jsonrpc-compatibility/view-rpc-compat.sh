#!/bin/bash

# Script to run hiveview server for viewing test results
# Usage: ./run-hiveview.sh

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HIVEVIEW_BINARY="hive/hiveview"

echo "🔍 Checking for hiveview binary..."

if [ ! -f "$HIVEVIEW_BINARY" ]; then
    echo "📦 hiveview binary not found, building..."
    cd hive
    go build ./cmd/hiveview
    cd "$SCRIPT_DIR"
    echo "✅ hiveview built successfully"
else
    echo "✅ hiveview binary found"
fi

echo "🌐 Starting hiveview server..."
echo "🔗 View results at: http://localhost:8080"
echo "💡 Press Ctrl+C to stop the server"
echo ""

cd hive
./hiveview --serve
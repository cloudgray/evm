#!/bin/bash

# Script to run Hive JSON-RPC compatibility tests for evmd
# Usage: ./run-hive-tests.sh

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 Step 1: Updating hive submodule..."
git submodule update --init --recursive hive
echo "✅ Hive submodule updated"

echo "🔄 Step 2: Copying evmd client configuration..."
if [ ! -d "evmd-hive-client" ]; then
    echo "❌ Error: evmd-hive-client directory not found!"
    exit 1
fi

# Remove existing evmd client if it exists
rm -rf hive/clients/evmd
# Copy our custom evmd client
cp -r evmd-hive-client hive/clients/evmd
echo "✅ evmd client configuration copied"

echo "🔄 Step 3: Running Hive tests..."
cd hive
echo "Starting tests with high log level (this may take several minutes)..."
./hive --sim=ethereum/rpc-compat-no-engine --client=evmd --sim.loglevel=4
echo "✅ Tests completed"

echo ""
echo "🎉 All tests completed successfully!"
echo "💡 To view results, run: ./run-hiveview.sh"
echo "🔗 Results will be available at: http://localhost:8080"
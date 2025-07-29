#!/bin/bash

# Script to run Hive JSON-RPC compatibility tests for evmd
# Usage: ./run-hive-tests.sh

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔄 Step 1: Updating hive submodule..."
git submodule update --init --recursive hive
echo "✅ Hive submodule updated"

echo "🔄 Step 2: Setting up custom client and simulator..."

# Check required directories exist
if [ ! -d "hive-client-evmd" ]; then
    echo "❌ Error: hive-client-evmd directory not found!"
    exit 1
fi

if [ ! -d "rpc-compat-evmd" ]; then
    echo "❌ Error: rpc-compat-evmd directory not found!"
    exit 1
fi

# Clean up any existing custom components
rm -rf hive/clients/evmd
rm -rf hive/simulators/ethereum/rpc-compat-no-engine

# Copy our custom evmd client and simulator
cp -r hive-client-evmd hive/clients/evmd
cp -r rpc-compat-evmd hive/simulators/ethereum/rpc-compat-no-engine
echo "✅ Custom client and simulator copied"

echo "🔄 Step 3: Running Hive tests..."
cd hive
echo "Starting tests with high log level (this may take several minutes)..."
./hive --sim=ethereum/rpc-compat-no-engine --client=evmd --sim.loglevel=4
TEST_EXIT_CODE=$?
cd "$SCRIPT_DIR"

echo "🔄 Step 4: Cleaning up custom components..."
rm -rf hive/clients/evmd
rm -rf hive/simulators/ethereum/rpc-compat-no-engine
echo "✅ Cleanup completed"

if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
    exit $TEST_EXIT_CODE
fi

echo ""
echo "🎉 All tests completed successfully!"
echo "💡 To view results, run: ./view-rpc-compat.sh"
echo "🔗 Results will be available at: http://localhost:8080"
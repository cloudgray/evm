#!/bin/bash
# This script extracts the enode URL from a running evmd client.
# For evmd (Cosmos-based), this is a placeholder as it doesn't use traditional Ethereum P2P
# Instead, it returns a mock enode URL

# Get the node ID (mock implementation)
NODE_ID="0x$(openssl rand -hex 64)"

# Return a mock enode URL
echo "enode://${NODE_ID}@$(hostname -i):30303"
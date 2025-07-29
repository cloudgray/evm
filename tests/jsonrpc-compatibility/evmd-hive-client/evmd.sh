#!/bin/bash

# evmd startup script for hive testing - Fixed state mode  
# Follow local_node.sh approach then add hive accounts

set -e

evmd=/usr/local/bin/evmd
KEYRING="test"
KEYALGO="eth_secp256k1"
HOMEDIR="/tmp/evmd"
MONIKER="hive-evmd"

# Clean start
rm -rf "$HOMEDIR"

# Extract chain ID from hive genesis if provided
if [ -f /genesis.json ]; then
    CHAINID=$(jq -r '.config.chainId' /genesis.json)
    echo "Using chain ID from hive genesis: $CHAINID"
else
    echo "No hive genesis found, using test suite default"
    CHAINID="3503995874084926"
fi

echo "Setting up evmd following local_node.sh approach..."

# Set client config
$evmd config set client chain-id "$CHAINID" --home "$HOMEDIR"
$evmd config set client keyring-backend "$KEYRING" --home "$HOMEDIR"

# Use the same validator key from local_node.sh for consistency
VAL_KEY="mykey"
VAL_MNEMONIC="gesture inject test cycle original hollow east ridge hen combine junk child bacon zero hope comfort vacuum milk pitch cage oppose unhappy lunar seat"

# Import validator key
echo "$VAL_MNEMONIC" | $evmd keys add "$VAL_KEY" --recover --keyring-backend "$KEYRING" --algo "$KEYALGO" --home "$HOMEDIR"

# Initialize chain
$evmd init $MONIKER -o --chain-id "$CHAINID" --home "$HOMEDIR"

# Apply local_node.sh configurations
GENESIS="$HOMEDIR/config/genesis.json"
TMP_GENESIS="$HOMEDIR/config/tmp_genesis.json"

echo "Applying local_node.sh configurations..."

# Change parameter token denominations to atest (exactly like local_node.sh)
jq '.app_state["staking"]["params"]["bond_denom"]="atest"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"
jq '.app_state["gov"]["deposit_params"]["min_deposit"][0]["denom"]="atest"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"
jq '.app_state["gov"]["params"]["min_deposit"][0]["denom"]="atest"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"
jq '.app_state["gov"]["params"]["expedited_min_deposit"][0]["denom"]="atest"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"
jq '.app_state["evm"]["params"]["evm_denom"]="atest"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"
jq '.app_state["mint"]["params"]["mint_denom"]="atest"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"

# Add token metadata
jq '.app_state["bank"]["denom_metadata"]=[{"description":"The native staking token for evmd.","denom_units":[{"denom":"atest","exponent":0,"aliases":["attotest"]},{"denom":"test","exponent":18,"aliases":[]}],"base":"atest","display":"test","name":"Test Token","symbol":"TEST","uri":"","uri_hash":""}]' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"

# Enable precompiles
jq '.app_state["evm"]["params"]["active_static_precompiles"]=["0x0000000000000000000000000000000000000100","0x0000000000000000000000000000000000000400","0x0000000000000000000000000000000000000800","0x0000000000000000000000000000000000000801","0x0000000000000000000000000000000000000802","0x0000000000000000000000000000000000000803","0x0000000000000000000000000000000000000804","0x0000000000000000000000000000000000000805", "0x0000000000000000000000000000000000000806", "0x0000000000000000000000000000000000000807"]' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"

# Enable native denomination as token pair  
jq '.app_state.erc20.params.native_precompiles=["0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"]' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"
jq '.app_state.erc20.token_pairs=[{contract_owner:1,erc20_address:"0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",denom:"atest",enabled:true}]' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"

# Set gas limit
jq '.consensus.params.block.max_gas="10000000"' "$GENESIS" >"$TMP_GENESIS" && mv "$TMP_GENESIS" "$GENESIS"

# Apply configuration changes from local_node.sh for proper setup
CONFIG="$HOMEDIR/config/config.toml"
APP_TOML="$HOMEDIR/config/app.toml"

# Enable prometheus metrics and all APIs (like local_node.sh)
sed -i.bak 's/prometheus = false/prometheus = true/' "$CONFIG"
sed -i.bak 's/prometheus-retention-time  = "0"/prometheus-retention-time  = "1000000000000"/g' "$APP_TOML"
sed -i.bak 's/enabled = false/enabled = true/g' "$APP_TOML"
sed -i.bak 's/enable = false/enable = true/g' "$APP_TOML"

# Change proposal periods for faster testing (like local_node.sh)
sed -i.bak 's/"max_deposit_period": "172800s"/"max_deposit_period": "30s"/g' "$GENESIS"
sed -i.bak 's/"voting_period": "172800s"/"voting_period": "30s"/g' "$GENESIS"
sed -i.bak 's/"expedited_voting_period": "86400s"/"expedited_voting_period": "15s"/g' "$GENESIS"

# Set custom pruning settings (like local_node.sh)
sed -i.bak 's/pruning = "default"/pruning = "custom"/g' "$APP_TOML"
sed -i.bak 's/pruning-keep-recent = "0"/pruning-keep-recent = "2"/g' "$APP_TOML"
sed -i.bak 's/pruning-interval = "0"/pruning-interval = "10"/g' "$APP_TOML"

# Add validator account with large balance
$evmd genesis add-genesis-account "$VAL_KEY" 100000000000000000000000000atest --keyring-backend "$KEYRING" --home "$HOMEDIR"

# Generate validator transaction
$evmd genesis gentx "$VAL_KEY" 1000000000000000000000atest --gas-prices 10000000atest --keyring-backend "$KEYRING" --chain-id "$CHAINID" --home "$HOMEDIR"

# Collect genesis transactions  
$evmd genesis collect-gentxs --home "$HOMEDIR"

# Now add hive accounts if provided
if [ -f /genesis.json ]; then
    echo "Adding hive accounts to genesis..."
    python3 /add_hive_accounts.py "$GENESIS" /genesis.json "$GENESIS"
fi

# Validate final genesis
echo "Validating final genesis..."
$evmd genesis validate-genesis --home "$HOMEDIR"

# Set log level
LOG_LEVEL="info"
if [ "$HIVE_LOGLEVEL" != "" ]; then
    case $HIVE_LOGLEVEL in
        0) LOG_LEVEL="error" ;;
        1) LOG_LEVEL="warn" ;;
        2) LOG_LEVEL="info" ;;
        3) LOG_LEVEL="info" ;;
        4) LOG_LEVEL="debug" ;;
        5) LOG_LEVEL="debug" ;;
        *) LOG_LEVEL="info" ;;
    esac
fi

echo "Starting evmd node..."

# Start the node in background
$evmd start \
    --log_level $LOG_LEVEL \
    --minimum-gas-prices=0.0001atest \
    --home "$HOMEDIR" \
    --json-rpc.api eth,txpool,personal,net,debug,web3 \
    --json-rpc.enable=true \
    --json-rpc.address=0.0.0.0:8545 \
    --json-rpc.ws-address=0.0.0.0:8546 \
    --chain-id "$CHAINID" &

NODE_PID=$!

echo "Waiting for evmd to commit first block..."

# Wait for the first block to be committed
MAX_WAIT=30
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 3
    WAIT_COUNT=$((WAIT_COUNT + 1))
    
    # Check if the JSON-RPC endpoint is responding and has committed at least one block
    if curl -s -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        http://localhost:8545 > /tmp/rpc_response.json 2>/dev/null; then
        
        # Check if we got a valid response (not an error)
        if grep -q '"result"' /tmp/rpc_response.json && ! grep -q 'evmd is not ready' /tmp/rpc_response.json; then
            CURRENT_HEIGHT=$(jq -r '.result' /tmp/rpc_response.json 2>/dev/null)
            if [ "$CURRENT_HEIGHT" != "null" ] && [ "$CURRENT_HEIGHT" != "" ]; then
                CURRENT_HEIGHT_DEC=$(printf "%d" "$CURRENT_HEIGHT" 2>/dev/null || echo "0")
                echo "evmd has committed first block at height: $CURRENT_HEIGHT_DEC"
                echo "evmd is ready for tests!"
                break
            fi
        fi
    fi
    
    # If we're still getting "not ready" errors, try to trigger block production
    # by sending a simple transaction to force consensus
    if [ $WAIT_COUNT -eq 5 ]; then
        echo "Attempting to trigger first block by sending a transaction..."
        # Send a minimal transaction to trigger block production
        $evmd tx bank send "$VAL_KEY" "cosmos10jmp6sgh4cc6zt3e8gw05wavvejgr5pwsjskvv" 1atest \
            --keyring-backend "$KEYRING" --chain-id "$CHAINID" --home "$HOMEDIR" \
            --gas-prices 0.0001atest --gas auto --gas-adjustment 1.5 --yes \
            --broadcast-mode sync > /dev/null 2>&1 || true
    fi
    
    echo "Still waiting for first block... ($WAIT_COUNT/$MAX_WAIT)"
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo "Warning: evmd may not have committed first block within timeout"
    echo "Proceeding anyway..."
fi

# Keep the node running
echo "evmd is ready, keeping node running..."
wait $NODE_PID
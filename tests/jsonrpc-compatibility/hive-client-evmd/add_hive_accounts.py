#!/usr/bin/env python3
"""
Add hive accounts to an existing genesis.json created by local_node.sh approach
"""
import json
import sys

# Bech32 encoding implementation
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_CONST = 1

def bech32_polymod(values):
    generator = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            chk ^= generator[i] if ((top >> i) & 1) else 0
    return chk

def bech32_hrp_expand(hrp):
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

def bech32_create_checksum(hrp, data):
    values = bech32_hrp_expand(hrp) + data
    polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ BECH32_CONST
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

def bech32_encode(hrp, data):
    checksum = bech32_create_checksum(hrp, data)
    combined = data + checksum
    return hrp + '1' + ''.join([CHARSET[d] for d in combined])

def convertbits(data, frombits, tobits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret

def eth_to_cosmos_address(eth_addr):
    """Convert 0x-prefixed Ethereum address to cosmos format (same but no 0x)"""
    return eth_addr.lower().replace('0x', '')

def eth_to_cosmos_bech32_address(eth_addr):
    """Convert Ethereum address to proper cosmos bech32 address"""
    # Remove 0x prefix and convert to bytes
    clean_addr = eth_addr.lower().replace('0x', '')
    addr_bytes = bytes.fromhex(clean_addr)
    
    # Convert to 5-bit groups for bech32 encoding
    five_bit_data = convertbits(addr_bytes, 8, 5)
    if five_bit_data is None:
        raise ValueError(f"Failed to convert address {eth_addr}")
    
    # Encode with cosmos prefix
    return bech32_encode("cosmos", five_bit_data)

def hex_to_int(hex_str):
    """Convert hex string to integer"""
    if hex_str.startswith('0x'):
        return int(hex_str, 16)
    return int(hex_str)

def add_hive_accounts(genesis_path, eth_genesis_path, output_path):
    """Add hive accounts to existing genesis"""
    
    # Load existing genesis (created by local_node.sh approach)
    with open(genesis_path, 'r') as f:
        genesis = json.load(f)
    
    # Load ethereum genesis for accounts
    with open(eth_genesis_path, 'r') as f:
        eth_genesis = json.load(f)
    
    alloc = eth_genesis.get('alloc', {})
    
    print(f"Adding {len(alloc)} hive accounts to existing genesis...")
    
    # Track current account numbers and total supply
    current_account_number = len(genesis['app_state']['auth']['accounts'])
    current_supply = 0
    if genesis['app_state']['bank']['supply']:
        current_supply = int(genesis['app_state']['bank']['supply'][0]['amount'])
    
    # Process each ethereum account
    for eth_addr, account_data in alloc.items():
        print(f"  Adding {eth_addr}")
        
        # Clean address (remove 0x)
        clean_addr = eth_to_cosmos_address(eth_addr)
        
        # Get balance (convert from hex)
        balance_wei = hex_to_int(account_data.get('balance', '0x0'))
        balance_str = str(balance_wei)
        current_supply += balance_wei
        
        # Convert storage from Ethereum map format to evmd array format
        storage_map = account_data.get('storage', {})
        storage_array = []
        for key, value in storage_map.items():
            # Remove 0x prefix from both key and value
            clean_key = key.replace('0x', '') if key.startswith('0x') else key  
            clean_value = value.replace('0x', '') if value.startswith('0x') else value
            storage_array.append({
                "key": clean_key,
                "value": clean_value
            })
        
        # Create EVM account with correct storage format
        evm_account = {
            "address": clean_addr,
            "code": account_data.get('code', '').replace('0x', '') if account_data.get('code', '').startswith('0x') else account_data.get('code', ''),
            "storage": storage_array
        }
        genesis['app_state']['evm']['accounts'].append(evm_account)
        
        # Convert to cosmos bech32 address for auth account
        cosmos_addr = eth_to_cosmos_bech32_address(eth_addr)
        
        # Create auth account with proper cosmos bech32 address
        auth_account = {
            "@type": "/cosmos.auth.v1beta1.BaseAccount",
            "address": cosmos_addr,
            "pub_key": None,
            "account_number": str(current_account_number),
            "sequence": "0"
        }
        genesis['app_state']['auth']['accounts'].append(auth_account)
        current_account_number += 1
        
        # Create bank balance for accounts with balance
        if balance_wei > 0:
            bank_balance = {
                "address": cosmos_addr,
                "coins": [{"denom": "atest", "amount": balance_str}]
            }
            genesis['app_state']['bank']['balances'].append(bank_balance)
    
    # Update total supply
    genesis['app_state']['bank']['supply'] = [
        {"denom": "atest", "amount": str(current_supply)}
    ]
    
    # Write updated genesis
    with open(output_path, 'w') as f:
        json.dump(genesis, f, indent=2)
    
    print(f"✅ Updated genesis saved to {output_path}")
    print(f"   Added {len(alloc)} hive accounts")
    print(f"   Total accounts: {len(genesis['app_state']['auth']['accounts'])}")
    print(f"   Total supply: {current_supply} atest")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 add_hive_accounts.py <existing_genesis.json> <ethereum_genesis.json> <output_genesis.json>")
        sys.exit(1)
    
    add_hive_accounts(sys.argv[1], sys.argv[2], sys.argv[3])
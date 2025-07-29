#!/usr/bin/env python3
"""
Convert Ethereum genesis.json to Cosmos SDK format for evmd
"""
import json
import sys
import hashlib
from datetime import datetime

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

def bech32_verify_checksum(hrp, data):
    return bech32_polymod(bech32_hrp_expand(hrp) + data) == BECH32_CONST

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

def convert_genesis(eth_genesis_path, output_path):
    """Convert Ethereum genesis to Cosmos SDK format following local_node.sh approach"""
    
    with open(eth_genesis_path, 'r') as f:
        eth_genesis = json.load(f)
    
    # Extract values from Ethereum genesis
    chain_id = str(eth_genesis['config']['chainId'])
    alloc = eth_genesis.get('alloc', {})
    
    print(f"Creating base genesis using evmd init...")
    
    # First, create a base genesis using evmd init (like local_node.sh does)
    # This will be created with proper validator setup
    
    # For now, create the structure manually but following local_node.sh patterns
    cosmos_genesis = {
        "app_name": "<appd>",
        "app_version": "",
        "genesis_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "chain_id": chain_id,
        "initial_height": 1,
        "app_hash": None,
        "app_state": {
            "07-tendermint": None,
            "auth": {
                "params": {
                    "max_memo_characters": "256",
                    "tx_sig_limit": "7",
                    "tx_size_cost_per_byte": "10",
                    "sig_verify_cost_ed25519": "590",
                    "sig_verify_cost_secp256k1": "1000"
                },
                "accounts": []
            },
            "authz": {"authorization": []},
            "bank": {
                "params": {
                    "send_enabled": [],
                    "default_send_enabled": True
                },
                "balances": [],
                "supply": [],
                "denom_metadata": [{
                    "description": "The native staking token for evmd.",
                    "denom_units": [
                        {"denom": "atest", "exponent": 0, "aliases": ["attotest"]},
                        {"denom": "test", "exponent": 18, "aliases": []}
                    ],
                    "base": "atest",
                    "display": "test",
                    "name": "Test Token",
                    "symbol": "TEST",
                    "uri": "",
                    "uri_hash": ""
                }],
                "send_enabled": []
            },
            "consensus": None,
            "distribution": {
                "params": {
                    "community_tax": "0.020000000000000000",
                    "base_proposer_reward": "0.000000000000000000",
                    "bonus_proposer_reward": "0.000000000000000000",
                    "withdraw_addr_enabled": True
                },
                "fee_pool": {"community_pool": []},
                "delegator_withdraw_infos": [],
                "previous_proposer": "",
                "outstanding_rewards": [],
                "validator_accumulated_commissions": [],
                "validator_historical_rewards": [],
                "validator_current_rewards": [],
                "delegator_starting_infos": [],
                "validator_slash_events": []
            },
            "erc20": {
                "params": {
                    "enable_erc20": True,
                    "native_precompiles": ["0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"],
                    "dynamic_precompiles": [],
                    "permissionless_registration": True
                },
                "token_pairs": [{
                    "contract_owner": 1,
                    "erc20_address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                    "denom": "atest",
                    "enabled": True
                }],
                "allowances": []
            },
            "evidence": {"evidence": []},
            "evm": {
                "accounts": [],
                "params": {
                    "evm_denom": "atest",
                    "extra_eips": [],
                    "allow_unprotected_txs": False,
                    "evm_channels": [],
                    "access_control": {
                        "create": {
                            "access_type": "ACCESS_TYPE_PERMISSIONLESS",
                            "access_control_list": []
                        },
                        "call": {
                            "access_type": "ACCESS_TYPE_PERMISSIONLESS", 
                            "access_control_list": []
                        }
                    },
                    "active_static_precompiles": [
                        "0x0000000000000000000000000000000000000100",
                        "0x0000000000000000000000000000000000000400",
                        "0x0000000000000000000000000000000000000800",
                        "0x0000000000000000000000000000000000000801",
                        "0x0000000000000000000000000000000000000802",
                        "0x0000000000000000000000000000000000000803",
                        "0x0000000000000000000000000000000000000804",
                        "0x0000000000000000000000000000000000000805",
                        "0x0000000000000000000000000000000000000806",
                        "0x0000000000000000000000000000000000000807"
                    ]
                },
                "preinstalls": []
            },
            "feegrant": {"allowances": []},
            "feemarket": {
                "params": {
                    "no_base_fee": False,
                    "base_fee_change_denominator": 8,
                    "elasticity_multiplier": 2,
                    "enable_height": "0",
                    "base_fee": "1000000000.000000000000000000",
                    "min_gas_price": "0.000000000000000000",
                    "min_gas_multiplier": "0.500000000000000000"
                },
                "block_gas": "0"
            },
            "genutil": {"gen_txs": []},
            "gov": {
                "starting_proposal_id": "1",
                "deposits": [],
                "votes": [],
                "proposals": [],
                "deposit_params": None,
                "voting_params": None,
                "tally_params": None,
                "params": {
                    "min_deposit": [{"denom": "atest", "amount": "10000000"}],
                    "max_deposit_period": "172800s",
                    "voting_period": "172800s",
                    "quorum": "0.334000000000000000",
                    "threshold": "0.500000000000000000",
                    "veto_threshold": "0.334000000000000000",
                    "min_initial_deposit_ratio": "0.000000000000000000",
                    "proposal_cancel_ratio": "0.500000000000000000",
                    "proposal_cancel_dest": "",
                    "expedited_voting_period": "86400s",
                    "expedited_threshold": "0.667000000000000000",
                    "expedited_min_deposit": [{"denom": "atest", "amount": "50000000"}],
                    "burn_vote_quorum": False,
                    "burn_proposal_deposit_prevote": False,
                    "burn_vote_veto": True,
                    "min_deposit_ratio": "0.010000000000000000"
                },
                "constitution": ""
            },
            "ibc": {
                "client_genesis": {
                    "clients": [],
                    "clients_consensus": [],
                    "clients_metadata": [],
                    "params": {"allowed_clients": ["*"]},
                    "create_localhost": False,
                    "next_client_sequence": "0"
                },
                "connection_genesis": {
                    "connections": [],
                    "client_connection_paths": [],
                    "next_connection_sequence": "0",
                    "params": {"max_expected_time_per_block": "30000000000"}
                },
                "channel_genesis": {
                    "channels": [],
                    "acknowledgements": [],
                    "commitments": [],
                    "receipts": [],
                    "send_sequences": [],
                    "recv_sequences": [],
                    "ack_sequences": [],
                    "next_channel_sequence": "0"
                },
                "client_v2_genesis": {"counterparty_infos": []},
                "channel_v2_genesis": {
                    "acknowledgements": [],
                    "commitments": [],
                    "receipts": [],
                    "async_packets": [],
                    "send_sequences": []
                }
            },
            "mint": {
                "minter": {
                    "inflation": "0.130000000000000000",
                    "annual_provisions": "0.000000000000000000"
                },
                "params": {
                    "mint_denom": "atest",
                    "inflation_rate_change": "0.130000000000000000",
                    "inflation_max": "0.200000000000000000",
                    "inflation_min": "0.070000000000000000",
                    "goal_bonded": "0.670000000000000000",
                    "blocks_per_year": "6311520"
                }
            },
            "precisebank": {
                "balances": [],
                "remainder": "0"
            },
            "slashing": {
                "params": {
                    "signed_blocks_window": "100",
                    "min_signed_per_window": "0.500000000000000000",
                    "downtime_jail_duration": "600s",
                    "slash_fraction_double_sign": "0.050000000000000000",
                    "slash_fraction_downtime": "0.010000000000000000"
                },
                "signing_infos": [],
                "missed_blocks": []
            },
            "staking": {
                "params": {
                    "unbonding_time": "1814400s",
                    "max_validators": 100,
                    "max_entries": 7,
                    "historical_entries": 10000,
                    "bond_denom": "atest",
                    "min_commission_rate": "0.000000000000000000"
                },
                "last_total_power": "0",
                "last_validator_powers": [],
                "validators": [],
                "delegations": [],
                "unbonding_delegations": [],
                "redelegations": [],
                "exported": False
            },
            "transfer": {
                "port_id": "transfer",
                "denoms": [],
                "params": {"send_enabled": True, "receive_enabled": True},
                "total_escrowed": []
            },
            "upgrade": {},
            "vesting": {}
        },
        "consensus": {
            "params": {
                "block": {"max_bytes": "22020096", "max_gas": "10000000"},
                "evidence": {
                    "max_age_num_blocks": "100000",
                    "max_age_duration": "172800000000000",
                    "max_bytes": "1048576"
                },
                "validator": {"pub_key_types": ["ed25519"]},
                "version": {"app": "0"},
                "abci": {"vote_extensions_enable_height": "0"}
            }
        }
    }
    
    # Convert Ethereum alloc to Cosmos format
    evm_accounts = []
    auth_accounts = []
    bank_balances = []
    total_supply = 0
    
    print(f"Processing {len(alloc)} accounts from Ethereum genesis...")
    
    for eth_addr, account_data in alloc.items():
        # Clean address (remove 0x)
        clean_addr = eth_to_cosmos_address(eth_addr)
        
        # Get balance (convert from hex)
        balance_wei = hex_to_int(account_data.get('balance', '0x0'))
        balance_str = str(balance_wei)
        total_supply += balance_wei
        
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
        evm_accounts.append(evm_account)
        
        # Convert to cosmos bech32 address for auth account
        cosmos_addr = eth_to_cosmos_bech32_address(eth_addr)
        print(f"  ETH address {eth_addr} -> cosmos {cosmos_addr}")
        
        # Create auth account with proper cosmos bech32 address
        auth_account = {
            "@type": "/cosmos.auth.v1beta1.BaseAccount",
            "address": cosmos_addr,
            "pub_key": None,
            "account_number": str(len(auth_accounts)),
            "sequence": "0"
        }
        auth_accounts.append(auth_account)
        
        # Create bank balance for accounts with balance
        if balance_wei > 0:
            bank_balance = {
                "address": cosmos_addr,
                "coins": [{"denom": "atest", "amount": balance_str}]
            }
            bank_balances.append(bank_balance)
    
    # Add minimal validator setup with properly sized ed25519 pubkey
    print("Adding minimal validator setup...")
    
    # Create a proper validator address using cosmos address format
    validator_hex = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"  # 20 bytes = 40 hex chars
    validator_bytes = bytes.fromhex(validator_hex)
    validator_5bit = convertbits(validator_bytes, 8, 5)
    validator_address = bech32_encode("cosmos", validator_5bit)
    validator_valoper_address = bech32_encode("cosmosvaloper", validator_5bit)
    validator_tokens = "1000000000000000000000"  # 1000 tokens with 18 decimals
    
    print(f"  Validator address: {validator_address}")
    print(f"  Validator operator: {validator_valoper_address}")
    
    # Add validator account
    validator_account = {
        "@type": "/cosmos.auth.v1beta1.BaseAccount",
        "address": validator_address,
        "pub_key": None,
        "account_number": str(len(auth_accounts)),
        "sequence": "0"
    }
    auth_accounts.append(validator_account)
    
    # Add validator balance (for fees, etc - not the staked amount)
    validator_balance = {
        "address": validator_address,
        "coins": [{"denom": "atest", "amount": "1000000000000000000"}]  # 1 token for fees
    }
    bank_balances.append(validator_balance)
    
    # Add bonded pool module account to hold the staked tokens
    bonded_pool_addr = "cosmos1fl48vsnmsdzcv85q5d2q4z5ajdha8yu34mf0eh"  # standard bonded pool address
    bonded_pool_account = {
        "@type": "/cosmos.auth.v1beta1.ModuleAccount",
        "base_account": {
            "@type": "/cosmos.auth.v1beta1.BaseAccount",
            "address": bonded_pool_addr,
            "pub_key": None,
            "account_number": str(len(auth_accounts)),
            "sequence": "0"
        },
        "name": "bonded_tokens_pool",
        "permissions": ["burner", "staking"]
    }
    auth_accounts.append(bonded_pool_account)
    
    # Add bonded pool balance (holds the actual staked tokens)
    bonded_pool_balance = {
        "address": bonded_pool_addr,
        "coins": [{"denom": "atest", "amount": validator_tokens}]
    }
    bank_balances.append(bonded_pool_balance)
    
    # Update total supply (validator balance + bonded pool balance)
    total_supply += int(validator_tokens) + 1000000000000000000
    
    # Create a proper 32-byte ed25519 public key (base64 encoded)
    # This is a dummy key but has the correct size (32 bytes = 44 chars in base64)
    import base64
    dummy_pubkey_bytes = bytes([0] * 32)  # 32 zero bytes
    dummy_pubkey_b64 = base64.b64encode(dummy_pubkey_bytes).decode('ascii')
    
    # Add validator to staking module
    validator = {
        "operator_address": validator_valoper_address,
        "consensus_pubkey": {
            "@type": "/cosmos.crypto.ed25519.PubKey",
            "key": dummy_pubkey_b64
        },
        "jailed": False,
        "status": "BOND_STATUS_BONDED",
        "tokens": validator_tokens,
        "delegator_shares": validator_tokens + ".000000000000000000",
        "description": {
            "moniker": "hive-validator",
            "identity": "",
            "website": "",
            "security_contact": "",
            "details": ""
        },
        "unbonding_height": "0",
        "unbonding_time": "1970-01-01T00:00:00Z",
        "commission": {
            "commission_rates": {
                "rate": "0.100000000000000000",
                "max_rate": "0.200000000000000000",
                "max_change_rate": "0.010000000000000000"
            },
            "update_time": "1970-01-01T00:00:00Z"
        },
        "min_self_delegation": "1"
    }
    
    # Add delegation
    delegation = {
        "delegator_address": validator_address,
        "validator_address": validator_valoper_address,
        "shares": validator_tokens + ".000000000000000000"
    }
    
    # Add validator power entry
    validator_power = {
        "address": validator_valoper_address,
        "power": "1000"  # voting power = tokens / 10^18
    }
    
    # Add to genesis
    cosmos_genesis['app_state']['evm']['accounts'] = evm_accounts
    cosmos_genesis['app_state']['auth']['accounts'] = auth_accounts
    cosmos_genesis['app_state']['bank']['balances'] = bank_balances
    cosmos_genesis['app_state']['bank']['supply'] = [
        {"denom": "atest", "amount": str(total_supply)}
    ]
    
    # Add staking data
    cosmos_genesis['app_state']['staking']['validators'] = [validator]
    cosmos_genesis['app_state']['staking']['delegations'] = [delegation]
    cosmos_genesis['app_state']['staking']['last_validator_powers'] = [validator_power]
    cosmos_genesis['app_state']['staking']['last_total_power'] = "1000"
    
    # No genesis transactions needed - validator is set up directly in state
    
    # Write converted genesis
    with open(output_path, 'w') as f:
        json.dump(cosmos_genesis, f, indent=2)
    
    print(f"✅ Converted genesis saved to {output_path}")
    print(f"   Chain ID: {chain_id}")
    print(f"   EVM Accounts: {len(evm_accounts)}")
    print(f"   Auth Accounts: {len(auth_accounts)} (including validator)")
    print(f"   Validator: {validator_address}")
    print(f"   Total Supply: {total_supply} atest")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 genesis_converter.py <ethereum_genesis.json> <output_cosmos_genesis.json>")
        sys.exit(1)
    
    convert_genesis(sys.argv[1], sys.argv[2])
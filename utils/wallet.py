# ═══════════════════════════════════════════════════════════════════════════════
# TEMPO BOT v2.0.1 - WALLET UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

import os
import json
from datetime import datetime
from web3 import Web3
from config import ERC20_ABI

def get_private_keys():
    """Load private keys from pv.txt"""
    try:
        with open('pv.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        keys = [line.strip() for line in content.split('\n')
                if line.strip() and not line.strip().startswith('#')]
        return keys
    except Exception as error:
        print(f'\033[1m\033[31mError reading pv.txt: {error}\033[0m')
        return []

def get_token_balance(web3, wallet_address: str, token_address: str):
    """Get token balance"""
    try:
        contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        decimals = contract.functions.decimals().call()
        formatted = balance / (10 ** decimals)
        return {'balance': balance, 'decimals': decimals, 'formatted': formatted}
    except Exception:
        return {'balance': 0, 'decimals': 18, 'formatted': '0'}

# ============ CREATED TOKENS STORAGE ============
# Resolve absolute path to created_tokens.json relative to project root
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)  # Go one level up (from utils to root)
TOKENS_FILE = os.path.join(_project_root, 'data', 'created_tokens.json')

if __name__ != '__main__':
    pass


def load_created_tokens():
    """Load created tokens and normalize addresses to checksum format"""
    try:
        data_dir = os.path.dirname(TOKENS_FILE)
        os.makedirs(data_dir, exist_ok=True)
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                normalized_data = {}
                for wallet_addr, tokens_list in data.items():
                    try:
                        normalized_wallet = Web3.to_checksum_address(wallet_addr)
                        normalized_tokens = []
                        for token_info in tokens_list:
                            normalized_token_info = token_info.copy()
                            if 'token' in normalized_token_info:
                                try:
                                    normalized_token_info['token'] = Web3.to_checksum_address(normalized_token_info['token'])
                                except Exception:
                                    pass
                            normalized_tokens.append(normalized_token_info)
                        if normalized_wallet in normalized_data:
                            normalized_data[normalized_wallet].extend(normalized_tokens)
                        else:
                            normalized_data[normalized_wallet] = normalized_tokens
                    except Exception as e:
                        print(f"\033[1m\033[33mWarning: failed to checksum wallet {wallet_addr}: {e}\033[0m")
                        continue
                if normalized_data != data:
                    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(normalized_data, f, indent=2, ensure_ascii=False)
                return normalized_data
    except Exception as e:
        try:
            data_dir = os.path.dirname(TOKENS_FILE)
            os.makedirs(data_dir, exist_ok=True)
            if os.path.exists(TOKENS_FILE):
                with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
    return {}

def save_created_token(wallet_address: str, token_address: str, symbol: str):
    """Save a created token (addresses normalized to checksum format)"""
    try:
        normalized_wallet = Web3.to_checksum_address(wallet_address)
        normalized_token = Web3.to_checksum_address(token_address)

        tokens = load_created_tokens()
        if normalized_wallet not in tokens:
            tokens[normalized_wallet] = []

        token_exists = False
        for existing_token in tokens[normalized_wallet]:
            if existing_token.get('token', '').lower() == normalized_token.lower():
                token_exists = True
                break

        if not token_exists:
            tokens[normalized_wallet].append({
                'token': normalized_token,
                'symbol': symbol,
                'createdAt': datetime.now().isoformat()
            })

            data_dir = os.path.dirname(TOKENS_FILE)
            os.makedirs(data_dir, exist_ok=True)

            with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)
        else:
            print(f"\033[1m\033[33m⚠️ Token {symbol} already exists for this wallet\033[0m")
    except Exception as e:
        print(f"\033[1m\033[31m✗ Error saving token: {e}\033[0m")
        import traceback
        print(f"\033[1m\033[31mDetails: {traceback.format_exc()}\033[0m")
        raise

def get_tokens_for_wallet(wallet_address: str):
    """Get tokens for a wallet (address normalized to checksum)"""
    tokens = load_created_tokens()
    normalized_wallet = Web3.to_checksum_address(wallet_address)
    return tokens.get(normalized_wallet, [])


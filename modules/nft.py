# ═══════════════════════════════════════════════════════════════════════════════
# NFT MODULE - [14]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import random
import string
from web3 import Web3
from eth_account import Account
from solcx import compile_source, set_solc_version
from config import CONFIG, COLORS
from utils.helpers import async_sleep, short_hash, wait_for_tx_with_retry, countdown, get_random_int
from utils.wallet import get_private_keys, get_token_balance
from utils.statistics import WalletStatistics
from config import SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI

def get_nft_contract_source(name, symbol):
    """Get NFT contract source code"""
    clean_symbol = ''.join(c for c in symbol if c.isalnum())
    return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {clean_symbol}NFT {{
    string public name = "{name}";
    string public symbol = "{symbol}";

    uint256 private _tokenIdCounter;
    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => string) private _tokenColors;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);

    function totalSupply() public view returns (uint256) {{ return _tokenIdCounter; }}
    function balanceOf(address owner) public view returns (uint256) {{ return _balances[owner]; }}
    function ownerOf(uint256 tokenId) public view returns (address) {{ return _owners[tokenId]; }}

    function mint(address to, string memory color) public returns (uint256) {{
        uint256 tokenId = _tokenIdCounter++;
        _owners[tokenId] = to;
        _balances[to]++;
        _tokenColors[tokenId] = color;
        emit Transfer(address(0), to, tokenId);
        return tokenId;
    }}

    function tokenURI(uint256 tokenId) public view returns (string memory) {{
        require(_owners[tokenId] != address(0), "Token does not exist");
        return string(abi.encodePacked("data:application/json,{{name:", _toString(tokenId), "}}"));
    }}

    function _toString(uint256 value) internal pure returns (string memory) {{
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {{ digits++; temp /= 10; }}
        bytes memory buffer = new bytes(digits);
        while (value != 0) {{ digits--; buffer[digits] = bytes1(uint8(48 + value % 10)); value /= 10; }}
        return string(buffer);
    }}
}}"""

def compile_nft_contract(name, symbol):
    """Compile NFT contract"""
    source = get_nft_contract_source(name, symbol)
    clean_symbol = ''.join(c for c in symbol if c.isalnum())
    contract_name = f"{clean_symbol}NFT"

    try:
        set_solc_version('0.8.20')
        compiled_sol = compile_source(
            source,
            solc_version='0.8.20',
            optimize=True,
            optimize_runs=200
        )

        contract_interface = compiled_sol[f'<stdin>:{contract_name}']
        return {'abi': contract_interface['abi'], 'bytecode': '0x' + contract_interface['bin']}
    except Exception as e:
        raise Exception(f'NFT compilation failed: {e}')

def get_random_color():
    """Get a random color"""
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DFE6E9', '#74B9FF', '#A29BFE']
    return random.choice(colors)

async def run_nft():
    """Main function of the NFT module"""
    print('\n═══════════════════════════════════════════════════════════════')
    print('[14] 🎨 NFT - Create and mint collection')
    print('═══════════════════════════════════════════════════════════════\n')

    private_keys = get_private_keys()
    if len(private_keys) == 0:
        print('❌ Private keys not found in pv.txt')
        return

    web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
    wallets = [Account.from_key(pk) for pk in private_keys]

    print(f"\033[1m\033[36mFound {len(wallets)} wallet(s)\033[0m\n")

    # Check fee token balance for all wallets
    fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

    successful = 0
    failed = 0
    skipped = 0

    for w in range(len(wallets)):
        wallet = wallets[w]
        private_key = private_keys[w]
        wallet_address = Web3.to_checksum_address(wallet.address)

        print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
        print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

        # Check fee token balance
        try:
            current_fee_token = fee_manager.functions.userTokens(wallet_address).call()
            if current_fee_token == '0x0000000000000000000000000000000000000000':
                current_fee_token = CONFIG['TOKENS']['PathUSD']  # Default

            fee_token_contract = web3.eth.contract(address=Web3.to_checksum_address(current_fee_token), abi=ERC20_ABI)
            fee_balance = fee_token_contract.functions.balanceOf(wallet_address).call()
            fee_balance_formatted = fee_balance / (10 ** 6)

            # Minimum balance to pay gas (about 0.5 token for deploy + mint)
            min_balance = int(0.5 * (10 ** 6))
            if fee_balance < min_balance:
                print(f"\033[1m\033[31m⚠️ Insufficient funds to pay gas!\033[0m")
                print(f"\033[1m\033[33m  Fee token balance: {fee_balance_formatted}\033[0m")
                print(f"\033[1m\033[33m  Minimum required: 0.5 token\033[0m")
                skipped += 1
                continue
        except Exception as fee_check_err:
            print(f"\033[1m\033[33m⚠️ Failed to check fee token balance: {str(fee_check_err)[:50]}\033[0m")
            # Continue execution, but user will be warned

        # Generate random name and symbol for each wallet
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        nft_name = f'Test NFT {random_suffix}'
        nft_symbol = 'T' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

        print(f"\033[1m\033[32mCollection: {nft_name} ({nft_symbol})\033[0m")

        try:
            # Compilation
            print('\033[1m\033[36m📝 Compiling NFT contract...\033[0m')
            compiled = compile_nft_contract(nft_name, nft_symbol)
            abi = compiled['abi']
            bytecode = compiled['bytecode']
            print('\033[1m\033[32m✓ Compiled\033[0m')

            # Deploy
            print('\033[1m\033[36m🚀 Deploying NFT contract...\033[0m')
            contract = web3.eth.contract(abi=abi, bytecode=bytecode)

            nonce = web3.eth.get_transaction_count(wallet_address)
            transaction = contract.constructor().build_transaction({
                'from': wallet_address,
                'nonce': nonce,
                'gas': 2000000,
                'gasPrice': web3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })

            # Sign transaction
            try:
                signed_txn = wallet.sign_transaction(transaction)
                raw_tx = signed_txn.rawTransaction
            except (AttributeError, TypeError):
                signed_txn = Account.sign_transaction(transaction, private_key)
                raw_tx = signed_txn.rawTransaction if hasattr(signed_txn, 'rawTransaction') else signed_txn.raw_transaction
            tx_hash = web3.eth.send_raw_transaction(raw_tx)

            print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")
            receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

            contract_address = Web3.to_checksum_address(receipt['contractAddress'])
            print(f"\033[1m\033[32m✓ Contract deployed: {contract_address}\033[0m")

            # Mint NFT
            print('\033[1m\033[36m🎨 Minting NFT...\033[0m')
            mint_count = 2
            minted_successfully = 0

            for i in range(mint_count):
                minted = False
                for retry in range(3):
                    if minted:
                        break
                    try:
                        color = get_random_color()
                        contract_instance = web3.eth.contract(address=contract_address, abi=abi)

                        nonce = web3.eth.get_transaction_count(wallet_address)
                        mint_tx = contract_instance.functions.mint(wallet_address, color).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 150000,
                            'gasPrice': web3.eth.gas_price,
                            'chainId': CONFIG['CHAIN_ID']
                        })

                        # Sign transaction
                        try:
                            signed_mint = wallet.sign_transaction(mint_tx)
                            raw_tx = signed_mint.rawTransaction
                        except (AttributeError, TypeError):
                            signed_mint = Account.sign_transaction(mint_tx, private_key)
                            raw_tx = signed_mint.rawTransaction if hasattr(signed_mint, 'rawTransaction') else signed_mint.raw_transaction
                        mint_tx_hash = web3.eth.send_raw_transaction(raw_tx)

                        print(f"\033[1m\033[33m  TX: {short_hash(mint_tx_hash.hex())}\033[0m")
                        receipt = await wait_for_tx_with_retry(web3, mint_tx_hash.hex())
                        print(f"\033[1m\033[32m  ✓ NFT #{i + 1} ({color})\033[0m")

                        stats = WalletStatistics()
                        stats.record_transaction(
                            wallet_address,
                            'nft_mint',
                            mint_tx_hash.hex(),
                            str(receipt['gasUsed']),
                            'success',
                            {'nftAddress': contract_address, 'tokenId': i, 'color': color}
                        )
                        stats.close()

                        minted_successfully += 1
                        minted = True
                    except Exception as e:
                        err_msg = str(e)
                        if ('502' in err_msg or '503' in err_msg) and retry < 2:
                            print(f"\033[1m\033[33m  ⚠️ RPC error, retry {retry + 1}/3...\033[0m")
                            await async_sleep(10)
                        else:
                            print(f"\033[1m\033[31m  ✗ Mint error: {err_msg[:50]}\033[0m")
                            break

                if i < mint_count - 1:
                    await async_sleep(3)

            # Проверяем баланс
            contract_instance = web3.eth.contract(address=contract_address, abi=abi)
            balance = contract_instance.functions.balanceOf(wallet_address).call()
            print(f"\033[1m\033[32m✅ NFT balance: {balance}\033[0m")
            print(f"\033[1m\033[36m🔗 Contract: {contract_address}\033[0m")
            print(f"\033[1m\033[36m📊 Total NFTs: {balance}\033[0m")

            if minted_successfully == mint_count:
                successful += 1
            else:
                failed += 1

        except Exception as error:
            err_msg = str(error)
            print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
            failed += 1

        if w < len(wallets) - 1:
            await countdown(get_random_int(5, 10), 'Next wallet in')

    # Final statistics
    print(f"\n\033[1m\033[35m📊  NFT CREATION SUMMARY\033[0m")
    print(f"\033[1m\033[32m✓\033[0m Successful: \033[1m\033[32m{successful}\033[0m")
    print(f"\033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
    if skipped > 0:
        print(f"\033[1m\033[33m⊘\033[0m Skipped: \033[1m\033[33m{skipped}\033[0m")
    print(f"\033[1m\033[36m◆\033[0m Total wallets: \033[1m\033[36m{len(wallets)}\033[0m")

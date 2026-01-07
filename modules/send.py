# ═══════════════════════════════════════════════════════════════════════════════
# SEND TOKEN MODULE - [3]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import random
from web3 import Web3
from eth_account import Account
from config import CONFIG, ERC20_ABI, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, get_token_balance
from utils.statistics import WalletStatistics

async def send_token(web3, wallet, private_key, token_address, token_symbol, to_address, amount, retry_count=0):
    """Send tokens"""
    max_retries = 3
    try:
        contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        decimals = contract.functions.decimals().call()
        amount_wei = int(amount * (10 ** decimals))

        balance_info = get_token_balance(web3, wallet.address, token_address)

        if balance_info['balance'] < amount_wei:
            print(f"\033[1m\033[31mInsufficient {token_symbol} balance. Have: {balance_info['formatted']}, Need: {amount}\033[0m")
            return {'success': False, 'reason': 'insufficient_balance'}

        print(f"\033[1m\033[36mSending {amount} {token_symbol} to {to_address[:10]}...\033[0m")
        print(f"\033[1m\033[34mBalance: {balance_info['formatted']} {token_symbol}\033[0m")

        nonce = web3.eth.get_transaction_count(wallet.address)
        transaction = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_wei
        ).build_transaction({
            'from': wallet.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'chainId': CONFIG['CHAIN_ID']
        })

        # Sign transaction using wallet.sign_transaction; fallback to Account.sign_transaction
        try:
            signed_txn = wallet.sign_transaction(transaction)
            raw_tx = signed_txn.rawTransaction
        except (AttributeError, TypeError) as e:
            signed_txn = Account.sign_transaction(transaction, private_key)
            if hasattr(signed_txn, 'rawTransaction'):
                raw_tx = signed_txn.rawTransaction
            elif hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction
            else:
                # Last fallback - use web3.eth.account.sign_transaction
                signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
                raw_tx = signed_txn.rawTransaction
        tx_hash = web3.eth.send_raw_transaction(raw_tx)

        print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")

        receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

        if receipt['status'] == 0:
            raise Exception('Transaction reverted')

        print(f"\033[1m\033[32mSent successfully! Block: {receipt['blockNumber']}\033[0m")
        print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

        stats = WalletStatistics()
        stats.record_transaction(
            wallet.address,
            'token_transfer',
            tx_hash.hex(),
            str(receipt['gasUsed']),
            'success',
            {'tokenAddress': token_address, 'symbol': token_symbol, 'to': to_address, 'amount': str(amount)}
        )
        stats.close()

        return {'success': True}

    except Exception as error:
        error_msg = str(error)
        is_retryable = any(x in error_msg for x in ['reverted', 'nonce', '502', '503', 'Bad Gateway', 'timeout'])

        if retry_count < max_retries and is_retryable:
            wait_time = (retry_count + 1) * 5
            print(f"\033[1m\033[33m⚠️ RPC error, retry in {wait_time}s... ({retry_count + 1}/{max_retries})\033[0m")
            await async_sleep(wait_time)
            return await send_token(web3, wallet, token_address, token_symbol, to_address, amount, retry_count + 1)

        print(f"\033[1m\033[31mSend failed: {error_msg[:100]}\033[0m")
        return {'success': False, 'reason': 'error'}

async def run_send_token():
    """Main entry for token sending module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET
    BOLD_GREEN = COLORS.BOLD_GREEN
    BOLD_RED = COLORS.BOLD_RED

    print(f"\n  {BOLD_MAGENTA}💸  TOKEN SEND MODULE{RESET}\n")

    token_list = list(CONFIG['TOKENS'].items())
    print('\033[1m\033[33mAvailable tokens:\033[0m')
    for i, (name, _) in enumerate(token_list):
        print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")
    print(f"\033[1m\033[34m  {len(token_list) + 1}. All tokens\033[0m\n")

    token_choice = ask_question('\033[1m\033[36mSelect token (number): \033[0m')
    try:
        token_index = int(token_choice) - 1
        if token_index < 0 or token_index > len(token_list):
            print('\033[1m\033[31mInvalid choice\033[0m')
            return
    except ValueError:
        print('\033[1m\033[31mInvalid choice\033[0m')
        return

    print('\n\033[1m\033[33mSend destination:\033[0m')
    print('\033[1m\033[34m  1. Random address\033[0m')
    print('\033[1m\033[34m  2. Enter address manually\033[0m\n')

    dest_choice = ask_question('\033[1m\033[36mChoose (1-2): \033[0m')
    use_random_address = dest_choice == '1'
    to_address = None
    if not use_random_address:
        to_address = ask_question('\033[1m\033[36mEnter recipient address: \033[0m')
        if not Web3.is_address(to_address):
            print('\033[1m\033[31mInvalid address\033[0m')
            return

    amount_input = ask_question('\033[1m\033[36mAmount to send (default 1): \033[0m')
    amount = float(amount_input) if amount_input else 1.0

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        successful = 0
        failed = 0

        tokens_to_send = token_list if token_index == len(token_list) else [token_list[token_index]]

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet.address}\033[0m\n")

            for token_symbol, token_address in tokens_to_send:
                to = Account.create().address if use_random_address else to_address
                result = await send_token(web3, wallet, private_key, token_address, token_symbol, to, amount)
                if result.get('success'):
                    successful += 1
                else:
                    failed += 1
                await async_sleep(2)

            if w < len(wallets) - 1:
                await countdown(get_random_int(5, 10), 'Next wallet in')

        print(f"\n  {BOLD_MAGENTA}📊  SEND RESULTS{RESET}")
        print(f"  {BOLD_GREEN}✓{RESET} Success: {BOLD_GREEN}{successful}{RESET}")
        print(f"  {BOLD_RED}✗{RESET} Failed: {BOLD_RED}{failed}{RESET}")

    except Exception as error:
        print(f"\033[1m\033[31mSend Error: {error}\033[0m")


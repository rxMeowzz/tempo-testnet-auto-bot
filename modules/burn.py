# ═══════════════════════════════════════════════════════════════════════════════
# BURN TOKENS MODULE - [9]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, load_created_tokens, get_token_balance
from utils.statistics import WalletStatistics
from config import SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI

TIP20_BURN_ABI = [
    {
        'constant': False,
        'inputs': [{'name': 'amount', 'type': 'uint256'}],
        'name': 'burn',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [],
        'name': 'decimals',
        'outputs': [{'name': '', 'type': 'uint8'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [{'name': '_owner', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'name': 'balance', 'type': 'uint256'}],
        'type': 'function'
    }
]

async def run_burn_tokens():
    """Main entry for burn-tokens module"""
    print(f"\n  \033[1m\033[35m🔥  BURN TOKENS MODULE\033[0m\n")
    print('\033[1m\033[33mBurn created tokens\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]
        created_tokens = load_created_tokens()

        # Convert addresses to checksum for created token lookup
        wallets_with_tokens = []
        for w in wallets:
            wallet_addr_checksum = Web3.to_checksum_address(w.address)
            # Try to find tokens by checksum address
            wallet_tokens = created_tokens.get(wallet_addr_checksum, [])
            if len(wallet_tokens) > 0:
                wallets_with_tokens.append(w)
            else:
                # Try any saved address variant (in case of different format)
                for saved_addr, tokens_list in created_tokens.items():
                    if saved_addr.lower() == wallet_addr_checksum.lower():
                        wallets_with_tokens.append(w)
                        break

        if len(wallets_with_tokens) == 0:
            print(f"\033[1m\033[31m⚠️ No created tokens found!\033[0m")
            if len(created_tokens) > 0:
                print(f"\033[1m\033[36mDebug info: {len(created_tokens)} wallets found in token file\033[0m")
            return

        print(f"\033[1m\033[32m✓ Found {len(wallets_with_tokens)} wallets with tokens\033[0m\n")

        amount_input = ask_question('\033[1m\033[36mAmount to burn (default 10): \033[0m')
        amount = amount_input or '10'

        successful = 0
        failed = 0
        skipped = 0

        # Check fee token balance for all wallets
        fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            wallet_address = Web3.to_checksum_address(wallet.address)
            wallet_tokens = created_tokens.get(wallet_address, [])

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            if len(wallet_tokens) == 0:
                print(f"\033[1m\033[33m⚠️ Нет токенов - пропуск\033[0m")
                skipped += 1
                continue

            # Проверяем баланс fee токена
            try:
                current_fee_token = fee_manager.functions.userTokens(wallet_address).call()
                if current_fee_token == '0x0000000000000000000000000000000000000000':
                    current_fee_token = CONFIG['TOKENS']['PathUSD']  # Default

                fee_token_contract = web3.eth.contract(address=Web3.to_checksum_address(current_fee_token), abi=ERC20_ABI)
                fee_balance = fee_token_contract.functions.balanceOf(wallet_address).call()
                fee_balance_formatted = fee_balance / (10 ** 6)

                # Minimum balance to pay gas (~0.1 token)
                min_balance = int(0.1 * (10 ** 6))
                if fee_balance < min_balance:
                    print(f"\033[1m\033[31m⚠️ Not enough balance to pay gas!\033[0m")
                    print(f"\033[1m\033[33m  Fee token balance: {fee_balance_formatted}\033[0m")
                    print(f"\033[1m\033[33m  Required minimum: 0.1 token\033[0m")
                    failed += 1
                    continue
            except Exception as fee_check_err:
                print(f"\033[1m\033[33m⚠️ Failed to check fee token balance: {str(fee_check_err)[:50]}\033[0m")

            for token_info in wallet_tokens:
                burn_retry = 0
                max_burn_retries = 3
                burn_done = False

                while not burn_done and burn_retry <= max_burn_retries:
                    try:
                        token_address_checksum = Web3.to_checksum_address(token_info['token'])
                        token = web3.eth.contract(address=token_address_checksum, abi=TIP20_BURN_ABI)

                        decimals = token.functions.decimals().call()
                        amount_wei = int(float(amount) * (10 ** decimals))

                        bal_before = token.functions.balanceOf(wallet_address).call()
                        print(f"\n\033[1m\033[36mBurning {amount} {token_info['symbol']}...\033[0m")
                        print(f"\033[1m\033[34mBalance before: {bal_before / (10 ** decimals)}\033[0m")

                        if bal_before < amount_wei:
                            print(f"\033[1m\033[33m⚠️ Not enough tokens - skipping\033[0m")
                            skipped += 1
                            burn_done = True
                            continue

                        nonce = web3.eth.get_transaction_count(wallet_address)
                        burn_tx = token.functions.burn(amount_wei).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 150000,
                            'gasPrice': web3.eth.gas_price,
                            'chainId': CONFIG['CHAIN_ID']
                        })
                        try:
                            signed_burn = wallet.sign_transaction(burn_tx)
                            raw_tx = signed_burn.rawTransaction
                        except (AttributeError, TypeError):
                            signed_burn = Account.sign_transaction(burn_tx, private_key)
                            raw_tx = signed_burn.rawTransaction if hasattr(signed_burn, 'rawTransaction') else signed_burn.raw_transaction
                        burn_tx_hash = web3.eth.send_raw_transaction(raw_tx)

                        print(f"\033[1m\033[33mTX: {short_hash(burn_tx_hash.hex())}\033[0m")
                        receipt = await wait_for_tx_with_retry(web3, burn_tx_hash.hex())

                        bal_after = token.functions.balanceOf(wallet_address).call()
                        print(f"\033[1m\033[34mBalance after: {bal_after / (10 ** decimals)}\033[0m")

                        if bal_after < bal_before:
                            print(f"\033[1m\033[32m✓ Burn successful! -{(bal_before - bal_after) / (10 ** decimals)}\033[0m")

                            # Record in statistics
                            stats = WalletStatistics()
                            stats.record_transaction(
                                wallet_address,
                                'token_burn',
                                burn_tx_hash.hex(),
                                str(receipt['gasUsed']),
                                'success',
                                {'tokenAddress': token_info['token'], 'symbol': token_info['symbol'], 'amount': amount}
                            )
                            stats.close()

                            successful += 1
                        else:
                            print(f"\033[1m\033[31m✗ Balance did not change\033[0m")
                            failed += 1

                        burn_done = True

                    except Exception as error:
                        err_msg = str(error)
                        is_retryable = any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout'])

                        if is_retryable and burn_retry < max_burn_retries:
                            burn_retry += 1
                            wait_time = burn_retry * 10
                            print(f"\033[1m\033[33m⚠️ RPC error, retry in {wait_time}s... ({burn_retry}/{max_burn_retries})\033[0m")
                            await countdown(wait_time, 'Retry in')
                        else:
                            print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                            failed += 1
                            burn_done = True

                await async_sleep(2)

            if w < len(wallets) - 1:
                await countdown(get_random_int(3, 6), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  BURN RESULTS\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
        if skipped > 0:
            print(f"  \033[1m\033[33m⊘\033[0m Skipped: \033[1m\033[33m{skipped}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mBurn Error: {error}\033[0m")

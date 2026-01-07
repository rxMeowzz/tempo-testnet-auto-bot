# ═══════════════════════════════════════════════════════════════════════════════
# REMOVE LIQUIDITY MODULE - [12]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, FEE_MANAGER_ABI, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys
from utils.statistics import WalletStatistics

async def run_remove_liquidity():
    """Main entry for remove-liquidity module"""
    print(f"\n  \033[1m\033[35m💧  REMOVE LIQUIDITY MODULE\033[0m\n")
    print('\033[1m\033[33mWithdraw liquidity from Fee AMM pool\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        token_list = list(CONFIG['TOKENS'].items())

        print('\033[1m\033[33mSelect User Token:\033[0m')
        for i, (name, _) in enumerate(token_list):
            print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")
        user_choice = ask_question('\033[1m\033[36mChoose (1-4): \033[0m')
        try:
            user_index = int(user_choice) - 1
            if user_index < 0 or user_index >= len(token_list):
                print('\033[1m\033[31mInvalid choice\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31mInvalid choice\033[0m')
            return

        user_token_symbol, user_token_address = token_list[user_index]

        print('\n\033[1m\033[33mSelect Validator Token:\033[0m')
        for i, (name, _) in enumerate(token_list):
            if i != user_index:
                print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")
        val_choice = ask_question('\033[1m\033[36mChoose (1-4): \033[0m')
        try:
            val_index = int(val_choice) - 1
            if val_index < 0 or val_index >= len(token_list) or val_index == user_index:
                print('\033[1m\033[31mInvalid choice\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31mInvalid choice\033[0m')
            return

        val_token_symbol, val_token_address = token_list[val_index]

        amount_input = ask_question('\033[1m\033[36mLP amount to withdraw (default 1): \033[0m')
        amount = amount_input or '1'

        print(f"\n\033[1m\033[32mParameters:\033[0m")
        print(f"  Pool: {user_token_symbol}/{val_token_symbol}")
        print(f"  LP amount: {amount}\n")

        fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

        successful = 0
        failed = 0
        skipped = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            wallet_address = Web3.to_checksum_address(wallet.address)
            user_token_address_checksum = Web3.to_checksum_address(user_token_address)
            val_token_address_checksum = Web3.to_checksum_address(val_token_address)

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            retry_count = 0
            max_retries = 3
            done = False

            while not done and retry_count <= max_retries:
                try:
                    pool_id = fee_manager.functions.getPoolId(
                        user_token_address_checksum,
                        val_token_address_checksum
                    ).call()
                    lp_balance = fee_manager.functions.liquidityBalances(pool_id, wallet_address).call()
                    print(f"\033[1m\033[34mLP balance: {lp_balance / (10 ** 6)}\033[0m")

                    withdraw_amount = int(float(amount) * (10 ** 6))

                    if lp_balance == 0:
                        print(f"\033[1m\033[33m⚠️ No LP tokens - skipping\033[0m")
                        skipped += 1
                        done = True
                        continue

                    if lp_balance < withdraw_amount:
                        print(f"\033[1m\033[33m⚠️ LP < {amount} - skipping\033[0m")
                        skipped += 1
                        done = True
                        continue

                    print(f"\033[1m\033[36mWithdrawing {amount} LP...\033[0m")
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    tx = fee_manager.functions.burn(
                        user_token_address_checksum,
                        val_token_address_checksum,
                        withdraw_amount,
                        wallet_address
                    ).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 500000,
                        'gasPrice': web3.eth.gas_price,
                        'chainId': CONFIG['CHAIN_ID']
                    })

                    try:
                        signed_tx = wallet.sign_transaction(tx)
                        raw_tx = signed_tx.rawTransaction
                    except (AttributeError, TypeError):
                        signed_tx = Account.sign_transaction(tx, private_key)
                        raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
                    tx_hash = web3.eth.send_raw_transaction(raw_tx)

                    print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")
                    receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                    lp_after = fee_manager.functions.liquidityBalances(pool_id, wallet_address).call()
                    print(f"\033[1m\033[34mLP balance after: {lp_after / (10 ** 6)}\033[0m")

                    if lp_after < lp_balance:
                        print(f"\033[1m\033[32m✓ Liquidity withdrawn!\033[0m")
                        print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                        stats = WalletStatistics()
                        stats.record_transaction(
                            wallet_address,
                            'liquidity_remove',
                            tx_hash.hex(),
                            str(receipt['gasUsed']),
                            'success',
                            {'userToken': user_token_symbol, 'validatorToken': val_token_symbol, 'amount': amount}
                        )
                        stats.close()

                        successful += 1
                    else:
                        print(f"\033[1m\033[31m✗ LP did not decrease\033[0m")
                        failed += 1

                    done = True

                except Exception as error:
                    err_msg = str(error)
                    is_retryable = any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout'])

                    if is_retryable and retry_count < max_retries:
                        retry_count += 1
                        wait_time = retry_count * 10
                        print(f"\033[1m\033[33m⚠️ RPC error, retry in {wait_time}s... ({retry_count}/{max_retries})\033[0m")
                        await countdown(wait_time, 'Retry in')
                    else:
                        print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                        failed += 1
                        done = True

            if w < len(wallets) - 1:
                await countdown(get_random_int(3, 6), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  REMOVE LIQUIDITY RESULTS\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
        if skipped > 0:
            print(f"  \033[1m\033[33m⊘\033[0m Skipped: \033[1m\033[33m{skipped}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mRemove Liquidity Error: {error}\033[0m")

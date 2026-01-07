# ═══════════════════════════════════════════════════════════════════════════════
# ADD LIQUIDITY MODULE - [6]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import random
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, get_token_balance, load_created_tokens
from utils.statistics import WalletStatistics

async def run_add_liquidity():
    """Main function of the add liquidity module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET
    BOLD_GREEN = COLORS.BOLD_GREEN
    BOLD_RED = COLORS.BOLD_RED
    BOLD_YELLOW = COLORS.BOLD_YELLOW

    print(f"\n  {BOLD_MAGENTA}💦  ADD LIQUIDITY MODULE{RESET}\n")
    print('\033[1m\033[33mAdding liquidity to Fee AMM pool\033[0m')
    print('\033[1m\033[34mFee AMM works with any USD TIP-20 tokens\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]
        created_tokens = load_created_tokens()

        token_list = list(CONFIG['TOKENS'].items())

        # Convert addresses to checksum format for checking created tokens
        wallets_with_tokens = [w for w in wallets if len(created_tokens.get(Web3.to_checksum_address(w.address), [])) > 0]

        print('\033[1m\033[33mToken mode:\033[0m')
        print('\033[1m\033[34m  1. Select pair manually\033[0m')
        print('\033[1m\033[34m  2. Full random (pairs + amounts)\033[0m')
        if len(wallets_with_tokens) > 0:
            print(f"\033[1m\033[34m  3. Created tokens ({len(wallets_with_tokens)} wallets)\033[0m")

        mode_choice = ask_question('\033[1m\033[36mSelect mode (1-3, default 1): \033[0m')
        use_full_random = mode_choice == '2'
        use_created_tokens = mode_choice == '3' and len(wallets_with_tokens) > 0

        user_token_symbol = None
        user_token_address = None
        val_token_symbol = None
        val_token_address = None
        use_random_liq_amount = False
        fixed_amount = None
        min_liq_amount = None
        max_liq_amount = None

        if use_full_random:
            print('\n\033[1m\033[32m🎲 FULL RANDOM MODE\033[0m\n')

            min_input = ask_question('\033[1m\033[36mMinimum amount (default 500): \033[0m')
            min_liq_amount = float(min_input) if min_input else 500.0
            max_input = ask_question('\033[1m\033[36mMaximum amount (default 2000): \033[0m')
            max_liq_amount = float(max_input) if max_input else 2000.0
            if min_liq_amount > max_liq_amount:
                min_liq_amount, max_liq_amount = max_liq_amount, min_liq_amount

            use_random_liq_amount = True
            user_token_symbol = 'RANDOM'
            val_token_symbol = 'RANDOM'

        elif use_created_tokens:
            val_token_symbol = 'PathUSD'
            val_token_address = CONFIG['TOKENS']['PathUSD']
            user_token_symbol = 'CREATED'
            user_token_address = None

            print('\n\033[1m\033[33mAmount mode:\033[0m')
            print('\033[1m\033[34m  1. Fixed amount\033[0m')
            print('\033[1m\033[34m  2. Random amount\033[0m\n')
            amt_mode = ask_question('\033[1m\033[36mChoose (1-2, default 1): \033[0m')
            use_random_liq_amount = amt_mode == '2'

            if use_random_liq_amount:
                min_input = ask_question('\033[1m\033[36mMinimum amount (default 500): \033[0m')
                min_liq_amount = float(min_input) if min_input else 500.0
                max_input = ask_question('\033[1m\033[36mMaximum amount (default 2000): \033[0m')
                max_liq_amount = float(max_input) if max_input else 2000.0
                if min_liq_amount > max_liq_amount:
                    min_liq_amount, max_liq_amount = max_liq_amount, min_liq_amount
            else:
                amount_input = ask_question('\033[1m\033[36mAmount (default 1000): \033[0m')
                fixed_amount = amount_input or '1000'
        else:
            print('\n\033[1m\033[33mSelect User Token:\033[0m')
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

            print('\n\033[1m\033[33mAmount mode:\033[0m')
            print('\033[1m\033[34m  1. Fixed amount\033[0m')
            print('\033[1m\033[34m  2. Random amount\033[0m\n')
            amt_mode = ask_question('\033[1m\033[36mChoose (1-2, default 1): \033[0m')
            use_random_liq_amount = amt_mode == '2'

            if use_random_liq_amount:
                min_input = ask_question('\033[1m\033[36mMinimum amount (default 500): \033[0m')
                min_liq_amount = float(min_input) if min_input else 500.0
                max_input = ask_question('\033[1m\033[36mMaximum amount (default 2000): \033[0m')
                max_liq_amount = float(max_input) if max_input else 2000.0
                if min_liq_amount > max_liq_amount:
                    min_liq_amount, max_liq_amount = max_liq_amount, min_liq_amount
            else:
                amount_input = ask_question('\033[1m\033[36mAmount (default 1000): \033[0m')
                fixed_amount = amount_input or '1000'

        fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

        successful = 0
        failed = 0
        skipped = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            # Ensure the address is in checksum format
            wallet_address = Web3.to_checksum_address(wallet.address)
            wallet_created_tokens = created_tokens.get(wallet_address, [])

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            tokens_to_process = []
            current_val_token_symbol = val_token_symbol
            current_val_token_address = val_token_address

            if use_full_random:
                shuffled = token_list.copy()
                random.shuffle(shuffled)
                user_t, val_t = shuffled[:2]
                tokens_to_process = [{'symbol': user_t[0], 'address': user_t[1]}]
                current_val_token_symbol = val_t[0]
                current_val_token_address = val_t[1]
                print(f"\033[1m\033[33m🎲 Random pair: {user_t[0]} + {val_t[0]}\033[0m")
            elif use_created_tokens:
                tokens_to_process = [{'symbol': t['symbol'], 'address': t['token']} for t in wallet_created_tokens]
            else:
                tokens_to_process = [{'symbol': user_token_symbol, 'address': user_token_address}]

            if use_created_tokens and len(wallet_created_tokens) == 0:
                print(f"\033[1m\033[33m⚠️ No created tokens - skipping\033[0m")
                skipped += 1
                if w < len(wallets) - 1:
                    await countdown(get_random_int(2, 4), 'Next wallet in')
                continue

            for token_to_add in tokens_to_process:
                current_user_symbol = token_to_add['symbol']
                current_user_address = token_to_add['address']

                if use_random_liq_amount:
                    random_value = min_liq_amount + random.random() * (max_liq_amount - min_liq_amount)
                    current_amount = f"{random_value:.2f}"
                else:
                    current_amount = fixed_amount

                # Ensure all addresses are in checksum format
                current_val_token_address_checksum = Web3.to_checksum_address(current_val_token_address)
                current_user_address_checksum = Web3.to_checksum_address(current_user_address)
                fee_manager_address_checksum = Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER'])

                val_balance = get_token_balance(web3, wallet_address, current_val_token_address_checksum)
                print(f"\033[1m\033[34mBalance {current_val_token_symbol}: {val_balance['formatted']}\033[0m")

                amount_wei = int(float(current_amount) * (10 ** 6))
                if val_balance['balance'] < amount_wei:
                    print(f"\033[1m\033[33m⚠️ Insufficient balance - skipping\033[0m")
                    failed += 1
                    continue

                print(f"\033[1m\033[36mPool: {current_user_symbol} + {current_val_token_symbol}\033[0m")

                liq_retry = 0
                max_liq_retries = 3
                liq_done = False

                while not liq_done and liq_retry <= max_liq_retries:
                    try:
                        val_token_contract = web3.eth.contract(address=current_val_token_address_checksum, abi=ERC20_ABI)
                        allowance_val = val_token_contract.functions.allowance(wallet_address, fee_manager_address_checksum).call()

                        if allowance_val < amount_wei:
                            print(f"\033[1m\033[34mApproving {current_val_token_symbol}...\033[0m")
                            nonce = web3.eth.get_transaction_count(wallet_address)
                            max_uint256 = 2**256 - 1
                            approve_tx = val_token_contract.functions.approve(fee_manager_address_checksum, max_uint256).build_transaction({
                                'from': wallet_address,
                                'nonce': nonce,
                                'gas': 100000,
                                'gasPrice': web3.eth.gas_price,
                                'chainId': CONFIG['CHAIN_ID']
                            })
                            # Sign transaction
                            try:
                                signed_approve = wallet.sign_transaction(approve_tx)
                                raw_tx = signed_approve.rawTransaction
                            except (AttributeError, TypeError):
                                signed_approve = Account.sign_transaction(approve_tx, private_key)
                                raw_tx = signed_approve.rawTransaction if hasattr(signed_approve, 'rawTransaction') else signed_approve.raw_transaction
                            await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())
                            print(f"\033[1m\033[32m✓ {current_val_token_symbol} approved\033[0m")

                        print(f"\033[1m\033[36mAdding liquidity...\033[0m")
                        nonce = web3.eth.get_transaction_count(wallet_address)
                        tx = fee_manager.functions.mintWithValidatorToken(
                            current_user_address_checksum,
                            current_val_token_address_checksum,
                            amount_wei,
                            wallet_address
                        ).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 500000,
                            'gasPrice': web3.eth.gas_price,
                            'chainId': CONFIG['CHAIN_ID']
                        })

                        # Sign transaction
                        try:
                            signed_tx = wallet.sign_transaction(tx)
                            raw_tx = signed_tx.rawTransaction
                        except (AttributeError, TypeError):
                            signed_tx = Account.sign_transaction(tx, private_key)
                            raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
                        tx_hash = web3.eth.send_raw_transaction(raw_tx)

                        print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")
                        receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                        print(f"\033[1m\033[32m✓ Liquidity added!\033[0m")
                        print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                        # Record in statistics
                        stats = WalletStatistics()
                        stats.record_transaction(
                            wallet_address,
                            'liquidity_add',
                            tx_hash.hex(),
                            str(receipt['gasUsed']),
                            'success',
                            {'userToken': current_user_symbol, 'validatorToken': current_val_token_symbol, 'amount': current_amount}
                        )
                        stats.close()

                        successful += 1
                        liq_done = True

                    except Exception as error:
                        err_msg = str(error)
                        is_retryable = any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout'])

                        if is_retryable and liq_retry < max_liq_retries:
                            liq_retry += 1
                            wait_time = liq_retry * 10
                            print(f"\033[1m\033[33m⚠️ Error, retrying in {wait_time}s... ({liq_retry}/{max_liq_retries})\033[0m")
                            await countdown(wait_time, 'Retry in')
                        else:
                            print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                            failed += 1
                            liq_done = True

                await async_sleep(2)

            if w < len(wallets) - 1:
                await countdown(get_random_int(5, 10), 'Next wallet in')

        print(f"\n  {BOLD_MAGENTA}📊  LIQUIDITY ADDITION SUMMARY{RESET}")
        print(f"  {BOLD_GREEN}✓{RESET} Successful: {BOLD_GREEN}{successful}{RESET}")
        print(f"  {BOLD_RED}✗{RESET} Failed: {BOLD_RED}{failed}{RESET}")
        if skipped > 0:
            print(f"  {BOLD_YELLOW}⊘{RESET} Skipped: {BOLD_YELLOW}{skipped}{RESET}")

    except Exception as error:
        print(f"\033[1m\033[31mLiquidity Error: {error}\033[0m")

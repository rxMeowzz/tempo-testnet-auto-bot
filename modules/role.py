# ═══════════════════════════════════════════════════════════════════════════════
# GRANT ROLE MODULE - [13]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, load_created_tokens, get_token_balance
from utils.statistics import WalletStatistics
from config import SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI

ROLE_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'role', 'type': 'bytes32'},
            {'name': 'account', 'type': 'address'}
        ],
        'name': 'grantRole',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'role', 'type': 'bytes32'},
            {'name': 'account', 'type': 'address'}
        ],
        'name': 'hasRole',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function'
    }
]

async def run_grant_role():
    """Main function of the grant roles module"""
    print(f"\n  \033[1m\033[35m🔑  GRANT ROLES MODULE\033[0m\n")
    print('\033[1m\033[33mGrant ISSUER_ROLE or PAUSE_ROLE to created tokens\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]
        created_tokens = load_created_tokens()

        # Convert addresses to checksum format to check created tokens
        wallets_with_tokens = []
        for w in wallets:
            wallet_addr_checksum = Web3.to_checksum_address(w.address)
            # Try to find tokens by checksum address
            wallet_tokens = created_tokens.get(wallet_addr_checksum, [])
            if len(wallet_tokens) > 0:
                wallets_with_tokens.append(w)
            else:
                # Try to find by any address variant (in case it was saved in another format)
                for saved_addr, tokens_list in created_tokens.items():
                    if saved_addr.lower() == wallet_addr_checksum.lower():
                        wallets_with_tokens.append(w)
                        break

        if len(wallets_with_tokens) == 0:
            print(f"\033[1m\033[31m⚠️ No created tokens!\033[0m")
            if len(created_tokens) > 0:
                print(f"\033[1m\033[36mDebug info: found {len(created_tokens)} wallets in token file\033[0m")
            return

        print(f"\033[1m\033[32m✓ Found {len(wallets_with_tokens)} wallets with tokens\033[0m\n")

        print('\033[1m\033[33mSelect role:\033[0m')
        print('\033[1m\033[34m  1. ISSUER_ROLE (for mint)\033[0m')
        print('\033[1m\033[34m  2. PAUSE_ROLE (for pause)\033[0m\n')

        role_choice = ask_question('\033[1m\033[36mChoose (1-2, default 1): \033[0m')
        role_name = 'PAUSE_ROLE' if role_choice == '2' else 'ISSUER_ROLE'
        role_hash = Web3.keccak(text=role_name)

        print(f"\n\033[1m\033[32mGranting role: {role_name}\033[0m\n")

        successful = 0
        failed = 0
        skipped = 0

        # Check fee token balance for all wallets
        fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            # Ensure the address is in checksum format
            wallet_address = Web3.to_checksum_address(wallet.address)
            wallet_tokens = created_tokens.get(wallet_address, [])

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            if len(wallet_tokens) == 0:
                print(f"\033[1m\033[33m⚠️ No tokens - skipping\033[0m")
                skipped += 1
                continue

            # Check fee token balance
            try:
                current_fee_token = fee_manager.functions.userTokens(wallet_address).call()
                if current_fee_token == '0x0000000000000000000000000000000000000000':
                    current_fee_token = CONFIG['TOKENS']['PathUSD']  # Default

                fee_token_contract = web3.eth.contract(address=Web3.to_checksum_address(current_fee_token), abi=ERC20_ABI)
                fee_balance = fee_token_contract.functions.balanceOf(wallet_address).call()
                fee_balance_formatted = fee_balance / (10 ** 6)

                # Minimum balance to pay gas (about 0.1 token)
                min_balance = int(0.1 * (10 ** 6))
                if fee_balance < min_balance:
                    print(f"\033[1m\033[31m⚠️ Insufficient funds to pay gas!\033[0m")
                    print(f"\033[1m\033[33m  Fee token balance: {fee_balance_formatted}\033[0m")
                    print(f"\033[1m\033[33m  Minimum required: 0.1 token\033[0m")
                    failed += 1
                    continue
            except Exception as fee_check_err:
                print(f"\033[1m\033[33m⚠️ Failed to check fee token balance: {str(fee_check_err)[:50]}\033[0m")

            for token_info in wallet_tokens:
                role_retry = 0
                max_role_retries = 3
                role_done = False

                while not role_done and role_retry <= max_role_retries:
                    try:
                        token_address_checksum = Web3.to_checksum_address(token_info['token'])
                        token = web3.eth.contract(address=token_address_checksum, abi=ROLE_ABI)

                        print(f"\n\033[1m\033[36mToken: {token_info['symbol']}\033[0m")

                        has_role = token.functions.hasRole(role_hash, wallet_address).call()

                        if has_role:
                            print(f"\033[1m\033[32m✓ {role_name} already granted\033[0m")
                            successful += 1
                            role_done = True
                            continue

                        print(f"\033[1m\033[36mGranting {role_name}...\033[0m")
                        nonce = web3.eth.get_transaction_count(wallet_address)
                        tx = token.functions.grantRole(role_hash, wallet_address).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 150000,
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

                        has_role_after = token.functions.hasRole(role_hash, wallet_address).call()
                        if has_role_after:
                            print(f"\033[1m\033[32m✓ {role_name} granted!\033[0m")

                            stats = WalletStatistics()
                            stats.record_transaction(
                                wallet_address,
                                'role_grant',
                                tx_hash.hex(),
                                str(receipt['gasUsed']),
                                'success',
                                {'tokenAddress': token_info['token'], 'symbol': token_info['symbol'], 'role': role_name, 'account': wallet_address}
                            )
                            stats.close()

                            successful += 1
                        else:
                            print(f"\033[1m\033[31m✗ Role not granted\033[0m")
                            failed += 1

                        role_done = True

                    except Exception as error:
                        err_msg = str(error)
                        is_retryable = any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout'])

                        if is_retryable and role_retry < max_role_retries:
                            role_retry += 1
                            wait_time = role_retry * 10
                            print(f"\033[1m\033[33m⚠️ RPC error, retrying in {wait_time}s... ({role_retry}/{max_role_retries})\033[0m")
                            await countdown(wait_time, 'Retry in')
                        else:
                            print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                            failed += 1
                            role_done = True

                await async_sleep(2)

            if w < len(wallets) - 1:
                await countdown(get_random_int(3, 6), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  ROLE GRANT SUMMARY\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Successful: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
        if skipped > 0:
            print(f"  \033[1m\033[33m⊘\033[0m Skipped: \033[1m\033[33m{skipped}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mGrant Role Error: {error}\033[0m")

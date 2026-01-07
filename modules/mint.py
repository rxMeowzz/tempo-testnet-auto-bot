# ═══════════════════════════════════════════════════════════════════════════════
# MINT TOKENS MODULE - [8]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, load_created_tokens, get_token_balance
from utils.statistics import WalletStatistics
from config import SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI

TIP20_MINT_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'to', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'}
        ],
        'name': 'mint',
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
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'role', 'type': 'bytes32'},
            {'name': 'account', 'type': 'address'}
        ],
        'name': 'grantRole',
        'outputs': [],
        'type': 'function'
    }
]

async def run_mint_tokens():
    """Main function of the token mint module"""
    print(f"\n  \033[1m\033[35m🏭  TOKEN MINT MODULE\033[0m\n")
    print('\033[1m\033[33mAutomatic mint for created tokens\033[0m')
    print('\033[1m\033[34mEach wallet mints only ITS own tokens\033[0m\n')

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
            print(f"\033[1m\033[33mFirst create tokens via [4] Create stablecoin\033[0m")
            return

        print(f"\033[1m\033[32m✓ Found {len(wallets_with_tokens)} wallets with created tokens\033[0m\n")

        amount_input = ask_question('\033[1m\033[36mAmount to mint (default 1000): \033[0m')
        amount = amount_input or '1000'

        ISSUER_ROLE = Web3.keccak(text="ISSUER_ROLE")

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
                print(f"\033[1m\033[33m⚠️ No created tokens - skipping\033[0m")
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

                # Minimum balance to pay gas (approximately 0.1 token)
                min_balance = int(0.1 * (10 ** 6))
                if fee_balance < min_balance:
                    print(f"\033[1m\033[31m⚠️ Insufficient funds to pay gas!\033[0m")
                    print(f"\033[1m\033[33m  Fee token balance: {fee_balance_formatted}\033[0m")
                    print(f"\033[1m\033[33m  Minimum required: 0.1 token\033[0m")
                    print(f"\033[1m\033[33m  Get tokens via [2] Faucet or set fee token via [7]\033[0m")
                    failed += 1
                    continue
            except Exception as fee_check_err:
                print(f"\033[1m\033[33m⚠️ Failed to check fee token balance: {str(fee_check_err)[:50]}\033[0m")
                # Continue execution, but user is warned

            print(f"\033[1m\033[32mTokens of this wallet: {len(wallet_tokens)}\033[0m")

            for token_info in wallet_tokens:
                mint_retry = 0
                max_mint_retries = 5
                mint_done = False

                while not mint_done and mint_retry <= max_mint_retries:
                    try:
                        token_address_checksum = Web3.to_checksum_address(token_info['token'])
                        token = web3.eth.contract(address=token_address_checksum, abi=TIP20_MINT_ABI)

                        decimals = 6
                        try:
                            decimals = token.functions.decimals().call()
                        except Exception as dec_err:
                            dec_err_msg = str(dec_err)
                            if any(x in dec_err_msg for x in ['502', '503', 'Bad Gateway']):
                                raise dec_err

                        amount_wei = int(float(amount) * (10 ** decimals))

                        needs_role = False
                        try:
                            has_issuer_role = token.functions.hasRole(ISSUER_ROLE, wallet_address).call()
                            needs_role = not has_issuer_role
                        except Exception as check_err:
                            check_err_msg = str(check_err)
                            if any(x in check_err_msg for x in ['502', '503', 'Bad Gateway']):
                                raise check_err
                            needs_role = True

                        if needs_role:
                            try:
                                print(f"\033[1m\033[33m  ⚠️ Granting ISSUER_ROLE...\033[0m")
                                nonce = web3.eth.get_transaction_count(wallet_address)
                                grant_tx = token.functions.grantRole(ISSUER_ROLE, wallet_address).build_transaction({
                                    'from': wallet_address,
                                    'nonce': nonce,
                                    'gas': 150000,
                                    'gasPrice': web3.eth.gas_price,
                                    'chainId': CONFIG['CHAIN_ID']
                                })
                                # Sign transaction
                                try:
                                    signed_grant = wallet.sign_transaction(grant_tx)
                                    raw_tx = signed_grant.rawTransaction
                                except (AttributeError, TypeError):
                                    signed_grant = Account.sign_transaction(grant_tx, private_key)
                                    raw_tx = signed_grant.rawTransaction if hasattr(signed_grant, 'rawTransaction') else signed_grant.raw_transaction
                                grant_tx_hash = web3.eth.send_raw_transaction(raw_tx)
                                print(f"\033[1m\033[33m  Grant TX: {short_hash(grant_tx_hash.hex())}\033[0m")
                                await wait_for_tx_with_retry(web3, grant_tx_hash.hex())
                                print(f"\033[1m\033[32m  ✓ ISSUER_ROLE granted\033[0m")
                                await async_sleep(2)
                            except Exception as grant_err:
                                print(f"\033[1m\033[33m  ⚠️ Failed to grant role: {str(grant_err)[:60]}\033[0m")

                        print(f"\n\033[1m\033[36mMint {amount} {token_info['symbol']}...\033[0m")
                        bal_before = token.functions.balanceOf(wallet_address).call()
                        print(f"\033[1m\033[34mBalance before: {bal_before / (10 ** decimals)}\033[0m")

                        nonce = web3.eth.get_transaction_count(wallet_address)
                        mint_tx = token.functions.mint(wallet_address, amount_wei).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 200000,
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

                        print(f"\033[1m\033[33mTX: {short_hash(mint_tx_hash.hex())}\033[0m")
                        receipt = await wait_for_tx_with_retry(web3, mint_tx_hash.hex())

                        bal_after = token.functions.balanceOf(wallet_address).call()
                        print(f"\033[1m\033[34mBalance after: {bal_after / (10 ** decimals)}\033[0m")

                        if bal_after > bal_before:
                            print(f"\033[1m\033[32m✓ Mint successful! +{(bal_after - bal_before) / (10 ** decimals)}\033[0m")

                            # Record in statistics
                            stats = WalletStatistics()
                            stats.record_transaction(
                                wallet_address,
                                'token_mint',
                                mint_tx_hash.hex(),
                                str(receipt['gasUsed']),
                                'success',
                                {'tokenAddress': token_info['token'], 'symbol': token_info['symbol'], 'amount': amount}
                            )
                            stats.close()

                            successful += 1
                        else:
                            print(f"\033[1m\033[31m✗ Balance did not change\033[0m")
                            failed += 1

                        mint_done = True

                    except Exception as error:
                        err_msg = str(error)
                        is_retryable = any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout'])

                        if is_retryable and mint_retry < max_mint_retries:
                            mint_retry += 1
                            wait_time = mint_retry * 10
                            print(f"\033[1m\033[33m⚠️ RPC error, retrying in {wait_time}s... ({mint_retry}/{max_mint_retries})\033[0m")
                            await countdown(wait_time, 'Retry in')
                        else:
                            print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                            failed += 1
                            mint_done = True

                await async_sleep(2)

            if w < len(wallets) - 1:
                await countdown(get_random_int(5, 10), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  MINT SUMMARY\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Successful: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
        if skipped > 0:
            print(f"  \033[1m\033[33m⊘\033[0m Skipped: \033[1m\033[33m{skipped}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mMint Error: {error}\033[0m")

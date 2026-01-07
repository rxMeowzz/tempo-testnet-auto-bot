# ═══════════════════════════════════════════════════════════════════════════════
# SET FEE TOKEN MODULE - [7]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, get_token_balance
from utils.statistics import WalletStatistics

async def run_set_fee_token():
    """Main entry for fee token setup module"""
    print(f"\n  \033[1m\033[35m⚙️   FEE TOKEN SETUP MODULE\033[0m\n")
    print('\033[1m\033[33mFee token is the stablecoin used to pay gas.\033[0m')
    print('\033[1m\033[33mTempo has no native token — gas is paid in stablecoins!\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        token_list = list(CONFIG['TOKENS'].items())

        print('\033[1m\033[33mSelect token to pay fees:\033[0m')
        for i, (name, _) in enumerate(token_list):
            print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")

        print('\033[1m\033[33m⚠️ On testnet validators expect AlphaUSD!\033[0m\n')
        choice = ask_question('\033[1m\033[36mChoose (1-4, default 2 AlphaUSD): \033[0m')
        try:
            index = int(choice) - 1 if choice else 1
            if index < 0 or index >= len(token_list):
                index = 1
        except ValueError:
            index = 1

        token_symbol, token_address = token_list[index]

        print(f"\n\033[1m\033[32mSetting fee token: {token_symbol}\033[0m\n")

        fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

        successful = 0
        failed = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            wallet_address = Web3.to_checksum_address(wallet.address)
            token_address_checksum = Web3.to_checksum_address(token_address)

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            retry_count = 0
            max_retries = 3
            done = False

            while not done and retry_count <= max_retries:
                try:
                    current_token = fee_manager.functions.userTokens(wallet_address).call()
                    current_fee_token_addr = CONFIG['TOKENS']['PathUSD'] if current_token == '0x0000000000000000000000000000000000000000' else current_token

                    current_token_name = 'PathUSD (default)'
                    if current_token != '0x0000000000000000000000000000000000000000':
                        for name, addr in CONFIG['TOKENS'].items():
                            if addr.lower() == current_token.lower():
                                current_token_name = name
                                break
                        if current_token_name == 'PathUSD (default)':
                            current_token_name = current_token

                    current_fee_token_contract = web3.eth.contract(address=Web3.to_checksum_address(current_fee_token_addr), abi=ERC20_ABI)
                    current_fee_balance = current_fee_token_contract.functions.balanceOf(wallet_address).call()
                    current_fee_balance_formatted = current_fee_balance / (10 ** 6)

                    print(f"\033[1m\033[34mCurrent fee token: {current_token_name} (balance: {current_fee_balance_formatted})\033[0m")

                    if current_fee_balance < int(1 * (10 ** 6)):
                        print(f"\033[1m\033[31m⚠️ Not enough {current_token_name} to pay gas!\033[0m")
                        failed += 1
                        done = True
                        continue

                    if current_token.lower() == token_address.lower():
                        print(f"\033[1m\033[32m✓ Already set to {token_symbol}\033[0m")
                        successful += 1
                        done = True
                        continue

                    print('\033[1m\033[36mSetting fee token...\033[0m')
                    await async_sleep(2)
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    tx = fee_manager.functions.setUserToken(token_address_checksum).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 150000,
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

                    receipt = None
                    wait_success = False
                    for wait_retry in range(5):
                        try:
                            receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())
                            wait_success = True
                            break
                        except Exception as wait_err:
                            wait_err_msg = str(wait_err)
                            if any(x in wait_err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR']):
                                print(f"\033[1m\033[33m⚠️ RPC ошибка при ожидании ({wait_retry + 1}/5), повтор через 5s...\033[0m")
                                await async_sleep(5)
                            else:
                                break

                    if not wait_success:
                        print(f"\033[1m\033[33m⚠️ TX отправлена, но не удалось подтвердить.\033[0m")
                        print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")
                        successful += 1
                        done = True
                        continue

                    print(f"\033[1m\033[32m✓ Fee token set!\033[0m")
                    print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                    stats = WalletStatistics()
                    stats.record_transaction(
                        wallet_address,
                        'fee_token_set',
                        tx_hash.hex(),
                        str(receipt['gasUsed']),
                        'success',
                        {'tokenAddress': token_address, 'symbol': token_symbol}
                    )
                    stats.close()

                    successful += 1
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
                        print(f"\033[1m\033[31m✗ Error: {err_msg[:150]}\033[0m")
                        failed += 1
                        done = True

            if w < len(wallets) - 1:
                await countdown(get_random_int(3, 6), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  FEE TOKEN SETUP RESULTS\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mSet Fee Token Error: {error}\033[0m")

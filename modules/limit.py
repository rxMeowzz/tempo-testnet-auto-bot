# ═══════════════════════════════════════════════════════════════════════════════
# LIMIT ORDER MODULE - [11]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, STABLECOIN_DEX_ABI, ERC20_ABI, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, get_token_balance
from utils.statistics import WalletStatistics

DEX_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'token', 'type': 'address'},
            {'name': 'amount', 'type': 'uint128'},
            {'name': 'isBid', 'type': 'bool'},
            {'name': 'tick', 'type': 'int16'}
        ],
        'name': 'place',
        'outputs': [{'name': 'orderId', 'type': 'uint128'}],
        'type': 'function'
    }
]

async def run_limit_order():
    """Main entry for limit order module"""
    print(f"\n  \033[1m\033[35m📊  LIMIT ORDER MODULE\033[0m\n")
    print('\033[1m\033[33mPlace limit orders on the DEX\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        token_list = list(CONFIG['TOKENS'].items())

        print('\033[1m\033[33mSelect token:\033[0m')
        for i, (name, _) in enumerate(token_list):
            print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")

        token_choice = ask_question('\033[1m\033[36mChoose (1-4): \033[0m')
        try:
            token_index = int(token_choice) - 1
            if token_index < 0 or token_index >= len(token_list):
                print('\033[1m\033[31mInvalid choice\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31mInvalid choice\033[0m')
            return

        token_symbol, token_address = token_list[token_index]

        print('\n\033[1m\033[33mOrder type:\033[0m')
        print('\033[1m\033[34m  1. BID (buy token for PathUSD)\033[0m')
        print('\033[1m\033[34m  2. ASK (sell token for PathUSD)\033[0m\n')

        type_choice = ask_question('\033[1m\033[36mChoose (1-2): \033[0m')
        is_bid = type_choice == '1'

        amount_input = ask_question('\033[1m\033[36mAmount (default 10): \033[0m')
        amount = amount_input or '10'

        tick_input = ask_question('\033[1m\033[36mTick (default 0 = $1.00): \033[0m')
        try:
            tick = int(tick_input) if tick_input else 0
        except ValueError:
            tick = 0

        print(f"\n\033[1m\033[32mParameters:\033[0m")
        print(f"  Token: {token_symbol}")
        print(f"  Type: {'BID (buy)' if is_bid else 'ASK (sell)'}")
        print(f"  Amount: {amount}")
        print(f"  Tick: {tick}\n")

        dex = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['STABLECOIN_DEX']), abi=DEX_ABI)

        successful = 0
        failed = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            wallet_address = Web3.to_checksum_address(wallet.address)
            token_address_checksum = Web3.to_checksum_address(token_address)
            dex_address_checksum = Web3.to_checksum_address(SYSTEM_CONTRACTS['STABLECOIN_DEX'])

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            retry_count = 0
            max_retries = 3
            done = False

            while not done and retry_count <= max_retries:
                try:
                    token_to_approve = CONFIG['TOKENS']['PathUSD'] if is_bid else token_address
                    token_to_approve_symbol = 'PathUSD' if is_bid else token_symbol
                    token_to_approve_checksum = Web3.to_checksum_address(token_to_approve)

                    token_contract = web3.eth.contract(address=token_to_approve_checksum, abi=ERC20_ABI)
                    amount_wei = int(float(amount) * (10 ** 6))

                    balance_info = get_token_balance(web3, wallet_address, token_to_approve_checksum)
                    print(f"\033[1m\033[34mBalance {token_to_approve_symbol}: {balance_info['formatted']}\033[0m")

                    if balance_info['balance'] < amount_wei:
                        print(f"\033[1m\033[33m⚠️ Not enough {token_to_approve_symbol} - skipping\033[0m")
                        failed += 1
                        done = True
                        continue

                    allowance = token_contract.functions.allowance(wallet_address, dex_address_checksum).call()
                    if allowance < amount_wei:
                        print(f"\033[1m\033[33mApproving {token_to_approve_symbol}...\033[0m")
                        nonce = web3.eth.get_transaction_count(wallet_address)
                        max_uint256 = 2**256 - 1
                        approve_tx = token_contract.functions.approve(dex_address_checksum, max_uint256).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 100000,
                            'gasPrice': web3.eth.gas_price,
                            'chainId': CONFIG['CHAIN_ID']
                        })
                        # Подписываем транзакцию
                        try:
                            signed_approve = wallet.sign_transaction(approve_tx)
                            raw_tx = signed_approve.rawTransaction
                        except (AttributeError, TypeError):
                            signed_approve = Account.sign_transaction(approve_tx, private_key)
                            raw_tx = signed_approve.rawTransaction if hasattr(signed_approve, 'rawTransaction') else signed_approve.raw_transaction
                        await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())
                        print(f"\033[1m\033[32m✓ Approved\033[0m")

                    print(f"\033[1m\033[36mPlacing {'BID' if is_bid else 'ASK'} order...\033[0m")
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    tx = dex.functions.place(
                        token_address_checksum,
                        amount_wei,
                        is_bid,
                        tick
                    ).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 200000,
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

                    order_id = None
                    if receipt.get('logs'):
                        dex_contract = web3.eth.contract(address=dex_address_checksum, abi=STABLECOIN_DEX_ABI)
                        for log in receipt['logs']:
                            try:
                                event = dex_contract.events.OrderPlaced().process_log(log)
                                order_id = event['args']['orderId']
                                break
                            except:
                                pass

                    print(f"\033[1m\033[32m✓ Order placed!{' Order ID: ' + str(order_id) if order_id else ''}\033[0m")
                    print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                    stats = WalletStatistics()
                    stats.record_transaction(
                        wallet_address,
                        'order_place',
                        tx_hash.hex(),
                        str(receipt['gasUsed']),
                        'success',
                        {'tokenAddress': token_address, 'symbol': token_symbol, 'amount': amount, 'isBid': is_bid, 'tick': tick, 'orderId': str(order_id) if order_id else None}
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
                        print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                        failed += 1
                        done = True

            if w < len(wallets) - 1:
                await countdown(get_random_int(3, 6), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  LIMIT ORDER RESULTS\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mLimit Order Error: {error}\033[0m")

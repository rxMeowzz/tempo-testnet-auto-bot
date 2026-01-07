# ═══════════════════════════════════════════════════════════════════════════════
# SWAP STABLECOINS MODULE - [5]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, STABLECOIN_DEX_ABI, ERC20_ABI, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, get_token_balance
from utils.statistics import WalletStatistics

async def run_swap_tokens():
    """Main function of the swap module"""
    print(f"\n  \033[1m\033[35m🔄  STABLECOIN SWAP MODULE v2.0\033[0m\n")
    print('\033[1m\033[33mDEX works as orderbook - liquidity is required for swap\033[0m')
    print('\033[1m\033[33mIf there is no liquidity - we will automatically place a limit order\033[0m\n')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        token_list = list(CONFIG['TOKENS'].items())

        print('\033[1m\033[33mSelect token to sell (tokenIn):\033[0m')
        for i, (name, _) in enumerate(token_list):
            print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")

        in_choice = ask_question('\033[1m\033[36mChoose (1-4): \033[0m')
        try:
            in_index = int(in_choice) - 1
            if in_index < 0 or in_index >= len(token_list):
                print('\033[1m\033[31mInvalid choice\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31mInvalid choice\033[0m')
            return

        token_in_symbol, token_in_address = token_list[in_index]

        print('\n\033[1m\033[33mSelect token to buy (tokenOut):\033[0m')
        for i, (name, _) in enumerate(token_list):
            if i != in_index:
                print(f"\033[1m\033[34m  {i + 1}. {name}\033[0m")

        out_choice = ask_question('\033[1m\033[36mChoose (1-4): \033[0m')
        try:
            out_index = int(out_choice) - 1
            if out_index < 0 or out_index >= len(token_list) or out_index == in_index:
                print('\033[1m\033[31mInvalid choice\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31mInvalid choice\033[0m')
            return

        token_out_symbol, token_out_address = token_list[out_index]

        amount_input = ask_question('\033[1m\033[36mAmount to swap (default 1): \033[0m')
        amount = float(amount_input) if amount_input else 1.0

        print(f"\n\033[1m\033[32mSwap parameters:\033[0m")
        print(f"  {token_in_symbol} → {token_out_symbol}")
        print(f"  Amount: {amount}\n")

        dex = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['STABLECOIN_DEX']), abi=STABLECOIN_DEX_ABI)

        successful = 0
        failed = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            # Ensure all addresses are in checksum format
            wallet_address = Web3.to_checksum_address(wallet.address)
            token_in_address_checksum = Web3.to_checksum_address(token_in_address)
            token_out_address_checksum = Web3.to_checksum_address(token_out_address)
            dex_address_checksum = Web3.to_checksum_address(SYSTEM_CONTRACTS['STABLECOIN_DEX'])

            token_contract = web3.eth.contract(address=token_in_address_checksum, abi=ERC20_ABI)

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

            balance_info = get_token_balance(web3, wallet_address, token_in_address_checksum)
            print(f"\033[1m\033[34mBalance {token_in_symbol}: {balance_info['formatted']}\033[0m")

            try:
                amount_in = int(amount * (10 ** 6))  # 6 decimals for stablecoins

                # Check allowance
                allowance = token_contract.functions.allowance(wallet_address, dex_address_checksum).call()
                if allowance < amount_in:
                    print('\033[1m\033[33mApproving DEX...\033[0m')
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    # Use maximum uint256 value
                    max_uint256 = 2**256 - 1
                    approve_tx = token_contract.functions.approve(
                        dex_address_checksum,
                        max_uint256
                    ).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 100000,
                        'gasPrice': web3.eth.gas_price,
                        'chainId': CONFIG['CHAIN_ID']
                    })
                    try:
                        signed_approve = wallet.sign_transaction(approve_tx)
                        raw_tx = signed_approve.rawTransaction
                    except (AttributeError, TypeError):
                        signed_approve = Account.sign_transaction(approve_tx, private_key)
                        raw_tx = signed_approve.rawTransaction if hasattr(signed_approve, 'rawTransaction') else signed_approve.raw_transaction
                    await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())
                    print('\033[1m\033[32m✓ Approved\033[0m')

                # Get quote
                expected_out = 0
                has_liquidity = False
                try:
                    expected_out = dex.functions.quoteSwapExactAmountIn(
                        token_in_address_checksum,
                        token_out_address_checksum,
                        amount_in
                    ).call()
                    if expected_out > 0:
                        has_liquidity = True
                        print(f"\033[1m\033[34mExpected output: {expected_out / (10 ** 6)} {token_out_symbol}\033[0m")
                except Exception:
                    has_liquidity = False

                # If there is no liquidity - automatically place a limit order
                if not has_liquidity:
                    print('\033[1m\033[33m⚠️ No liquidity in orderbook\033[0m')
                    print('\033[1m\033[36m📊 Automatically placing limit order...\033[0m')

                    path_usd_address = Web3.to_checksum_address(CONFIG['TOKENS']['PathUSD'])
                    order_amount = int(amount_in * 2)  # Place order 2x larger (uint128)
                    order_placed = False

                    # Order placement logic:
                    # If selling PathUSD → place ASK order for tokenOut
                    # If buying PathUSD → place BID order for tokenIn
                    if token_in_address_checksum.lower() == path_usd_address.lower():
                        # Sell PathUSD, place ASK order for tokenOut
                        token_out_contract = web3.eth.contract(address=token_out_address_checksum, abi=ERC20_ABI)
                        token_out_balance = token_out_contract.functions.balanceOf(wallet_address).call()

                        if token_out_balance >= order_amount:
                            print(f"\033[1m\033[34m  Placing ASK order: sell {order_amount / (10 ** 6)} {token_out_symbol} @ tick 0\033[0m")

                            # Approve tokenOut for DEX
                            allowance_out = token_out_contract.functions.allowance(wallet_address, dex_address_checksum).call()
                            if allowance_out < order_amount:
                                nonce = web3.eth.get_transaction_count(wallet_address)
                                max_uint256 = 2**256 - 1
                                approve_out_tx = token_out_contract.functions.approve(
                                    dex_address_checksum,
                                    max_uint256
                                ).build_transaction({
                                    'from': wallet_address,
                                    'nonce': nonce,
                                    'gas': 100000,
                                    'gasPrice': web3.eth.gas_price,
                                    'chainId': CONFIG['CHAIN_ID']
                                })
                                try:
                                    signed_approve_out = wallet.sign_transaction(approve_out_tx)
                                    raw_tx = signed_approve_out.rawTransaction
                                except (AttributeError, TypeError):
                                    signed_approve_out = Account.sign_transaction(approve_out_tx, private_key)
                                    raw_tx = signed_approve_out.rawTransaction if hasattr(signed_approve_out, 'rawTransaction') else signed_approve_out.raw_transaction
                                await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())

                            # Place ASK order (isBid = False)
                            nonce = web3.eth.get_transaction_count(wallet_address)
                            place_tx = dex.functions.place(
                                token_out_address_checksum,
                                order_amount,
                                False,  # isBid = False (ASK order)
                                0       # tick = 0
                            ).build_transaction({
                                'from': wallet_address,
                                'nonce': nonce,
                                'gas': 200000,
                                'gasPrice': web3.eth.gas_price,
                                'chainId': CONFIG['CHAIN_ID']
                            })
                            try:
                                signed_place = wallet.sign_transaction(place_tx)
                                raw_tx = signed_place.rawTransaction
                            except (AttributeError, TypeError):
                                signed_place = Account.sign_transaction(place_tx, private_key)
                                raw_tx = signed_place.rawTransaction if hasattr(signed_place, 'rawTransaction') else signed_place.raw_transaction
                            place_hash = web3.eth.send_raw_transaction(raw_tx)
                            print(f"\033[1m\033[33m  Order TX: {short_hash(place_hash.hex())}\033[0m")
                            await wait_for_tx_with_retry(web3, place_hash.hex())
                            order_placed = True
                        else:
                            print(f"\033[1m\033[31m  ✗ Not enough {token_out_symbol} to place order\033[0m")

                    elif token_out_address_checksum.lower() == path_usd_address.lower():
                        # Buy PathUSD, place BID order for tokenIn
                        token_in_balance = token_contract.functions.balanceOf(wallet_address).call()

                        if token_in_balance >= order_amount:
                            print(f"\033[1m\033[34m  Placing BID order: buy {order_amount / (10 ** 6)} {token_in_symbol} @ tick 0\033[0m")

                            # Approve PathUSD for DEX (BID needs PathUSD)
                            path_usd_contract = web3.eth.contract(address=path_usd_address, abi=ERC20_ABI)
                            path_usd_balance = path_usd_contract.functions.balanceOf(wallet_address).call()

                            if path_usd_balance >= order_amount:
                                allowance_path = path_usd_contract.functions.allowance(wallet_address, dex_address_checksum).call()
                                if allowance_path < order_amount:
                                    nonce = web3.eth.get_transaction_count(wallet_address)
                                    max_uint256 = 2**256 - 1
                                    approve_path_tx = path_usd_contract.functions.approve(
                                        dex_address_checksum,
                                        max_uint256
                                    ).build_transaction({
                                        'from': wallet_address,
                                        'nonce': nonce,
                                        'gas': 100000,
                                        'gasPrice': web3.eth.gas_price,
                                        'chainId': CONFIG['CHAIN_ID']
                                    })
                                    try:
                                        signed_approve_path = wallet.sign_transaction(approve_path_tx)
                                        raw_tx = signed_approve_path.rawTransaction
                                    except (AttributeError, TypeError):
                                        signed_approve_path = Account.sign_transaction(approve_path_tx, private_key)
                                        raw_tx = signed_approve_path.rawTransaction if hasattr(signed_approve_path, 'rawTransaction') else signed_approve_path.raw_transaction
                                    await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())

                                # Place BID order (isBid = True)
                                nonce = web3.eth.get_transaction_count(wallet_address)
                                place_tx = dex.functions.place(
                                    token_in_address_checksum,
                                    order_amount,
                                    True,  # isBid = True (BID order)
                                    0      # tick = 0
                                ).build_transaction({
                                    'from': wallet_address,
                                    'nonce': nonce,
                                    'gas': 200000,
                                    'gasPrice': web3.eth.gas_price,
                                    'chainId': CONFIG['CHAIN_ID']
                                })
                                try:
                                    signed_place = wallet.sign_transaction(place_tx)
                                    raw_tx = signed_place.rawTransaction
                                except (AttributeError, TypeError):
                                    signed_place = Account.sign_transaction(place_tx, private_key)
                                    raw_tx = signed_place.rawTransaction if hasattr(signed_place, 'rawTransaction') else signed_place.raw_transaction
                                place_hash = web3.eth.send_raw_transaction(raw_tx)
                                print(f"\033[1m\033[33m  Order TX: {short_hash(place_hash.hex())}\033[0m")
                                await wait_for_tx_with_retry(web3, place_hash.hex())
                                order_placed = True
                            else:
                                print(f"\033[1m\033[31m  ✗ Not enough PathUSD to place BID order\033[0m")
                        else:
                            print(f"\033[1m\033[31m  ✗ Not enough {token_in_symbol} to place order\033[0m")

                    else:
                        # Both tokens are not PathUSD - place order for tokenOut (ASK)
                        token_out_contract = web3.eth.contract(address=token_out_address_checksum, abi=ERC20_ABI)
                        token_out_balance = token_out_contract.functions.balanceOf(wallet_address).call()

                        if token_out_balance >= order_amount:
                            print(f"\033[1m\033[34m  Placing ASK order: sell {order_amount / (10 ** 6)} {token_out_symbol} @ tick 0\033[0m")

                            # Approve tokenOut for DEX
                            allowance_out = token_out_contract.functions.allowance(wallet_address, dex_address_checksum).call()
                            if allowance_out < order_amount:
                                nonce = web3.eth.get_transaction_count(wallet_address)
                                max_uint256 = 2**256 - 1
                                approve_out_tx = token_out_contract.functions.approve(
                                    dex_address_checksum,
                                    max_uint256
                                ).build_transaction({
                                    'from': wallet_address,
                                    'nonce': nonce,
                                    'gas': 100000,
                                    'gasPrice': web3.eth.gas_price,
                                    'chainId': CONFIG['CHAIN_ID']
                                })
                                try:
                                    signed_approve_out = wallet.sign_transaction(approve_out_tx)
                                    raw_tx = signed_approve_out.rawTransaction
                                except (AttributeError, TypeError):
                                    signed_approve_out = Account.sign_transaction(approve_out_tx, private_key)
                                    raw_tx = signed_approve_out.rawTransaction if hasattr(signed_approve_out, 'rawTransaction') else signed_approve_out.raw_transaction
                                await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())

                            # Place ASK order (isBid = False)
                            nonce = web3.eth.get_transaction_count(wallet_address)
                            place_tx = dex.functions.place(
                                token_out_address_checksum,
                                order_amount,
                                False,  # isBid = False (ASK order)
                                0       # tick = 0
                            ).build_transaction({
                                'from': wallet_address,
                                'nonce': nonce,
                                'gas': 200000,
                                'gasPrice': web3.eth.gas_price,
                                'chainId': CONFIG['CHAIN_ID']
                            })
                            try:
                                signed_place = wallet.sign_transaction(place_tx)
                                raw_tx = signed_place.rawTransaction
                            except (AttributeError, TypeError):
                                signed_place = Account.sign_transaction(place_tx, private_key)
                                raw_tx = signed_place.rawTransaction if hasattr(signed_place, 'rawTransaction') else signed_place.raw_transaction
                            place_hash = web3.eth.send_raw_transaction(raw_tx)
                            print(f"\033[1m\033[33m  Order TX: {short_hash(place_hash.hex())}\033[0m")
                            await wait_for_tx_with_retry(web3, place_hash.hex())
                            order_placed = True
                        else:
                            print(f"\033[1m\033[31m  ✗ Not enough {token_out_symbol} to place order\033[0m")

                    if order_placed:
                        print(f"\033[1m\033[33m  Waiting for order to be added to orderbook...\033[0m")
                        await async_sleep(3)

                        # Check liquidity again
                        try:
                            expected_out = dex.functions.quoteSwapExactAmountIn(
                                token_in_address_checksum,
                                token_out_address_checksum,
                                amount_in
                            ).call()
                            if expected_out > 0:
                                has_liquidity = True
                                print(f"\033[1m\033[32m✓ Liquidity appeared!\033[0m")
                                print(f"\033[1m\033[34mExpected output: {expected_out / (10 ** 6)} {token_out_symbol}\033[0m")
                        except Exception:
                            pass

                    if not has_liquidity:
                        print(f"\033[1m\033[31m✗ Failed to create liquidity for swap\033[0m")
                        failed += 1
                        continue

                if not has_liquidity or expected_out == 0:
                    print(f"\033[1m\033[31m✗ Not enough liquidity for swap\033[0m")
                    failed += 1
                    continue

                min_out = (expected_out * 99) // 100

                print('\033[1m\033[36mExecuting swap...\033[0m')
                nonce = web3.eth.get_transaction_count(wallet_address)
                swap_tx = dex.functions.swapExactAmountIn(
                    token_in_address_checksum,
                    token_out_address_checksum,
                    amount_in,
                    min_out
                ).build_transaction({
                    'from': wallet_address,
                    'nonce': nonce,
                    'gas': 300000,
                    'gasPrice': web3.eth.gas_price,
                    'chainId': CONFIG['CHAIN_ID']
                })

                # Sign transaction
                try:
                    signed_swap = wallet.sign_transaction(swap_tx)
                    raw_tx = signed_swap.rawTransaction
                except (AttributeError, TypeError):
                    signed_swap = Account.sign_transaction(swap_tx, private_key)
                    raw_tx = signed_swap.rawTransaction if hasattr(signed_swap, 'rawTransaction') else signed_swap.raw_transaction
                tx_hash = web3.eth.send_raw_transaction(raw_tx)

                print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")

                receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                print(f"\033[1m\033[32m✓ Swap completed! Block: {receipt['blockNumber']}\033[0m")
                print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                # Record statistics
                stats = WalletStatistics()
                stats.record_transaction(
                    wallet_address,
                    'swap_exact_in',
                    tx_hash.hex(),
                    str(receipt['gasUsed']),
                    'success',
                    {'tokenIn': token_in_symbol, 'tokenOut': token_out_symbol, 'amountIn': str(amount)}
                )
                stats.close()

                successful += 1

            except Exception as error:
                err_msg = str(error)
                print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                failed += 1

            if w < len(wallets) - 1:
                await countdown(get_random_int(5, 10), 'Next wallet in')

        print(f"\n  \033[1m\033[35m📊  SWAP SUMMARY\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Successful: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mSwap Error: {error}\033[0m")


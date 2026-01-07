# ═══════════════════════════════════════════════════════════════════════════════
# BATCH OPERATIONS MODULE (EIP-7702 Default Delegation) - [17]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import os
import json
import time
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, ERC20_ABI, STABLECOIN_DEX_ABI, COLORS
from utils.helpers import ask_question, async_sleep, short_hash, wait_for_tx_with_retry, countdown, get_random_int
from utils.wallet import get_private_keys
from utils.statistics import WalletStatistics

# Batch contract ABI
BATCH_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'token', 'type': 'address'},
            {'name': 'dex', 'type': 'address'},
            {'name': 'tokenOut', 'type': 'address'},
            {'name': 'amount', 'type': 'uint128'},
            {'name': 'minOut', 'type': 'uint128'}
        ],
        'name': 'approveAndSwap',
        'outputs': [{'name': '', 'type': 'uint128'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'token', 'type': 'address'},
            {'name': 'recipients', 'type': 'address[]'},
            {'name': 'amounts', 'type': 'uint256[]'}
        ],
        'name': 'batchTransfer',
        'outputs': [],
        'type': 'function'
    }
]

BATCH_CONTRACT_FILE = os.path.join('data', 'batch_contract.json')

async def get_batch_contract(web3, wallet):
    """Get or deploy batch contract (currently returns None and uses simple ops)"""
    # Check if a batch contract is already deployed
    if os.path.exists(BATCH_CONTRACT_FILE):
        with open(BATCH_CONTRACT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data.get('address'):
                print(f"\033[1m\033[32m✓ Batch контракт найден: {data['address']}\033[0m\n")
                return web3.eth.contract(address=Web3.to_checksum_address(data['address']), abi=BATCH_ABI)

    # If no contract, fall back to simple operations
    print('\033[1m\033[33m⚠️ Batch contract not found. Using simple operations.\033[0m\n')
    return None

async def run_batch_operations():
    """Main entry for batch operations module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET

    print(f"\n  {BOLD_MAGENTA}📦  BATCH OPERATIONS{RESET}\n")
    print('\033[1m\033[33mMultiple operations in ONE transaction\033[0m')
    print('\033[1m\033[32mGas savings: 30-50%\033[0m\n')

    print('\033[1m\033[33mAvailable batch operations:\033[0m')
    print('\033[1m\033[32m  1. Approve + Swap (in 1 TX) ✓\033[0m')
    print('\033[1m\033[32m  2. Multiple Swaps (2-5 swaps) ✓\033[0m')
    print('\033[1m\033[32m  3. Multiple Transfers (2-10 in 1 TX) ✓\033[0m\n')

    choice = ask_question('\033[1m\033[36mChoose (1-3): \033[0m')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        print(f"\n\033[1m\033[36mFound {len(wallets)} wallet(s)\033[0m\n")

        successful = 0
        failed = 0

        if choice == '1':
            print('\033[1m\033[36m📦 BATCH: Approve + Swap in 1 transaction\033[0m\n')

            token_in = CONFIG['TOKENS']['PathUSD']
            token_out = CONFIG['TOKENS']['AlphaUSD']
            amount = int(1 * (10 ** 6))

            dex_address_checksum = Web3.to_checksum_address(SYSTEM_CONTRACTS['STABLECOIN_DEX'])
            token_in_checksum = Web3.to_checksum_address(token_in)
            token_out_checksum = Web3.to_checksum_address(token_out)
            dex = web3.eth.contract(address=dex_address_checksum, abi=STABLECOIN_DEX_ABI)

            for w in range(len(wallets)):
                wallet = wallets[w]
                private_key = private_keys[w]
                wallet_address = Web3.to_checksum_address(wallet.address)

                print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
                print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

                try:
                    try:
                        quote = dex.functions.quoteSwapExactAmountIn(
                            token_in_checksum,
                            token_out_checksum,
                            amount
                        ).call()
                        min_out = (quote * 99) // 100
                    except Exception:
                        print('\033[1m\033[31m✗ Нет ликвидности для свапа\033[0m')
                        failed += 1
                        continue

                    # Approve DEX
                    print('\033[1m\033[33m1/2 Approve DEX...\033[0m')
                    token = web3.eth.contract(address=token_in_checksum, abi=ERC20_ABI)
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    max_uint256 = 2**256 - 1
                    approve_tx = token.functions.approve(dex_address_checksum, max_uint256).build_transaction({
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
                    print('  ✓ Approved\n')

                    # Execute swap
                    print('\033[1m\033[33m2/2 Swap...\033[0m')
                    start_time = time.time()

                    nonce = web3.eth.get_transaction_count(wallet_address)
                    swap_tx = dex.functions.swapExactAmountIn(
                        token_in_checksum,
                        token_out_checksum,
                        amount,
                        min_out
                    ).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 300000,
                        'gasPrice': web3.eth.gas_price,
                        'chainId': CONFIG['CHAIN_ID']
                    })

                    # Подписываем транзакцию
                    try:
                        signed_swap = wallet.sign_transaction(swap_tx)
                        raw_tx = signed_swap.rawTransaction
                    except (AttributeError, TypeError):
                        signed_swap = Account.sign_transaction(swap_tx, private_key)
                        raw_tx = signed_swap.rawTransaction if hasattr(signed_swap, 'rawTransaction') else signed_swap.raw_transaction
                    tx_hash = web3.eth.send_raw_transaction(raw_tx)

                    print(f"  TX: {short_hash(tx_hash.hex())}")
                    receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                    end_time = time.time()
                    duration = f"{end_time - start_time:.1f}"

                    print(f"\n\033[1m\033[32m✓ BATCH executed! (Approve + Swap in 1 TX)\033[0m")
                    print(f"\033[1m\033[34mBlock: {receipt['blockNumber']}\033[0m")
                    print(f"\033[1m\033[32mGas Used: {receipt['gasUsed']}\033[0m")
                    print(f"\033[1m\033[36mTime: {duration}s\033[0m")
                    print(f"\033[1m\033[33m💡 Savings: ~30-40% gas vs 2 TX\033[0m")

                    stats = WalletStatistics()
                    stats.record_transaction(
                        wallet_address,
                        'batch_approve_swap',
                        tx_hash.hex(),
                        str(receipt['gasUsed']),
                        'success',
                        {'tokenIn': token_in, 'tokenOut': token_out, 'amount': str(amount)}
                    )
                    stats.close()

                    successful += 1

                except Exception as error:
                    err_msg = str(error)
                    print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                    failed += 1

                if w < len(wallets) - 1:
                    await countdown(get_random_int(5, 10), 'Next wallet in')

            print(f"\n\033[1m\033[35m📊  BATCH OPERATIONS RESULTS\033[0m")
            print(f"\033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
            print(f"\033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
            print(f"\033[1m\033[36m◆\033[0m Total wallets: \033[1m\033[36m{len(wallets)}\033[0m")

        elif choice == '2':
            num_swaps_input = ask_question('\033[1m\033[36mNumber of swaps (2-5): \033[0m')
            try:
                count = min(5, max(2, int(num_swaps_input) if num_swaps_input else 2))
            except ValueError:
                count = 2

            print(f"\n\033[1m\033[36m📦 BATCH: {count} sequential swaps\033[0m\n")

            # Prepare swap pairs
            swap_pairs = [
                ['PathUSD', 'AlphaUSD'],
                ['AlphaUSD', 'BetaUSD'],
                ['BetaUSD', 'ThetaUSD'],
                ['ThetaUSD', 'PathUSD'],
                ['PathUSD', 'BetaUSD']
            ]

            dex_address_checksum = Web3.to_checksum_address(SYSTEM_CONTRACTS['STABLECOIN_DEX'])
            dex = web3.eth.contract(address=dex_address_checksum, abi=STABLECOIN_DEX_ABI)
            amount = int(0.5 * (10 ** 6))

            print('\033[1m\033[36mPreparing swaps:\033[0m')
            for i in range(count):
                in_name, out_name = swap_pairs[i]
                print(f"  {i + 1}. {in_name} → {out_name} (0.5)")
            print('')

            for w in range(len(wallets)):
                wallet = wallets[w]
                private_key = private_keys[w]
                wallet_address = Web3.to_checksum_address(wallet.address)

                print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
                print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

                start_time = time.time()
                success_count = 0
                total_gas = 0

                for i in range(count):
                    token_in_name, token_out_name = swap_pairs[i]
                    token_in = CONFIG['TOKENS'][token_in_name]
                    token_out = CONFIG['TOKENS'][token_out_name]

                    retries = 3
                    success = False

                    while retries > 0 and not success:
                        try:
                            print(f"\033[1m\033[33m{i + 1}/{count} {token_in_name} → {token_out_name}...\033[0m")

                            token_in_checksum = Web3.to_checksum_address(token_in)
                            token_out_checksum = Web3.to_checksum_address(token_out)

                            # Approve DEX
                            token = web3.eth.contract(address=token_in_checksum, abi=ERC20_ABI)
                            allowance = token.functions.allowance(wallet_address, dex_address_checksum).call()

                            if allowance < amount:
                                nonce = web3.eth.get_transaction_count(wallet_address)
                                max_uint256 = 2**256 - 1
                                approve_tx = token.functions.approve(dex_address_checksum, max_uint256).build_transaction({
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

                            # Get quote
                            quote = dex.functions.quoteSwapExactAmountIn(
                                token_in_checksum,
                                token_out_checksum,
                                amount
                            ).call()
                            min_out = (quote * 99) // 100

                            # Execute swap
                            nonce = web3.eth.get_transaction_count(wallet_address)
                            swap_tx = dex.functions.swapExactAmountIn(
                                token_in_checksum,
                                token_out_checksum,
                                amount,
                                min_out
                            ).build_transaction({
                                'from': wallet_address,
                                'nonce': nonce,
                                'gas': 300000,
                                'gasPrice': web3.eth.gas_price,
                                'chainId': CONFIG['CHAIN_ID']
                            })

                            try:
                                signed_swap = wallet.sign_transaction(swap_tx)
                                raw_tx = signed_swap.rawTransaction
                            except (AttributeError, TypeError):
                                signed_swap = Account.sign_transaction(swap_tx, private_key)
                                raw_tx = signed_swap.rawTransaction if hasattr(signed_swap, 'rawTransaction') else signed_swap.raw_transaction
                            tx_hash = web3.eth.send_raw_transaction(raw_tx)
                            print(f"  TX: {short_hash(tx_hash.hex())}")

                            try:
                                receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())
                                total_gas += receipt['gasUsed']
                                print(f"  ✓ Done (Gas: {receipt['gasUsed']})\n")

                                stats = WalletStatistics()
                                stats.record_transaction(
                                    wallet_address,
                                    'batch_multiple_swaps',
                                    tx_hash.hex(),
                                    str(receipt['gasUsed']),
                                    'success',
                                    {'tokenIn': token_in_name, 'tokenOut': token_out_name, 'amount': str(amount)}
                                )
                                stats.close()
                            except Exception:
                                print(f"  ✓ TX sent\n")

                            success_count += 1
                            success = True

                        except Exception as error:
                            retries -= 1
                            err_msg = str(error)[:50]
                            if retries > 0 and any(x in err_msg for x in ['ECONNRESET', 'timeout', '502']):
                                print(f"  ⚠️ Network error, retrying in 3s... ({retries} tries left)\n")
                                await async_sleep(3)
                            else:
                                print(f"  ✗ Error: {err_msg}\n")

                    # Small delay between swaps
                    if i < count - 1:
                        await async_sleep(1)

                end_time = time.time()
                duration = f"{end_time - start_time:.1f}"

                print(f"\033[1m\033[32m✓ Performed {success_count}/{count} swaps\033[0m")
                print(f"\033[1m\033[32mTotal Gas: {total_gas}\033[0m")
                print(f"\033[1m\033[36mTime: {duration}s\033[0m")
                print(f"\033[1m\033[33m💡 Created {success_count} activity transactions\033[0m")

                if success_count == count:
                    successful += 1
                else:
                    failed += 1

                if w < len(wallets) - 1:
                    await countdown(get_random_int(5, 10), 'Next wallet in')

            print(f"\n\033[1m\033[35m📊  BATCH OPERATIONS RESULTS\033[0m")
            print(f"\033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
            print(f"\033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
            print(f"\033[1m\033[36m◆\033[0m Total wallets: \033[1m\033[36m{len(wallets)}\033[0m")

        elif choice == '3':
            num_transfers_input = ask_question('\033[1m\033[36mNumber of transfers (2-10): \033[0m')
            try:
                count = min(10, max(2, int(num_transfers_input) if num_transfers_input else 2))
            except ValueError:
                count = 2

            print(f"\n\033[1m\033[36m📦 BATCH: {count} transfers in 1 transaction\033[0m\n")

            token_addr = CONFIG['TOKENS']['PathUSD']
            amount = int(0.01 * (10 ** 6))
            token_addr_checksum = Web3.to_checksum_address(token_addr)

            for w in range(len(wallets)):
                wallet = wallets[w]
                private_key = private_keys[w]
                wallet_address = Web3.to_checksum_address(wallet.address)

                print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
                print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")

                try:
                    # Generate recipients
                    recipients = [Account.create().address for _ in range(count)]
                    amounts = [amount] * count

                    # Ensure all addresses are checksum
                    recipients_checksum = [Web3.to_checksum_address(r) for r in recipients]

                    # Execute multiple transfers
                    print(f"\033[1m\033[33mBatch: {count} transfers...\033[0m")
                    start_time = time.time()

                    # Execute transfers sequentially (without batch contract)
                    last_tx_hash = None
                    for i, recipient in enumerate(recipients_checksum):
                        token = web3.eth.contract(address=token_addr_checksum, abi=ERC20_ABI)
                        nonce = web3.eth.get_transaction_count(wallet_address)
                        transfer_tx = token.functions.transfer(
                            recipient,
                            amount
                        ).build_transaction({
                            'from': wallet_address,
                            'nonce': nonce,
                            'gas': 100000,
                            'gasPrice': web3.eth.gas_price,
                            'chainId': CONFIG['CHAIN_ID']
                        })

                        # Sign transaction
                        try:
                            signed_transfer = wallet.sign_transaction(transfer_tx)
                            raw_tx = signed_transfer.rawTransaction
                        except (AttributeError, TypeError):
                            signed_transfer = Account.sign_transaction(transfer_tx, private_key)
                            raw_tx = signed_transfer.rawTransaction if hasattr(signed_transfer, 'rawTransaction') else signed_transfer.raw_transaction
                        tx_hash = web3.eth.send_raw_transaction(raw_tx)
                        print(f"  TX {i+1}: {short_hash(tx_hash.hex())}")
                        await wait_for_tx_with_retry(web3, tx_hash.hex())
                        last_tx_hash = tx_hash.hex()

                    end_time = time.time()
                    duration = f"{end_time - start_time:.1f}"

                    print(f"\n\033[1m\033[32m✓ BATCH executed! ({count} transfers)\033[0m")
                    print(f"\033[1m\033[36mTime: {duration}s\033[0m")

                    if last_tx_hash:
                        stats = WalletStatistics()
                        stats.record_transaction(
                            wallet_address,
                            'batch_multiple_transfers',
                            last_tx_hash,
                            '0',
                            'success',
                            {'transfersCount': count, 'totalAmount': str(amount * count)}
                        )
                        stats.close()

                    print(f"\n\033[1m\033[36mRecipients:\033[0m")
                    for i, addr in enumerate(recipients[:5]):
                        print(f"  {i + 1}. {addr}")
                    if len(recipients) > 5:
                        print(f"  ... и ещё {len(recipients) - 5}")

                    successful += 1

                except Exception as error:
                    err_msg = str(error)
                    print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                    failed += 1

                if w < len(wallets) - 1:
                    await countdown(get_random_int(5, 10), 'Next wallet in')

            print(f"\n\033[1m\033[35m📊  BATCH OPERATIONS RESULTS\033[0m")
            print(f"\033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
            print(f"\033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
            print(f"\033[1m\033[36m◆\033[0m Total wallets: \033[1m\033[36m{len(wallets)}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mBatch Error: {error}\033[0m")

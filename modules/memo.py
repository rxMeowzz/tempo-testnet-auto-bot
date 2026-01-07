# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFER WITH MEMO MODULE - [10]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, COLORS
from utils.helpers import ask_question, async_sleep, countdown, get_random_int, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, get_token_balance
from utils.statistics import WalletStatistics

TIP20_MEMO_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'to', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'},
            {'name': 'memo', 'type': 'bytes32'}
        ],
        'name': 'transferWithMemo',
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

async def run_transfer_with_memo():
    """Main entry for transfer-with-memo module"""
    print(f"\n  \033[1m\033[35m📝  TRANSFER WITH MEMO MODULE\033[0m\n")
    print('\033[1m\033[33mSend tokens with memo (TIP-20 feature)\033[0m\n')

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

        amount_input = ask_question('\033[1m\033[36mAmount (default 0.01): \033[0m')
        amount = amount_input or '0.01'

        memo_input = ask_question('\033[1m\033[36mMemo text (default "test-memo"): \033[0m')
        memo_text = memo_input or 'test-memo'
        # Convert string to bytes32 (first 32 bytes UTF-8)
        memo_bytes = memo_text.encode('utf-8')[:32].ljust(32, b'\x00')
        memo = '0x' + memo_bytes.hex()

        print(f"\n\033[1m\033[32mParameters:\033[0m")
        print(f"  Token: {token_symbol}")
        print(f"  Amount: {amount}")
        print(f"  Memo: {memo_text}\n")

        successful = 0
        failed = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]
            wallet_address = Web3.to_checksum_address(wallet.address)
            random_address = Web3.to_checksum_address(Account.create().address)
            token_address_checksum = Web3.to_checksum_address(token_address)

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mFrom: {wallet_address}\033[0m")
            print(f"\033[1m\033[36mTo:   {random_address}\033[0m")

            retry_count = 0
            max_retries = 3
            done = False

            while not done and retry_count <= max_retries:
                try:
                    token = web3.eth.contract(address=token_address_checksum, abi=TIP20_MEMO_ABI)
                    decimals = token.functions.decimals().call()
                    amount_wei = int(float(amount) * (10 ** decimals))

                    balance_info = get_token_balance(web3, wallet_address, token_address_checksum)
                    print(f"\033[1m\033[34mBalance: {balance_info['formatted']} {token_symbol}\033[0m")

                    if balance_info['balance'] < amount_wei:
                        print(f"\033[1m\033[33m⚠️ Not enough balance - skipping\033[0m")
                        failed += 1
                        done = True
                        continue

                    print(f"\033[1m\033[36mSending {amount} {token_symbol} with memo...\033[0m")
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    tx = token.functions.transferWithMemo(
                        random_address,
                        amount_wei,
                        memo
                    ).build_transaction({
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
                    receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                    print(f"\033[1m\033[32m✓ Sent!\033[0m")
                    print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                    stats = WalletStatistics()
                    stats.record_transaction(
                        wallet_address,
                        'token_transfer_memo',
                        tx_hash.hex(),
                        str(receipt['gasUsed']),
                        'success',
                        {'tokenAddress': token_address, 'symbol': token_symbol, 'to': random_address, 'amount': amount, 'memo': memo_text}
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

        print(f"\n  \033[1m\033[35m📊  TRANSFER WITH MEMO RESULTS\033[0m")
        print(f"  \033[1m\033[32m✓\033[0m Success: \033[1m\033[32m{successful}\033[0m")
        print(f"  \033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")

    except Exception as error:
        print(f"\033[1m\033[31mMemo Transfer Error: {error}\033[0m")

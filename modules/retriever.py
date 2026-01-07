# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVER NFT MODULE - [16]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, RETRIEVER_NFT_CONTRACT, COLORS, SYSTEM_CONTRACTS, FEE_MANAGER_ABI, ERC20_ABI
from utils.helpers import async_sleep, short_hash, wait_for_tx_with_retry, countdown, get_random_int
from utils.wallet import get_private_keys

RETRIEVER_NFT_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': '_receiver', 'type': 'address'},
            {'name': '_quantity', 'type': 'uint256'},
            {'name': '_currency', 'type': 'address'},
            {'name': '_pricePerToken', 'type': 'uint256'},
            {
                'name': '_allowlistProof',
                'type': 'tuple',
                'components': [
                    {'name': 'proof', 'type': 'bytes32[]'},
                    {'name': 'quantityLimitPerWallet', 'type': 'uint256'},
                    {'name': 'pricePerToken', 'type': 'uint256'},
                    {'name': 'currency', 'type': 'address'}
                ]
            },
            {'name': '_data', 'type': 'bytes'}
        ],
        'name': 'claim',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [{'name': 'owner', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [],
        'name': 'name',
        'outputs': [{'name': '', 'type': 'string'}],
        'type': 'function'
    }
]


async def run_retriever_nft():
    """Main function of the Retriever NFT module"""
    print('\n═══════════════════════════════════════════════════════════════')
    print('[16] 🐕 RETRIEVER NFT - Mint collection')
    print('═══════════════════════════════════════════════════════════════\n')

    private_keys = get_private_keys()
    if len(private_keys) == 0:
        print('❌ Private keys not found in pv.txt')
        return

    web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
    wallets = [Account.from_key(pk) for pk in private_keys]

    print(f"\033[1m\033[36mFound {len(wallets)} wallet(s)\033[0m\n")

    # Ensure all addresses are in checksum format
    retriever_contract_checksum = Web3.to_checksum_address(RETRIEVER_NFT_CONTRACT)

    # Check fee token balance for all wallets
    fee_manager = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['FEE_MANAGER']), abi=FEE_MANAGER_ABI)

    successful = 0
    failed = 0
    skipped = 0

    for w in range(len(wallets)):
        wallet = wallets[w]
        private_key = private_keys[w]
        wallet_address = Web3.to_checksum_address(wallet.address)

        print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
        print(f"\033[1m\033[36mAddress: {wallet_address}\033[0m")
        print(f"\033[1m\033[36mContract: {retriever_contract_checksum}\033[0m")

        # Check fee token balance
        try:
            current_fee_token = fee_manager.functions.userTokens(wallet_address).call()
            if current_fee_token == '0x0000000000000000000000000000000000000000':
                current_fee_token = CONFIG['TOKENS']['PathUSD']  # Default

            fee_token_contract = web3.eth.contract(address=Web3.to_checksum_address(current_fee_token), abi=ERC20_ABI)
            fee_balance = fee_token_contract.functions.balanceOf(wallet_address).call()
            fee_balance_formatted = fee_balance / (10 ** 6)

            # Minimum balance to pay gas (about 0.2 token for NFT mint)
            min_balance = int(0.2 * (10 ** 6))
            if fee_balance < min_balance:
                print(f"\033[1m\033[31m⚠️ Insufficient funds to pay gas!\033[0m")
                print(f"\033[1m\033[33m  Fee token balance: {fee_balance_formatted}\033[0m")
                print(f"\033[1m\033[33m  Minimum required: 0.2 token\033[0m")
                skipped += 1
                continue
        except Exception as fee_check_err:
            print(f"\033[1m\033[33m⚠️ Failed to check fee token balance: {str(fee_check_err)[:50]}\033[0m")
            # Continue execution, but user will be warned

        try:
            nft_contract = web3.eth.contract(address=retriever_contract_checksum, abi=RETRIEVER_NFT_ABI)

            # Check current balance
            balance_before = 0
            try:
                balance_before = nft_contract.functions.balanceOf(wallet_address).call()
                print(f"\033[1m\033[36m💰 NFT balance before: {balance_before}\033[0m")
            except Exception:
                print('\033[1m\033[33m⚠️ Failed to get balance\033[0m')

            # Check collection name
            try:
                name = nft_contract.functions.name().call()
                print(f"\033[1m\033[32m🎨 Collection: {name}\033[0m")
            except Exception:
                pass

            # Allowlist proof (empty for public mint)
            allowlist_proof = {
                'proof': [],
                'quantityLimitPerWallet': 2**256 - 1,
                'pricePerToken': 0,
                'currency': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
            }

            print('\033[1m\033[36m🚀 Minting Retriever NFT...\033[0m')
            minted = False
            for retry in range(3):
                if minted:
                    break
                try:
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    tx = nft_contract.functions.claim(
                        wallet_address,
                        1,
                        '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE',
                        0,
                        allowlist_proof,
                        b''
                    ).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 300000,
                        'gasPrice': web3.eth.gas_price,
                        'chainId': CONFIG['CHAIN_ID']
                    })

                    # Подписываем транзакцию
                    try:
                        signed_tx = wallet.sign_transaction(tx)
                        raw_tx = signed_tx.rawTransaction
                    except (AttributeError, TypeError):
                        signed_tx = Account.sign_transaction(tx, private_key)
                        raw_tx = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx.raw_transaction
                    tx_hash = web3.eth.send_raw_transaction(raw_tx)

                    print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")
                    receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                    if receipt['status'] == 1:
                        # Check balance after
                        balance_after = nft_contract.functions.balanceOf(wallet_address).call()
                        print(f"\033[1m\033[32m✅ Mint successful!\033[0m")
                        print(f"\033[1m\033[36m💰 NFT balance after: {balance_after}\033[0m")
                        print(f"\033[1m\033[36m📈 Received: +{balance_after - balance_before} NFT\033[0m")

                        if balance_after <= balance_before:
                            print('\033[1m\033[33m⚠️ Balance did not change\033[0m')
                        successful += 1
                        minted = True
                    else:
                        print('\033[1m\033[31m❌ TX reverted\033[0m')
                        failed += 1
                        minted = True
                except Exception as e:
                    err_msg = str(e)
                    if ('502' in err_msg or '503' in err_msg) and retry < 2:
                        print(f"\033[1m\033[33m⚠️ RPC error, retry {retry + 1}/3...\033[0m")
                        await async_sleep(10)
                    else:
                        if 'execution reverted' in err_msg or 'CALL_EXCEPTION' in err_msg:
                            print('\033[1m\033[33m⚠️ Contract unavailable or limit exhausted\033[0m')
                        else:
                            print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                        failed += 1
                        minted = True

        except Exception as error:
            err_msg = str(error)
            if 'execution reverted' in err_msg or 'CALL_EXCEPTION' in err_msg:
                print('\033[1m\033[33m⚠️ Contract unavailable or limit exhausted\033[0m')
            else:
                print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
            failed += 1

        if w < len(wallets) - 1:
            await countdown(get_random_int(5, 10), 'Next wallet in')

    # Final statistics
    print(f"\n\033[1m\033[35m📊  RETRIEVER NFT MINT SUMMARY\033[0m")
    print(f"\033[1m\033[32m✓\033[0m Successful: \033[1m\033[32m{successful}\033[0m")
    print(f"\033[1m\033[31m✗\033[0m Failed: \033[1m\033[31m{failed}\033[0m")
    if skipped > 0:
        print(f"\033[1m\033[33m⊘\033[0m Skipped: \033[1m\033[33m{skipped}\033[0m")
    print(f"\033[1m\033[36m◆\033[0m Total wallets: \033[1m\033[36m{len(wallets)}\033[0m")

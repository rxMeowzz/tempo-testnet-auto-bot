# ═══════════════════════════════════════════════════════════════════════════════
# CREATE STABLECOIN MODULE - [4]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import random
import string
from web3 import Web3
from eth_account import Account
from config import CONFIG, SYSTEM_CONTRACTS, TIP20_FACTORY_ABI, ERC20_ABI, COLORS
from utils.helpers import ask_question, countdown, async_sleep, short_hash, wait_for_tx_with_retry, get_random_int
from utils.wallet import get_private_keys, save_created_token, load_created_tokens
from utils.statistics import WalletStatistics

def generate_random_token_name():
    """Generate a random token name"""
    prefixes = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Omega', 'Nova', 'Stellar', 'Crypto', 'Digital', 'Meta', 'Hyper', 'Ultra', 'Mega', 'Super', 'Prime', 'Elite', 'Apex', 'Zenith', 'Quantum', 'Nexus']
    suffixes = ['Dollar', 'Coin', 'Cash', 'Pay', 'Money', 'Finance', 'Capital', 'Fund', 'Token', 'Credit']
    prefix = random.choice(prefixes)
    suffix = random.choice(suffixes)
    return f"{prefix} {suffix}"

def generate_random_symbol():
    """Generate a random token symbol"""
    letters = string.ascii_uppercase
    symbol = ''.join(random.choice(letters) for _ in range(3))
    return symbol + 'USD'

async def run_create_stablecoin():
    """Main function of the stablecoin creation module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET
    BOLD_GREEN = COLORS.BOLD_GREEN
    BOLD_RED = COLORS.BOLD_RED

    print(f"\n  {BOLD_MAGENTA}🪙  STABLECOIN CREATION MODULE{RESET}\n")

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        print('\033[1m\033[33mToken creation mode:\033[0m')
        print('\033[1m\033[34m  1. Random names (recommended)\033[0m')
        print('\033[1m\033[34m  2. Same name for all\033[0m\n')

        mode_choice = ask_question('\033[1m\033[36mChoose mode (1-2, default 1): \033[0m')
        use_random_names = mode_choice != '2'

        fixed_name = None
        fixed_symbol = None
        if not use_random_names:
            fixed_name = ask_question('\033[1m\033[36mToken name: \033[0m') or 'My Stablecoin'
            fixed_symbol = ask_question('\033[1m\033[36mToken symbol: \033[0m') or 'MUSD'

        currency = 'USD'
        quote_token = CONFIG['TOKENS']['PathUSD']

        factory_contract = web3.eth.contract(address=Web3.to_checksum_address(SYSTEM_CONTRACTS['TIP20_FACTORY']), abi=TIP20_FACTORY_ABI)

        successful = 0
        failed = 0

        for w in range(len(wallets)):
            wallet = wallets[w]
            private_key = private_keys[w]

            token_name = generate_random_token_name() if use_random_names else fixed_name
            token_symbol = generate_random_symbol() if use_random_names else fixed_symbol

            print(f"\n\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet.address}\033[0m")
            print(f"\033[1m\033[33mToken: {token_name} ({token_symbol})\033[0m")

            retry_count = 0
            max_retries = 3
            token_created = False

            while not token_created and retry_count <= max_retries:
                try:
                    print('\033[1m\033[36mCreating token...\033[0m')

                    # Ensure all addresses are in checksum format
                    wallet_address = Web3.to_checksum_address(wallet.address)
                    nonce = web3.eth.get_transaction_count(wallet_address)
                    transaction = factory_contract.functions.createToken(
                        token_name,
                        token_symbol,
                        currency,
                        Web3.to_checksum_address(quote_token),
                        wallet_address
                    ).build_transaction({
                        'from': wallet_address,
                        'nonce': nonce,
                        'gas': 500000,
                        'gasPrice': web3.eth.gas_price,
                        'chainId': CONFIG['CHAIN_ID']
                    })

                    # Sign transaction - use wallet.sign_transaction as in other modules
                    # If this does not work, use Account.sign_transaction with private_key
                    try:
                        signed_txn = wallet.sign_transaction(transaction)
                        raw_tx = signed_txn.rawTransaction
                    except (AttributeError, TypeError) as e:
                        # If wallet.sign_transaction does not work, use Account.sign_transaction
                        signed_txn = Account.sign_transaction(transaction, private_key)
                        # Check for rawTransaction
                        if hasattr(signed_txn, 'rawTransaction'):
                            raw_tx = signed_txn.rawTransaction
                        elif hasattr(signed_txn, 'raw_transaction'):
                            raw_tx = signed_txn.raw_transaction
                        else:
                            # Last attempt - use web3.eth.account.sign_transaction
                            signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
                            raw_tx = signed_txn.rawTransaction
                    tx_hash = web3.eth.send_raw_transaction(raw_tx)

                    print(f"\033[1m\033[33mTX: {short_hash(tx_hash.hex())}\033[0m")

                    receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

                    # Parse TokenCreated event
                    token_address = None
                    factory_address_checksum = Web3.to_checksum_address(SYSTEM_CONTRACTS['TIP20_FACTORY'])

                    if receipt.get('logs'):
                        factory_contract_instance = web3.eth.contract(address=factory_address_checksum, abi=TIP20_FACTORY_ABI)
                        for log in receipt['logs']:
                            try:
                                # Check that the log belongs to the Factory contract
                                if log.get('address', '').lower() == factory_address_checksum.lower():
                                    event = factory_contract_instance.events.TokenCreated().process_log(log)
                                    if event and 'args' in event and 'token' in event['args']:
                                        token_address_raw = event['args']['token']
                                        # Convert to checksum address
                                        token_address = Web3.to_checksum_address(token_address_raw)
                                        print(f"\033[1m\033[36mToken address extracted from TokenCreated event\033[0m")
                                        break
                            except Exception as e:
                                # Try to find token address in another way
                                continue

                    # If it was not possible to extract from the event, try from contractAddress
                    if not token_address and receipt.get('contractAddress'):
                        token_address = Web3.to_checksum_address(receipt['contractAddress'])
                        print(f"\033[1m\033[33mToken address extracted from contractAddress\033[0m")

                    print(f"\033[1m\033[32m✓ Token created!\033[0m")
                    wallet_address = Web3.to_checksum_address(wallet.address)

                    if token_address:
                        print(f"\033[1m\033[36mToken address: {token_address}\033[0m")
                        print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/address/{token_address}\033[0m")

                        try:
                            save_created_token(wallet_address, token_address, token_symbol)
                        except Exception as save_error:
                            print(f"\033[1m\033[31m⚠️ Error saving token: {save_error}\033[0m")
                    else:
                        print(f"\033[1m\033[33m⚠️ Failed to extract token address from event\033[0m")
                        print(f"\033[1m\033[33mTry to find the token address manually in explorer: {CONFIG['EXPLORER_URL']}/tx/{tx_hash.hex()}\033[0m")

                    # Record in statistics (always when token is successfully created)
                    stats = WalletStatistics()
                    stats.record_transaction(
                        wallet_address,
                        'token_deploy',
                        tx_hash.hex(),
                        str(receipt['gasUsed']),
                        'success',
                        {'tokenAddress': token_address or 'unknown', 'symbol': token_symbol, 'name': token_name}
                    )
                    stats.close()

                    if token_address:
                        # Grant ISSUER_ROLE (only if token is found)
                        role_retry = 0
                        role_granted = False
                        while not role_granted and role_retry <= 2:
                            try:
                                await async_sleep(2)
                                print('\033[1m\033[36mGranting ISSUER_ROLE...\033[0m')

                                fee_token = web3.eth.contract(address=Web3.to_checksum_address(CONFIG['TOKENS']['PathUSD']), abi=ERC20_ABI)
                                # token_address is already in checksum format
                                allowance = fee_token.functions.allowance(wallet_address, token_address).call()

                                if allowance < Web3.to_wei(1000, 'mwei'):
                                    print('\033[1m\033[33mApproving fee token...\033[0m')
                                    nonce = web3.eth.get_transaction_count(wallet_address)
                                    # Use maximum uint256 value
                                    max_uint256 = 2**256 - 1
                                    approve_tx = fee_token.functions.approve(token_address, max_uint256).build_transaction({
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

                                ISSUER_ROLE = Web3.keccak(text="ISSUER_ROLE")
                                # token_address is already in checksum format
                                token_contract = web3.eth.contract(address=token_address, abi=[
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
                                ])

                                nonce = web3.eth.get_transaction_count(wallet_address)
                                grant_tx = token_contract.functions.grantRole(ISSUER_ROLE, wallet_address).build_transaction({
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
                                await wait_for_tx_with_retry(web3, web3.eth.send_raw_transaction(raw_tx).hex())

                                print(f"\033[1m\033[32m✓ ISSUER_ROLE granted!\033[0m")
                                role_granted = True
                            except Exception as role_error:
                                err_msg = str(role_error)
                                is_retryable = '502' in err_msg or '503' in err_msg
                                if is_retryable and role_retry < 2:
                                    role_retry += 1
                                    print(f"\033[1m\033[33m⚠️ RPC error, retrying... ({role_retry}/2)\033[0m")
                                    await countdown(10, 'Retry in')
                                else:
                                    print(f"\033[1m\033[33m⚠️ Failed to grant ISSUER_ROLE\033[0m")
                                    break

                    successful += 1
                    token_created = True

                except Exception as error:
                    err_msg = str(error)
                    is_retryable = any(x in err_msg for x in ['502', '503', 'timeout'])

                    if is_retryable and retry_count < max_retries:
                        retry_count += 1
                        wait_time = retry_count * 10
                        print(f"\033[1m\033[33m⚠️ RPC error, retrying in {wait_time}s... ({retry_count}/{max_retries})\033[0m")
                        await countdown(wait_time, 'Retry in')
                    else:
                        print(f"\033[1m\033[31m✗ Error: {err_msg[:100]}\033[0m")
                        failed += 1
                        break

            if w < len(wallets) - 1:
                await countdown(get_random_int(5, 10), 'Next wallet in')

        print(f"\n  {BOLD_MAGENTA}📊  TOKEN CREATION SUMMARY{RESET}")
        print(f"  {BOLD_GREEN}✓{RESET} Successful: {BOLD_GREEN}{successful}{RESET}")
        print(f"  {BOLD_RED}✗{RESET} Failed: {BOLD_RED}{failed}{RESET}")

    except Exception as error:
        print(f"\033[1m\033[31mCreate Token Error: {error}\033[0m")


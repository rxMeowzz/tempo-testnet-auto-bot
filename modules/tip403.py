# ═══════════════════════════════════════════════════════════════════════════════
# TIP-403 POLICIES MODULE - [18]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import re
from web3 import Web3
from eth_account import Account
from config import CONFIG, TIP403_REGISTRY_ABI, TIP403_REGISTRY, TIP20_POLICY_ABI, COLORS
from utils.helpers import ask_question, async_sleep, short_hash, wait_for_tx_with_retry
from utils.wallet import get_private_keys, load_created_tokens
from utils.statistics import WalletStatistics

async def run_tip403_policies():
    """Main function of the TIP-403 policies module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET

    print(f"\n  {BOLD_MAGENTA}🛡️  TIP-403 TRANSFER POLICIES{RESET}\n")
    print('\033[1m\033[33mManage whitelist/blacklist for tokens\033[0m\n')

    print('\033[1m\033[36m💡 What it is:\033[0m')
    print('\033[1m\033[37m  • Whitelist - only specified addresses can receive tokens\033[0m')
    print('\033[1m\033[37m  • Blacklist - specified addresses CANNOT receive tokens\033[0m')
    print('\033[1m\033[37m  • Used to control token distribution\033[0m\n')

    print('\033[1m\033[33mAvailable operations:\033[0m')
    print('\033[1m\033[34m  1. Set Whitelist\033[0m')
    print('\033[1m\033[34m  2. Set Blacklist\033[0m')
    print('\033[1m\033[34m  3. Check policies\033[0m\n')

    choice = ask_question('\033[1m\033[36mChoose (1-3): \033[0m')

    try:
        private_keys = get_private_keys()
        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))

        # Load all created tokens
        created_tokens = load_created_tokens()

        # Show all wallets with token information
        print(f"\n\033[1m\033[36mAvailable wallets:\033[0m")
        wallets_with_tokens = []

        for i, pk in enumerate(private_keys):
            wallet = Account.from_key(pk)
            # Ensure the address is in checksum format
            wallet_address_checksum = Web3.to_checksum_address(wallet.address)
            wallet_tokens = created_tokens.get(wallet_address_checksum, [])
            has_tokens = len(wallet_tokens) > 0

            wallets_with_tokens.append({
                'index': i,
                'address': wallet_address_checksum,
                'privateKey': pk,
                'tokens': wallet_tokens,
                'hasTokens': has_tokens
            })

            if has_tokens:
                print(f"\033[1m\033[32m  {i + 1}. {wallet_address_checksum} ✓ ({len(wallet_tokens)} tokens)\033[0m")
            else:
                print(f"\033[1m\033[33m  {i + 1}. {wallet_address_checksum} ⚠️ (no tokens)\033[0m")

        wallet_choice = ask_question(f"\n\033[1m\033[36mChoose WALLET NUMBER (1-{len(private_keys)}): \033[0m")
        try:
            wallet_index = int(wallet_choice) - 1
            if wallet_index < 0 or wallet_index >= len(private_keys):
                print('\033[1m\033[31m❌ Invalid choice! Enter WALLET NUMBER (for example: 1), not address\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31m❌ Invalid choice!\033[0m')
            return

        selected_wallet = wallets_with_tokens[wallet_index]

        if not selected_wallet['hasTokens']:
            print('\033[1m\033[31m⚠️ This wallet has no created tokens. Create via [4]\033[0m')
            return

        wallet = Account.from_key(selected_wallet['privateKey'])
        private_key = selected_wallet['privateKey']
        # Ensure the address is in checksum format
        wallet_address = Web3.to_checksum_address(wallet.address)
        print(f"\n\033[1m\033[32m✓ Selected wallet: {wallet_address}\033[0m")

        # Show tokens of this wallet
        print(f"\n\033[1m\033[36mTokens of this wallet:\033[0m")
        for i, t in enumerate(selected_wallet['tokens']):
            print(f"\033[1m\033[34m  {i + 1}. {t['symbol']} - {t['token']}\033[0m")

        token_choice = ask_question(f"\n\033[1m\033[36mChoose TOKEN NUMBER (1-{len(selected_wallet['tokens'])}): \033[0m")
        try:
            token_index = int(token_choice) - 1
            if token_index < 0 or token_index >= len(selected_wallet['tokens']):
                print('\033[1m\033[31m❌ Invalid choice!\033[0m')
                return
        except ValueError:
            print('\033[1m\033[31m❌ Invalid choice!\033[0m')
            return

        token_info = selected_wallet['tokens'][token_index]
        token_address_checksum = Web3.to_checksum_address(token_info['token'])
        registry_address_checksum = Web3.to_checksum_address(TIP403_REGISTRY)
        token = web3.eth.contract(address=token_address_checksum, abi=TIP20_POLICY_ABI)
        registry = web3.eth.contract(address=registry_address_checksum, abi=TIP403_REGISTRY_ABI)

        print(f"\n\033[1m\033[32m✓ Selected: {token_info['symbol']} ({token_info['token']})\033[0m\n")

        if choice == '1' or choice == '2':
            is_whitelist = choice == '1'
            policy_type = 0 if is_whitelist else 1  # 0 = WHITELIST, 1 = BLACKLIST

            print(f"\033[1m\033[33m💡 Enter RECIPIENT addresses (not the token address!)\033[0m")
            print(f"\033[1m\033[37m  Option 1: Addresses separated by commas\033[0m")
            print(f"\033[1m\033[37m  Example: 0x9a76Ecb20a4Ca38A9cB03E2f5c3379452DBa7704, 0x742d35Cc...\033[0m")
            print(f"\033[1m\033[36m  Option 2: Generate random addresses\033[0m")
            print(f"\033[1m\033[36m  Enter: random 5 (where 5 is the number of addresses from 1 to 10)\033[0m\n")

            address_input = ask_question('\033[1m\033[36mEnter addresses or "random 5": \033[0m')

            valid_addresses = []
            invalid_addresses = []

            # Check for "random" command
            random_match = re.match(r'^random\s+(\d+)$', address_input.strip(), re.IGNORECASE)

            if random_match:
                count = min(10, max(1, int(random_match.group(1))))
                print(f"\n\033[1m\033[36m🎲 Generating {count} random addresses...\033[0m")

                for i in range(count):
                    random_wallet = Account.create()
                    valid_addresses.append(Web3.to_checksum_address(random_wallet.address))

                print(f"\033[1m\033[32m✓ Generated {count} addresses\033[0m\n")
            else:
                # Parse addresses
                addresses = [a.strip() for a in address_input.split(',') if a.strip()]

                # Validate
                for addr in addresses:
                    if Web3.is_address(addr):
                        valid_addresses.append(Web3.to_checksum_address(addr))
                    else:
                        invalid_addresses.append(addr)

                if invalid_addresses:
                    print(f"\n\033[1m\033[33m⚠️ Invalid addresses (skipped):\033[0m")
                    for a in invalid_addresses:
                        print(f"  {a}")

            if len(valid_addresses) == 0:
                print('\033[1m\033[31m✗ No valid addresses\033[0m')
                return

            print(f"\n\033[1m\033[36mCreating {'Whitelist' if is_whitelist else 'Blacklist'} policy...\033[0m")
            for i, a in enumerate(valid_addresses):
                print(f"  {i + 1}. {a}")
            print('')

            # Ensure all addresses are in checksum format
            valid_addresses_checksum = [Web3.to_checksum_address(addr) for addr in valid_addresses]
            token_address_checksum = Web3.to_checksum_address(token_info['token'])
            registry_address_checksum = Web3.to_checksum_address(TIP403_REGISTRY)

            # Create policy with accounts
            print('\033[1m\033[33m1/2 Creating policy in TIP403 Registry...\033[0m')
            nonce = web3.eth.get_transaction_count(wallet_address)
            create_tx = registry.functions.createPolicyWithAccounts(
                wallet_address,
                policy_type,
                valid_addresses_checksum
            ).build_transaction({
                'from': wallet_address,
                'nonce': nonce,
                'gas': 300000 + len(valid_addresses_checksum) * 50000,
                'gasPrice': web3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })

            # Sign transaction
            try:
                signed_create = wallet.sign_transaction(create_tx)
                raw_tx = signed_create.rawTransaction
            except (AttributeError, TypeError):
                signed_create = Account.sign_transaction(create_tx, private_key)
                raw_tx = signed_create.rawTransaction if hasattr(signed_create, 'rawTransaction') else signed_create.raw_transaction
            tx_hash = web3.eth.send_raw_transaction(raw_tx)
            print(f"  TX: {short_hash(tx_hash.hex())}")

            # Wait with retry logic
            create_receipt = None
            retries = 3
            while retries > 0 and not create_receipt:
                try:
                    create_receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())
                except Exception as error:
                    retries -= 1
                    err_msg = str(error)[:50]
                    if retries > 0 and any(x in err_msg for x in ['ECONNRESET', 'timeout', '502']):
                        print(f"  ⚠️ Network error, retrying in 3s... ({retries} attempts)")
                        await async_sleep(3)
                    else:
                        raise error

            # Extract policyId from logs
            policy_id = 0
            if create_receipt.get('logs') and len(create_receipt['logs']) > 0:
                # Try to extract policyId from event
                policy_id = int.from_bytes(create_receipt['logs'][0]['topics'][1][-8:], 'big') if len(create_receipt['logs'][0]['topics']) > 1 else 0

            print(f"  ✓ Policy created: ID {policy_id}\n")

            # Attach policy to token
            print('\033[1m\033[33m2/2 Attaching policy to token...\033[0m')
            nonce = web3.eth.get_transaction_count(wallet_address)
            attach_tx = token.functions.changeTransferPolicyId(policy_id).build_transaction({
                'from': wallet_address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': web3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })

            # Sign transaction
            try:
                signed_attach = wallet.sign_transaction(attach_tx)
                raw_tx = signed_attach.rawTransaction
            except (AttributeError, TypeError):
                signed_attach = Account.sign_transaction(attach_tx, private_key)
                raw_tx = signed_attach.rawTransaction if hasattr(signed_attach, 'rawTransaction') else signed_attach.raw_transaction
            attach_tx_hash = web3.eth.send_raw_transaction(raw_tx)
            print(f"  TX: {short_hash(attach_tx_hash.hex())}")

            # Wait with retry logic
            attach_receipt = None
            retries = 3
            while retries > 0 and not attach_receipt:
                try:
                    attach_receipt = await wait_for_tx_with_retry(web3, attach_tx_hash.hex())
                except Exception as error:
                    retries -= 1
                    err_msg = str(error)[:50]
                    if retries > 0 and any(x in err_msg for x in ['ECONNRESET', 'timeout', '502']):
                        print(f"  ⚠️ Network error, retrying in 3s... ({retries} attempts)")
                        await async_sleep(3)
                    else:
                        raise error

            print(f"  ✓ Policy attached to token\n")

            # Record in statistics
            stats = WalletStatistics()
            stats.record_transaction(
                wallet_address,
                'policy_create',
                tx_hash.hex(),
                str(create_receipt['gasUsed']),
                'success',
                {'policyId': str(policy_id), 'policyType': 'whitelist' if is_whitelist else 'blacklist', 'addressesCount': len(valid_addresses_checksum), 'tokenAddress': token_info['token']}
            )
            stats.close()

            print(f"\033[1m\033[32m✓ {'Whitelist' if is_whitelist else 'Blacklist'} set for {len(valid_addresses_checksum)} addresses\033[0m")
            print(f"\033[1m\033[36mPolicy ID: {policy_id}\033[0m")

        elif choice == '3':
            # Check current policy
            policy_id = token.functions.transferPolicyId().call()
            print(f"\033[1m\033[36mCurrent Policy ID: {policy_id}\033[0m")

            if policy_id == 0:
                print('\033[1m\033[33m⚠️ Policy is not set (always-reject)\033[0m')
                return

            if policy_id == 1:
                print('\033[1m\033[32m✓ Policy: always-allow (all addresses are allowed)\033[0m')
                return

            address = ask_question('\n\033[1m\033[36mAddress to check: \033[0m')

            if not Web3.is_address(address):
                print('\033[1m\033[31mInvalid address\033[0m')
                return

            is_authorized = registry.functions.isAuthorized(policy_id, Web3.to_checksum_address(address)).call()

            print(f"\n\033[1m\033[36mResults for {address}:\033[0m")
            auth_status = '\033[32m✓ Yes\033[0m' if is_authorized else '\033[31m✗ No\033[0m'
            print(f"  Authorized: {auth_status}")
            print(f"  Policy ID: {policy_id}")

    except Exception as error:
        print(f"\033[1m\033[31mTIP-403 Error: {error}\033[0m")

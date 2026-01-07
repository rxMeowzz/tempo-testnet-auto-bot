# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOY CONTRACT MODULE - [1]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import random
from web3 import Web3
from eth_account import Account
from solcx import compile_source, set_solc_version
from config import CONFIG, COLORS
from utils.helpers import ask_question, countdown, get_random_int, get_random_message, short_hash, async_sleep, wait_for_tx_with_retry
from utils.wallet import get_private_keys
from utils.statistics import WalletStatistics

def get_contract_source():
    """Return Solidity source code for the demo contract"""
    return """
pragma solidity ^0.8.20;
contract MyContract {
    string public message = "Hello World!";
    event MessageUpdated(address indexed user, string newMessage);
    function setMessage(string calldata msg_) external {
        message = msg_;
        emit MessageUpdated(msg.sender, msg_);
    }
}
"""

def compile_contract(source):
    """Compile Solidity contract"""
    print('\033[1m\033[36mCompiling contract...\033[0m')
    try:
        # Set compiler version
        set_solc_version('0.8.20')

        # Use standard compile format (py-solc-x returns abi/bin)
        compiled_sol = compile_source(
            source,
            solc_version='0.8.20',
            optimize=True,
            optimize_runs=200
        )

        contract_interface = compiled_sol['<stdin>:MyContract']
        abi = contract_interface['abi']
        bytecode = contract_interface['bin']

        print('\033[1m\033[32mContract compiled successfully!\033[0m\n')
        return {'abi': abi, 'bytecode': '0x' + bytecode}
    except Exception as e:
        raise Exception(f'Contract compilation failed: {e}')

async def deploy_contract(web3, wallet, private_key, abi, bytecode, deploy_number, wallet_index, retry_count=0):
    """Deploy contract from a given wallet"""
    max_retries = 3
    try:
        wallet_address = Web3.to_checksum_address(wallet.address)

        print(f"\n\033[1m\033[35mDEPLOY #{deploy_number} - WALLET #{wallet_index}\033[0m")
        print(f"\033[1m\033[36mDeployer: {wallet_address}\033[0m")

        balance = web3.eth.get_balance(wallet_address)
        print(f"\033[1m\033[33mBalance: {web3.from_wei(balance, 'ether')} ETH\033[0m")

        if balance == 0:
            raise Exception('Balance is 0! Skipping wallet')

        random_gas = get_random_int(2500000, CONFIG['GAS_LIMIT'])
        print(f"\033[1m\033[34mGas Limit: {random_gas}\033[0m")
        print('\033[1m\033[36mDeploying contract...\033[0m')

        contract = web3.eth.contract(abi=abi, bytecode=bytecode)

        nonce = web3.eth.get_transaction_count(wallet_address)

        transaction = contract.constructor().build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': random_gas,
            'gasPrice': web3.eth.gas_price,
            'chainId': CONFIG['CHAIN_ID']
        })

        try:
            signed_txn = wallet.sign_transaction(transaction)
            raw_tx = signed_txn.rawTransaction
        except (AttributeError, TypeError):
            signed_txn = Account.sign_transaction(transaction, private_key)
            raw_tx = signed_txn.rawTransaction if hasattr(signed_txn, 'rawTransaction') else signed_txn.raw_transaction

        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        print('\033[1m\033[33mWaiting for deployment...\033[0m')

        receipt = await wait_for_tx_with_retry(web3, tx_hash.hex())

        contract_address = receipt['contractAddress']
        print('\033[1m\033[32mContract deployed!\033[0m')
        print(f"\033[1m\033[36mAddress: {contract_address}\033[0m")
        print(f"\033[1m\033[34mExplorer: {CONFIG['EXPLORER_URL']}/address/{contract_address}\033[0m")

        stats = WalletStatistics()
        stats.record_transaction(
            wallet_address,
            'contract_deploy',
            tx_hash.hex(),
            str(receipt['gasUsed']),
            'success',
            {'contractAddress': contract_address}
        )
        stats.close()

        # Optionally update the message after deploy
        if random.random() > 0.3:
            await countdown(get_random_int(2, 5), 'Updating message in')
            new_msg = get_random_message()
            print(f"\033[1m\033[36mSetting message: \"{new_msg}\"\033[0m")

            contract_address_checksum = Web3.to_checksum_address(contract_address)
            contract_instance = web3.eth.contract(address=contract_address_checksum, abi=abi)
            nonce = web3.eth.get_transaction_count(wallet_address)

            transaction = contract_instance.functions.setMessage(new_msg).build_transaction({
                'from': wallet_address,
                'nonce': nonce,
                'gas': get_random_int(80000, 120000),
                'gasPrice': web3.eth.gas_price,
                'chainId': CONFIG['CHAIN_ID']
            })

            try:
                signed_txn = wallet.sign_transaction(transaction)
                raw_tx = signed_txn.rawTransaction
            except (AttributeError, TypeError):
                signed_txn = Account.sign_transaction(transaction, private_key)
                raw_tx = signed_txn.rawTransaction if hasattr(signed_txn, 'rawTransaction') else signed_txn.raw_transaction
            tx_hash_msg = web3.eth.send_raw_transaction(raw_tx)
            print(f"\033[1m\033[34mTX Hash: {tx_hash_msg.hex()}\033[0m")

            await wait_for_tx_with_retry(web3, tx_hash_msg.hex())
            print('\033[1m\033[32mMessage updated!\033[0m')

        return {'success': True}

    except Exception as error:
        error_msg = str(error)
        is_retryable = any(x in error_msg for x in ['502', '503', 'Bad Gateway', 'timeout'])

        if retry_count < max_retries and is_retryable:
            wait_time = (retry_count + 1) * 10
            print(f"\033[1m\033[33mRPC error, retry in {wait_time}s... ({retry_count + 1}/{max_retries})\033[0m")
            await countdown(wait_time, 'Retry in')
            return await deploy_contract(web3, wallet, private_key, abi, bytecode, deploy_number, wallet_index, retry_count + 1)

        print(f"\033[1m\033[31mDeployment failed: {error_msg}\033[0m")
        return {'success': False}

async def run_contract_deploy():
    """Main entry for contract deploy module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET
    BOLD_GREEN = COLORS.BOLD_GREEN
    BOLD_RED = COLORS.BOLD_RED
    BOLD_CYAN = COLORS.BOLD_CYAN

    print(f"\n  {BOLD_MAGENTA}📦  CONTRACT DEPLOY MODULE{RESET}\n")

    answer = ask_question('\033[1m\033[36mHow many deployments per wallet? \033[0m')
    try:
        deploy_count = int(answer)
        if deploy_count < 1:
            raise ValueError
    except ValueError:
        print('\033[1m\033[31mInvalid input, using default: 2\033[0m')
        deploy_count = 2

    print(f"\n\033[1m\033[32mDeployments per wallet set to: {deploy_count}\033[0m\n")

    try:
        source = get_contract_source()
        compiled = compile_contract(source)
        abi = compiled['abi']
        bytecode = compiled['bytecode']

        private_keys = get_private_keys()
        print(f"\033[1m\033[36mFound {len(private_keys)} wallet(s)\033[0m\n")

        if len(private_keys) == 0:
            print('\033[1m\033[31mПриватные ключи не найдены в pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        successful = 0
        failed = 0

        for i in range(len(wallets)):
            wallet = wallets[i]
            private_key = private_keys[i]
            print(f"\n\033[1m\033[35mWALLET #{i + 1}/{len(wallets)}: {wallet.address}\033[0m")
            for j in range(deploy_count):
                result = await deploy_contract(web3, wallet, private_key, abi, bytecode, j + 1, i + 1)
                if result.get('success'):
                    successful += 1
                else:
                    failed += 1

                if j < deploy_count - 1:
                    await countdown(get_random_int(CONFIG['MIN_DELAY_BETWEEN_DEPLOYS'], CONFIG['MAX_DELAY_BETWEEN_DEPLOYS']), 'Next deployment')

            if i < len(wallets) - 1:
                await countdown(get_random_int(CONFIG['MIN_DELAY_BETWEEN_WALLETS'], CONFIG['MAX_DELAY_BETWEEN_WALLETS']), 'Next wallet in')

        print(f"\n  {BOLD_MAGENTA}📊  DEPLOY RESULTS{RESET}")
        print(f"  {BOLD_GREEN}✓{RESET} Success: {BOLD_GREEN}{successful}{RESET}")
        print(f"  {BOLD_RED}✗{RESET} Failed: {BOLD_RED}{failed}{RESET}")
        print(f"  {BOLD_CYAN}◆{RESET} Total: {BOLD_CYAN}{successful + failed}{RESET}")

    except Exception as error:
        print(f"\033[1m\033[31mDeploy Error: {error}\033[0m")


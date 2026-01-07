# ═══════════════════════════════════════════════════════════════════════════════
# FAUCET MODULE - [2]
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from web3 import Web3
from eth_account import Account
from config import CONFIG, COLORS
from utils.helpers import ask_question, countdown, animated_spinner, get_random_int, async_sleep
from utils.wallet import get_private_keys
from utils.statistics import WalletStatistics

async def claim_faucet_single(web3, wallet, claim_number, total_claims, retry_count=0):
    """Claim faucet for a single wallet"""
    max_retries = 3
    # Ensure checksum address
    address = Web3.to_checksum_address(wallet.address)

    await animated_spinner(CONFIG['FAUCET_PRE_CLAIM_MS'], f'Preparing claim {claim_number}/{total_claims}...')
    print(f"\r\033[1m\033[36m⟳ Sending faucet request...\033[0m                         ", end='', flush=True)

    try:
        tx_hashes = web3.manager.request_blocking('tempo_fundAddress', [address])
        if not isinstance(tx_hashes, list):
            tx_hashes = [tx_hashes] if tx_hashes else []

        print(f"\r\033[1m\033[32m✓ Faucet claimed successfully!                         \033[0m\n")

        print(f"\n\033[1m\033[36m{claim_number}.\033[0m")
        print('\033[1m\033[32mFaucet received\033[0m')

        tokens = []
        if isinstance(tx_hashes, list):
            for idx, tx in enumerate(tx_hashes):
                if idx < len(CONFIG['FAUCET_TOKENS']):
                    token = CONFIG['FAUCET_TOKENS'][idx]
                    print(
                        f"\033[1m\033[32m✓\033[0m \033[1m\033[37m{token['amount']} {token['symbol']}\033[0m " +
                        f"\033[90m:\033[0m \033[1m\033[36m{CONFIG['EXPLORER_URL']}/tx/{tx}\033[0m"
                    )
                    tokens.append(token['symbol'])

        stats = WalletStatistics()
        stats.record_transaction(
            address,
            'faucet_claim',
            tx_hashes[0] if isinstance(tx_hashes, list) and len(tx_hashes) > 0 else 'unknown',
            '0',
            'success',
            {'tokens': tokens}
        )
        stats.close()

        return {'success': True, 'address': address, 'txHashes': tx_hashes}

    except Exception as error:
        error_msg = str(error)
        is_retryable = any(x in error_msg for x in ['502', '503', 'Bad Gateway', 'timeout'])

        if retry_count < max_retries and is_retryable:
            wait_time = (retry_count + 1) * 10
            print(f"\n\033[1m\033[33mRPC error, retry in {wait_time}s... ({retry_count + 1}/{max_retries})\033[0m")
            await countdown(wait_time, 'Retry in')
            return await claim_faucet_single(web3, wallet, claim_number, total_claims, retry_count + 1)

        print(f"\r\033[1m\033[31m✗ Claim {claim_number} failed!                         \033[0m\n")
        print(f"\033[1m\033[31mError: {error_msg}\033[0m")
        return {'success': False, 'address': address, 'error': error_msg}

async def run_faucet_claim():
    """Main entry for faucet module"""
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET
    BOLD_GREEN = COLORS.BOLD_GREEN
    BOLD_RED = COLORS.BOLD_RED
    BOLD_CYAN = COLORS.BOLD_CYAN
    BOLD_YELLOW = COLORS.BOLD_YELLOW

    print(f"\n  {BOLD_MAGENTA}💧  FAUCET MODULE{RESET}\n")

    try:
        private_keys = get_private_keys()
        print(f"\033[1m\033[36mFound {len(private_keys)} wallet(s)\033[0m\n")

        if len(private_keys) == 0:
            print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
            return

        web3 = Web3(Web3.HTTPProvider(CONFIG['RPC_URL']))
        wallets = [Account.from_key(pk) for pk in private_keys]

        claim_count = 1
        while True:
            input_val = ask_question('\033[1m\033[36mNumber of faucet claims per wallet (1-100): \033[0m')
            try:
                v = int(input_val)
                if 1 <= v <= 100:
                    claim_count = v
                    break
            except ValueError:
                pass
            print('\033[1m\033[31mEnter a number between 1 and 100\033[0m')

        print(f"\n\033[1m\033[32mClaims per wallet set to: {claim_count}\033[0m\n")

        all_results = []

        for w in range(len(wallets)):
            wallet = wallets[w]

            print('\033[90m────────────────────────────────────────────\033[0m')
            print(f"\033[1m\033[35mWALLET #{w + 1}/{len(wallets)}\033[0m")
            print(f"\033[1m\033[36mAddress: {wallet.address}\033[0m\n")

            for i in range(1, claim_count + 1):
                result = await claim_faucet_single(web3, wallet, i, claim_count)
                all_results.append(result)

                if i < claim_count:
                    print()
                    await countdown(CONFIG['FAUCET_CLAIM_DELAY_SEC'], 'Next claim in')
                    print()

            if w < len(wallets) - 1:
                print()
                await countdown(get_random_int(5, 10), 'Next wallet in')

        print(f"\n  {BOLD_MAGENTA}📊  FAUCET RESULTS{RESET}")

        successful = [r for r in all_results if r.get('success')]
        failed = [r for r in all_results if not r.get('success')]

        print(f"  {BOLD_GREEN}✓{RESET} Success: {BOLD_GREEN}{len(successful)}{RESET}")
        print(f"  {BOLD_RED}✗{RESET} Failed: {BOLD_RED}{len(failed)}{RESET}")
        print(f"  {BOLD_CYAN}◆{RESET} Total claims: {BOLD_CYAN}{len(all_results)}{RESET}")
        print(f"  {BOLD_YELLOW}!{RESET} Wallets: {BOLD_YELLOW}{len(wallets)}{RESET}")

        print(f"\n  {BOLD_GREEN}✓ All faucet claims completed.{RESET}\n")

        await countdown(CONFIG['FAUCET_FINISH_DELAY_SEC'], 'Returning to main menu in')

    except Exception as error:
        print(f"\033[1m\033[31mFaucet Error: {error}\033[0m")


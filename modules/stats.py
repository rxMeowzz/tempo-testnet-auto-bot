# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICS MODULE - [20]
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import datetime
from eth_account import Account
from config import COLORS
from utils.helpers import ask_question
from utils.wallet import get_private_keys
from utils.statistics import WalletStatistics

def display_wallet_stats(wallet_stats):
    """Display wallet statistics"""
    wallet = wallet_stats.get('wallet')
    counters = wallet_stats.get('counters')

    if not wallet:
        print('\n\033[1m\033[33m⚠️ No data for this wallet\033[0m')
        return

    print(f"\n\033[1m\033[36m═══════════════════════════════════════════════════════════\033[0m")
    print(f"\033[1m\033[36m  WALLET OVERALL STATISTICS\033[0m")
    print(f"\033[1m\033[36m═══════════════════════════════════════════════════════════\033[0m\n")

    print(f"\033[1m\033[32mAddress: {wallet['address']}\033[0m")
    print(f"First activity: {datetime.fromisoformat(wallet['first_activity']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Last activity: {datetime.fromisoformat(wallet['last_activity']).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\033[1m\033[33mTotal transactions: {wallet.get('total_transactions', 0)}\033[0m")
    print(f"\033[1m\033[33mTotal gas used: {wallet.get('total_gas_used', 0)}\033[0m\n")

    if counters:
        print(f"\033[1m\033[36m═══════════════════════════════════════════════════════════\033[0m")
        print(f"\033[1m\033[33m📊 ACTIVITY COUNTERS\033[0m")
        print(f"\033[1m\033[36m═══════════════════════════════════════════════════════════\033[0m\n")

        print(f"\033[1m\033[36m🪙 Tokens:\033[0m")
        print(f"  Created: \033[1m\033[32m{counters.get('tokens_deployed', 0)}\033[0m")
        print(f"  Mint: \033[1m\033[32m{counters.get('tokens_minted', 0)}\033[0m")
        print(f"  Burned: \033[1m\033[32m{counters.get('tokens_burned', 0)}\033[0m")
        print(f"  Transfers: \033[1m\033[32m{counters.get('tokens_transferred', 0)}\033[0m\n")

        print(f"\033[1m\033[36m🔄 Swaps:\033[0m")
        print(f"  Total: \033[1m\033[32m{counters.get('swaps_total', 0)}\033[0m")
        print(f"  Successful: \033[1m\033[32m{counters.get('swaps_successful', 0)}\033[0m")
        print(f"  Failed: \033[1m\033[31m{counters.get('swaps_failed', 0)}\033[0m\n")

        print(f"\033[1m\033[36m💧 Liquidity:\033[0m")
        print(f"  Added: \033[1m\033[32m{counters.get('liquidity_added', 0)}\033[0m")
        print(f"  Removed: \033[1m\033[32m{counters.get('liquidity_removed', 0)}\033[0m\n")

        print(f"\033[1m\033[36m📦 DEX:\033[0m")
        print(f"  Orders placed: \033[1m\033[32m{counters.get('orders_placed', 0)}\033[0m")
        print(f"  Orders cancelled: \033[1m\033[32m{counters.get('orders_cancelled', 0)}\033[0m\n")

        print(f"\033[1m\033[36m🎨 NFT:\033[0m")
        print(f"  Mint: \033[1m\033[32m{counters.get('nfts_minted', 0)}\033[0m")
        print(f"  Transfers: \033[1m\033[32m{counters.get('nfts_transferred', 0)}\033[0m\n")

        print(f"\033[1m\033[36m⚡ Batch operations: \033[1m\033[32m{counters.get('batch_operations', 0)}\033[0m\n")

        print(f"\033[1m\033[36m🛡️ TIP-403:\033[0m")
        print(f"  Policies: \033[1m\033[32m{counters.get('policies_created', 0)}\033[0m")
        print(f"  Whitelists: \033[1m\033[32m{counters.get('whitelists_set', 0)}\033[0m")
        print(f"  Blacklists: \033[1m\033[32m{counters.get('blacklists_set', 0)}\033[0m\n")

        print(f"\033[1m\033[36m💰 Faucet claims: \033[1m\033[32m{counters.get('faucet_claims', 0)}\033[0m\n")

    print(f"\033[1m\033[36m═══════════════════════════════════════════════════════════\033[0m\n")

async def run_statistics():
    """Main function of the statistics module"""
    BOLD_CYAN = COLORS.BOLD_CYAN
    RESET = COLORS.RESET

    print(f"\n  {BOLD_CYAN}📊  WALLET STATISTICS{RESET}\n")

    print('\033[1m\033[33mAvailable operations:\033[0m')
    print('\033[1m\033[34m  1. Show wallet statistics\033[0m')
    print('\033[1m\033[34m  2. Top-10 most active wallets\033[0m')
    print('\033[1m\033[34m  3. Export statistics to CSV\033[0m')
    print('\033[1m\033[34m  4. Show all wallets\033[0m\n')

    choice = ask_question('\033[1m\033[36mChoose (1-4): \033[0m')

    stats = WalletStatistics()

    try:
        if choice == '1':
            # Show statistics for a specific wallet
            private_keys = get_private_keys()
            if len(private_keys) == 0:
                print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
                return

            print(f"\n\033[1m\033[36mAvailable wallets:\033[0m")
            for i, pk in enumerate(private_keys):
                wallet = Account.from_key(pk)
                print(f"\033[1m\033[34m  {i + 1}. {wallet.address}\033[0m")

            wallet_choice = ask_question(f"\n\033[1m\033[36mChoose WALLET NUMBER (1-{len(private_keys)}): \033[0m")
            try:
                wallet_index = int(wallet_choice) - 1
                if wallet_index < 0 or wallet_index >= len(private_keys):
                    print('\033[1m\033[31m❌ Invalid choice!\033[0m')
                    return
            except ValueError:
                print('\033[1m\033[31m❌ Invalid choice!\033[0m')
                return

            wallet = Account.from_key(private_keys[wallet_index])
            wallet_stats = stats.get_wallet_stats(wallet.address)

            display_wallet_stats(wallet_stats)

        elif choice == '2':
            # Top-10 wallets
            top_wallets = stats.get_top_wallets(10)

            print(f"\n\033[1m\033[36m🏆 TOP-10 MOST ACTIVE WALLETS\033[0m\n")

            if len(top_wallets) == 0:
                print('\033[1m\033[33m⚠️ No data. Start using the modules!\033[0m')
                return

            for i, w in enumerate(top_wallets):
                print(f"\033[1m\033[32m{i + 1}. {w['address']}\033[0m")
                print(f"   Transactions: {w.get('total_transactions', 0)}")
                print(f"   Gas: {w.get('total_gas_used', 0)}")
                print(f"   Tokens created: {w.get('tokens_deployed', 0)}")
                print(f"   Swaps: {w.get('swaps_total', 0)}\n")

        elif choice == '3':
            # Export to CSV
            private_keys = get_private_keys()
            if len(private_keys) == 0:
                print('\033[1m\033[31mPrivate keys not found in pv.txt\033[0m')
                return

            print(f"\n\033[1m\033[36mAvailable wallets:\033[0m")
            for i, pk in enumerate(private_keys):
                wallet = Account.from_key(pk)
                print(f"\033[1m\033[34m  {i + 1}. {wallet.address}\033[0m")

            wallet_choice = ask_question(f"\n\033[1m\033[36mChoose WALLET NUMBER (1-{len(private_keys)}): \033[0m")
            try:
                wallet_index = int(wallet_choice) - 1
                if wallet_index < 0 or wallet_index >= len(private_keys):
                    print('\033[1m\033[31m❌ Invalid choice!\033[0m')
                    return
            except ValueError:
                print('\033[1m\033[31m❌ Invalid choice!\033[0m')
                return

            wallet = Account.from_key(private_keys[wallet_index])
            filename = f"wallet_stats_{wallet.address[:10]}.csv"

            success = stats.export_to_csv(wallet.address, filename)

            if success:
                print(f"\n\033[1m\033[32m✓ Export completed: {filename}\033[0m")
            else:
                print(f"\n\033[1m\033[31m✗ No data to export\033[0m")

        elif choice == '4':
            # Show all wallets
            all_wallets = stats.get_all_wallets()

            print(f"\n\033[1m\033[36m📋 ALL WALLETS ({len(all_wallets)})\033[0m\n")

            if len(all_wallets) == 0:
                print('\033[1m\033[33m⚠️ No data. Start using the modules!\033[0m')
                return

            for i, w in enumerate(all_wallets):
                print(f"\033[1m\033[32m{i + 1}. {w['address']}\033[0m")
                print(f"   Transactions: {w.get('total_transactions', 0)}")
                print(f"   Tokens: {w.get('tokens_deployed', 0)} | Swaps: {w.get('swaps_total', 0)} | Batch: {w.get('batch_operations', 0)}\n")

    except Exception as error:
        print(f"\033[1m\033[31mError: {error}\033[0m")
    finally:
        stats.close()

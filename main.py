#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# TEMPO BOT v2.0.1 - MODULAR VERSION (Python)
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import sys
import signal
import subprocess
from config import COLORS, VERSION_INFO
from utils.helpers import ask_question, close_rl

# Import modules
from modules.deploy import run_contract_deploy
from modules.faucet import run_faucet_claim
from modules.send import run_send_token
from modules.token import run_create_stablecoin
from modules.swap import run_swap_tokens
from modules.nft import run_nft
from modules.infinity import run_infinity_name
from modules.retriever import run_retriever_nft
from modules.batch import run_batch_operations
from modules.tip403 import run_tip403_policies
from modules.analytics import run_analytics
from modules.stats import run_statistics
from modules.auto import run_auto_mode

# Helper functions
from utils.wallet import load_created_tokens

def banner():
    """Show banner with logo"""
    print("\033[2J\033[H", end='')  # Clear screen

    try:
        # Run curl command to fetch logo
        result = subprocess.run(
            ['bash', '-c', 'curl -s https://raw.githubusercontent.com/profitnoders/Profit_Nodes/refs/heads/main/logo_scripts.sh | bash'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout:
            # Print logo
            print(result.stdout)
        else:
            # If logo fetch fails, show default banner
            _show_default_banner()

    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        # If curl or bash are not available, show default banner
        _show_default_banner()
    except Exception as e:
        # For any other error, show default banner
        _show_default_banner()

def _show_default_banner():
    """Show default banner (fallback)"""
    BOLD_CYAN = COLORS.BOLD_CYAN
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    BOLD_WHITE = COLORS.BOLD_WHITE
    RESET = COLORS.RESET

    print(f"""
{BOLD_CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           {BOLD_MAGENTA}🚀  PROFIT SCRIPTS  v{VERSION_INFO['VERSION']} (MODULAR)  🚀{BOLD_CYAN}          ║
║                                                               ║
║  {BOLD_WHITE}Automation of activities on Tempo Testnet{BOLD_CYAN}                   ║
║  {BOLD_WHITE}Modular architecture for easy maintenance{BOLD_CYAN}                   ║
║                                                               ║
║  {BOLD_WHITE}Build: {VERSION_INFO['BUILD_DATE']}                    Author: {VERSION_INFO['AUTHOR']}{BOLD_CYAN}          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{RESET}
""")

async def show_menu():
    """Show main menu"""
    BOLD_CYAN = COLORS.BOLD_CYAN
    BOLD_GREEN = COLORS.BOLD_GREEN
    BOLD_WHITE = COLORS.BOLD_WHITE
    BOLD_RED = COLORS.BOLD_RED
    BOLD_MAGENTA = COLORS.BOLD_MAGENTA
    RESET = COLORS.RESET

    banner()
    print(f"  {BOLD_CYAN}Select an option:{RESET}\n")
    print(f"  {BOLD_GREEN}[1]{RESET} {BOLD_WHITE}📦  Deploy contracts{RESET}")
    print(f"  {BOLD_GREEN}[2]{RESET} {BOLD_WHITE}💧  Claim tokens from faucet{RESET}")
    print(f"  {BOLD_GREEN}[3]{RESET} {BOLD_WHITE}💸  Send tokens{RESET}")
    print(f"  {BOLD_GREEN}[4]{RESET} {BOLD_WHITE}🪙  Create stablecoin{RESET}")
    print(f"  {BOLD_GREEN}[5]{RESET} {BOLD_WHITE}🔄  Swap stablecoins{RESET}")
    print(f"  {BOLD_GREEN}[6]{RESET} {BOLD_WHITE}💦  Add liquidity{RESET}")
    print(f"  {BOLD_GREEN}[7]{RESET} {BOLD_WHITE}⚙️   Set fee token{RESET}")
    print(f"  {BOLD_GREEN}[8]{RESET} {BOLD_WHITE}🏭  Mint tokens{RESET}")
    print(f"  {BOLD_GREEN}[9]{RESET} {BOLD_WHITE}🔥  Burn tokens{RESET}")
    print(f"  {BOLD_GREEN}[10]{RESET} {BOLD_WHITE}📝  Transfer with memo{RESET}")
    print(f"  {BOLD_GREEN}[11]{RESET} {BOLD_WHITE}📊  Limit order{RESET}")
    print(f"  {BOLD_GREEN}[12]{RESET} {BOLD_WHITE}💧  Remove liquidity{RESET}")
    print(f"  {BOLD_GREEN}[13]{RESET} {BOLD_WHITE}🔑  Grant role (ISSUER/PAUSE){RESET}")
    print(f"  {BOLD_GREEN}[14]{RESET} {BOLD_WHITE}🎨  NFT (Create + Mint){RESET}")
    print(f"  {BOLD_GREEN}[15]{RESET} {BOLD_WHITE}🌐  InfinityName - Mint domain{RESET}")
    print(f"  {BOLD_GREEN}[16]{RESET} {BOLD_WHITE}🐕  Retriever NFT - MintAura{RESET}")
    print(f"  {BOLD_GREEN}[17]{RESET} {BOLD_WHITE}📦  Batch Operations (EIP-7702){RESET}")
    print(f"  {BOLD_GREEN}[18]{RESET} {BOLD_WHITE}🛡️  TIP-403 Policies - Whitelist/Blacklist{RESET}")
    print(f"  {BOLD_GREEN}[19]{RESET} {BOLD_WHITE}📊  Analytics - Token balances{RESET}")
    print(f"  {BOLD_GREEN}[20]{RESET} {BOLD_WHITE}📈  Statistics - Activity database{RESET}")
    print(f"  {BOLD_GREEN}[21]{RESET} {BOLD_WHITE}🚀  Auto mode{RESET}")
    print()
    print(f"  {BOLD_RED}[0]{RESET} {BOLD_WHITE}🚪  Exit{RESET}")
    print()

async def main():
    """Main entrypoint"""
    # Global error handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        err_msg = str(exc_value)
        if any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout']):
            print('\n\033[1m\033[33m⚠️ RPC temporarily unavailable (502/503). Continuing...\033[0m')
        else:
            print(f'\n\033[1m\033[31m⚠️ Unhandled error:\033[0m {err_msg[:150]}')

    sys.excepthook = handle_exception

    while True:
        await show_menu()
        choice = ask_question('\033[1m\033[36mEnter your choice (0-21): \033[0m')

        try:
            if choice == '1':
                await run_contract_deploy()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '2':
                await run_faucet_claim()
            elif choice == '3':
                await run_send_token()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '4':
                await run_create_stablecoin()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '5':
                await run_swap_tokens()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '6':
                from modules.liquidity import run_add_liquidity
                await run_add_liquidity()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '7':
                from modules.fee import run_set_fee_token
                await run_set_fee_token()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '8':
                from modules.mint import run_mint_tokens
                await run_mint_tokens()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '9':
                from modules.burn import run_burn_tokens
                await run_burn_tokens()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '10':
                from modules.memo import run_transfer_with_memo
                await run_transfer_with_memo()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '11':
                from modules.limit import run_limit_order
                await run_limit_order()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '12':
                from modules.remove import run_remove_liquidity
                await run_remove_liquidity()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '13':
                from modules.role import run_grant_role
                await run_grant_role()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '14':
                await run_nft()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '15':
                await run_infinity_name()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '16':
                await run_retriever_nft()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '17':
                await run_batch_operations()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '18':
                await run_tip403_policies()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '19':
                await run_analytics()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '20':
                await run_statistics()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '21':
                await run_auto_mode()
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
            elif choice == '0':
                print(f"\n  {COLORS.BOLD_MAGENTA}👋  Goodbye!{COLORS.RESET}\n")
                close_rl()
                sys.exit(0)
            else:
                print('\033[1m\033[31mInvalid choice! Please select 0-21\033[0m')
                ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')
        except KeyboardInterrupt:
            print(f"\n  {COLORS.BOLD_MAGENTA}👋  Goodbye!{COLORS.RESET}\n")
            close_rl()
            sys.exit(0)
        except Exception as e:
            print(f'\033[1m\033[31mError: {e}\033[0m')
            ask_question('\n\033[1m\033[33mPress Enter to continue...\033[0m')

# Handle exit
def signal_handler(sig, frame):
    """Signal handler for graceful exit"""
    print(f"\n  {COLORS.BOLD_MAGENTA}👋  Goodbye!{COLORS.RESET}\n")
    close_rl()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n  {COLORS.BOLD_MAGENTA}👋  Goodbye!{COLORS.RESET}\n")
        close_rl()
        sys.exit(0)
    except Exception as error:
        print(f'\033[1m\033[31mFatal Error: {error}\033[0m')
        close_rl()
        sys.exit(1)


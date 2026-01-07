# ═══════════════════════════════════════════════════════════════════════════════
# TEMPO BOT v2.0.1 - HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import sys
import os
import json
import random
from typing import Optional

# Global readline interface (on Windows we fall back to input)
def ask_question(question: str) -> str:
    """Prompt the user for input"""
    try:
        return input(question).strip()
    except (EOFError, KeyboardInterrupt):
        return ""

def sleep(seconds: float):
    """Sleep for the given number of seconds (sync)"""
    asyncio.run(asyncio.sleep(seconds))

async def async_sleep(seconds: float):
    """Async sleep helper"""
    await asyncio.sleep(seconds)

def get_random_int(min_val: int, max_val: int) -> int:
    """Get a random integer in range"""
    return random.randint(min_val, max_val)

def get_random_message() -> str:
    """Return a random message"""
    messages = [
        "Hello World", "GM everyone", "GN friends", "Testing 123", "Done!", "Success!",
        "Have a nice day", "Good vibes only", "Keep building", "Stay positive",
        "Making progress", "One step at a time", "Let's go!", "All good here",
        "Checking in", "Status update", "Quick test", "Running smooth"
    ]
    return random.choice(messages)

def format_time(seconds: int) -> str:
    """Format time in h/m/s"""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

def short_hash(hash_str: str) -> str:
    """Shorten a tx hash for display"""
    if len(hash_str) < 16:
        return hash_str
    return hash_str[:10] + '...' + hash_str[-6:]

async def countdown(seconds: int, message: str = 'Next action in'):
    """Countdown with a progress print"""
    for i in range(seconds, 0, -1):
        print(f"\r\033[1m\033[33m{message}: {format_time(i)}   \033[0m", end='', flush=True)
        await async_sleep(1)
    print(f"\r\033[1m\033[32m{message}: Ready!                              \033[0m\n", end='')

# Spinner animation
spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

async def animated_spinner(ms: int, text: str):
    """Animated spinner for a duration"""
    import time
    start_time = time.time()
    frame_index = 0

    while (time.time() - start_time) * 1000 < ms:
        print(f"\r\033[1m\033[36m{spinner_frames[frame_index]} {text}\033[0m", end='', flush=True)
        frame_index = (frame_index + 1) % len(spinner_frames)
        await async_sleep(0.08)
    print('\r' + ' ' * (len(text) + 10) + '\r', end='')

async def wait_for_tx_with_retry(web3, tx_hash: str, max_retries: int = 5):
    """Wait for a tx with retries on RPC errors"""
    import time
    for attempt in range(max_retries + 1):
        try:
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return receipt
        except Exception as error:
            err_msg = str(error)
            is_rpc_error = any(x in err_msg for x in ['502', '503', 'Bad Gateway', 'SERVER_ERROR', 'timeout'])

            if is_rpc_error and attempt < max_retries:
                wait_time = (attempt + 1) * 5
                print(f"\033[1m\033[33m⚠️ RPC error while waiting for TX, retry in {wait_time}s... ({attempt + 1}/{max_retries})\033[0m")
                await async_sleep(wait_time)
            else:
                raise error

# ============ CREATED TOKENS STORAGE ============

# Token-related helpers moved to utils/wallet.py
# Use: from utils.wallet import load_created_tokens, save_created_token, get_tokens_for_wallet

def close_rl():
    """Close readline (compat stub)"""
    pass


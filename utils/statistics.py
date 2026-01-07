# ═══════════════════════════════════════════════════════════════════════════════
# WALLET STATISTICS DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Dict, List

class WalletStatistics:
    def __init__(self):
        db_path = os.path.join('data', 'wallet_stats.db')

        # Create data folder if missing
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.init_database()

    def init_database(self):
        """Initialize the database"""
        # Table: wallets base info
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                address TEXT PRIMARY KEY,
                wallet_index INTEGER,
                first_activity TEXT,
                last_activity TEXT,
                total_transactions INTEGER DEFAULT 0,
                total_gas_used TEXT DEFAULT '0',
                status TEXT DEFAULT 'active'
            )
        ''')

        # Table: activity counters
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS activity_counters (
                address TEXT PRIMARY KEY,
                tokens_deployed INTEGER DEFAULT 0,
                tokens_minted INTEGER DEFAULT 0,
                tokens_burned INTEGER DEFAULT 0,
                tokens_transferred INTEGER DEFAULT 0,
                swaps_total INTEGER DEFAULT 0,
                swaps_successful INTEGER DEFAULT 0,
                swaps_failed INTEGER DEFAULT 0,
                liquidity_added INTEGER DEFAULT 0,
                liquidity_removed INTEGER DEFAULT 0,
                orders_placed INTEGER DEFAULT 0,
                orders_cancelled INTEGER DEFAULT 0,
                nfts_minted INTEGER DEFAULT 0,
                nfts_transferred INTEGER DEFAULT 0,
                batch_operations INTEGER DEFAULT 0,
                policies_created INTEGER DEFAULT 0,
                whitelists_set INTEGER DEFAULT 0,
                blacklists_set INTEGER DEFAULT 0,
                faucet_claims INTEGER DEFAULT 0,
                FOREIGN KEY (address) REFERENCES wallets(address)
            )
        ''')

        # Table: transaction history
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                tx_hash TEXT,
                block_number INTEGER,
                gas_used TEXT,
                status TEXT,
                details TEXT,
                FOREIGN KEY (address) REFERENCES wallets(address)
            )
        ''')

        # Indexes for faster lookup
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_transactions_address ON transactions(address)')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
        self.db.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')

        self.db.commit()

    def init_wallet(self, address: str, wallet_index: int = 0):
        """Initialize wallet rows"""
        now = datetime.now().isoformat()

        self.db.execute('''
            INSERT OR IGNORE INTO wallets (address, wallet_index, first_activity, last_activity)
            VALUES (?, ?, ?, ?)
        ''', (address, wallet_index, now, now))

        self.db.execute('''
            INSERT OR IGNORE INTO activity_counters (address)
            VALUES (?)
        ''', (address,))

        self.db.commit()

    def record_transaction(self, address: str, tx_type: str, tx_hash: str,
                          gas_used: str, status: str, details: Optional[Dict] = None):
        """Record a transaction"""
        self.init_wallet(address)

        now = datetime.now().isoformat()
        details_json = json.dumps(details or {})

        self.db.execute('''
            INSERT INTO transactions (address, timestamp, type, tx_hash, gas_used, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (address, now, tx_type, tx_hash, gas_used or '0', status, details_json))

        self.update_counters(address, tx_type, status)

        self.update_wallet_info(address, gas_used)

        self.db.commit()

    def update_counters(self, address: str, tx_type: str, status: str):
        """Update activity counters"""
        counter_map = {
            'token_deploy': 'tokens_deployed',
            'token_mint': 'tokens_minted',
            'token_burn': 'tokens_burned',
            'token_transfer': 'tokens_transferred',
            'token_transfer_memo': 'tokens_transferred',
            'swap_exact_in': 'swaps_total',
            'swap_exact_out': 'swaps_total',
            'liquidity_add': 'liquidity_added',
            'liquidity_remove': 'liquidity_removed',
            'order_place': 'orders_placed',
            'order_cancel': 'orders_cancelled',
            'nft_mint': 'nfts_minted',
            'nft_transfer': 'nfts_transferred',
            'batch_approve_swap': 'batch_operations',
            'batch_multiple_swaps': 'batch_operations',
            'batch_multiple_transfers': 'batch_operations',
            'policy_create': 'policies_created',
            'policy_attach': 'policies_created',
            'whitelist_set': 'whitelists_set',
            'blacklist_set': 'blacklists_set',
            'faucet_claim': 'faucet_claims'
        }

        column = counter_map.get(tx_type)
        if not column:
            return

        self.db.execute(f'''
            UPDATE activity_counters
            SET {column} = {column} + 1
            WHERE address = ?
        ''', (address,))

        if tx_type.startswith('swap_'):
            swap_column = 'swaps_successful' if status == 'success' else 'swaps_failed'
            self.db.execute(f'''
                UPDATE activity_counters
                SET {swap_column} = {swap_column} + 1
                WHERE address = ?
            ''', (address,))

    def update_wallet_info(self, address: str, gas_used: str):
        """Update aggregate wallet info"""
        now = datetime.now().isoformat()

        self.db.execute('''
            UPDATE wallets
            SET last_activity = ?,
                total_transactions = total_transactions + 1,
                total_gas_used = CAST(total_gas_used AS INTEGER) + ?
            WHERE address = ?
        ''', (now, int(gas_used or '0'), address))

    def get_wallet_stats(self, address: str):
        """Get wallet statistics"""
        wallet = self.db.execute('SELECT * FROM wallets WHERE address = ?', (address,)).fetchone()
        counters = self.db.execute('SELECT * FROM activity_counters WHERE address = ?', (address,)).fetchone()
        transactions = self.db.execute('''
            SELECT * FROM transactions
            WHERE address = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (address,)).fetchall()

        return {
            'wallet': dict(wallet) if wallet else None,
            'counters': dict(counters) if counters else None,
            'recentTransactions': [
                {**dict(tx), 'details': json.loads(tx['details'] or '{}')}
                for tx in transactions
            ]
        }

    def sync_tokens_from_file(self):
        """Sync token count from created_tokens.json into DB"""
        try:
            from utils.wallet import load_created_tokens
            from web3 import Web3

            tokens_data = load_created_tokens()

            for wallet_address, token_list in tokens_data.items():
                if not token_list:
                    continue

                normalized_address = Web3.to_checksum_address(wallet_address)
                token_count = len(token_list)

                self.init_wallet(normalized_address)

                current_count = self.db.execute(
                    'SELECT tokens_deployed FROM activity_counters WHERE address = ?',
                    (normalized_address,)
                ).fetchone()

                current_value = dict(current_count)['tokens_deployed'] if current_count else 0
                new_value = max(current_value, token_count)

                if new_value != current_value:
                    self.db.execute('''
                        UPDATE activity_counters
                        SET tokens_deployed = ?
                        WHERE address = ?
                    ''', (new_value, normalized_address))

            self.db.commit()
        except Exception as e:
            pass

    def get_all_wallets(self):
        """Get all wallets"""
        # Sync tokens from file before querying
        self.sync_tokens_from_file()

        rows = self.db.execute('''
            SELECT w.*, ac.*
            FROM wallets w
            LEFT JOIN activity_counters ac ON w.address = ac.address
            ORDER BY w.total_transactions DESC
        ''').fetchall()

        return [dict(row) for row in rows]

    def get_top_wallets(self, limit: int = 10, order_by: str = 'total_transactions'):
        """Get top wallets"""
        # Sync tokens from file before querying
        self.sync_tokens_from_file()

        valid_columns = ['total_transactions', 'total_gas_used', 'tokens_deployed', 'swaps_total']
        column = order_by if order_by in valid_columns else 'total_transactions'

        rows = self.db.execute(f'''
            SELECT w.*, ac.*
            FROM wallets w
            LEFT JOIN activity_counters ac ON w.address = ac.address
            ORDER BY w.{column} DESC
            LIMIT ?
        ''', (limit,)).fetchall()

        return [dict(row) for row in rows]

    def get_wallet_stats(self, address: str):
        """Get wallet statistics (with transactions)"""
        # Sync tokens from file before querying
        self.sync_tokens_from_file()

        wallet = self.db.execute('SELECT * FROM wallets WHERE address = ?', (address,)).fetchone()
        counters = self.db.execute('SELECT * FROM activity_counters WHERE address = ?', (address,)).fetchone()
        transactions = self.db.execute('''
            SELECT * FROM transactions
            WHERE address = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (address,)).fetchall()

        return {
            'wallet': dict(wallet) if wallet else None,
            'counters': dict(counters) if counters else None,
            'recentTransactions': [
                {**dict(tx), 'details': json.loads(tx['details'] or '{}')}
                for tx in transactions
            ]
        }

    def export_to_csv(self, address: str, filename: str) -> bool:
        """Export wallet transactions to CSV"""
        stats = self.get_wallet_stats(address)
        if not stats['wallet']:
            return False

        lines = ['Timestamp,Type,TxHash,GasUsed,Status,Details']

        all_tx = self.db.execute('''
            SELECT * FROM transactions
            WHERE address = ?
            ORDER BY timestamp DESC
        ''', (address,)).fetchall()

        for tx in all_tx:
            details = json.dumps(json.loads(tx['details'] or '{}')).replace(',', ';')
            lines.append(f"{tx['timestamp']},{tx['type']},{tx['tx_hash']},{tx['gas_used']},{tx['status']},\"{details}\"")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return True

    def close(self):
        """Close database connection"""
        self.db.close()


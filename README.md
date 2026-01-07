# tempo-testnet-autobot

# 🚀 Tempo Testnet v2.0.1

Automation of activities on the Tempo Testnet. Modular architecture for easy maintenance and extension.

## 📋 Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Modules](#modules)
- [Project Structure](#project-structure)
- [Notes](#notes)
- [License](#license)

## 🔧 Requirements

- **Python 3.8+** (3.10+ recommended)
- **pip** (Python package manager)
- **Internet connection** to interact with the blockchain

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/rxMeowzz/tempo-testnet-autobot.git
cd tempo-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Solidity compiler

```bash
python -c "from solcx import install_solc; install_solc('0.8.20')"
```

Or manually:

```bash
python -m solcx.install 0.8.20
```

## ⚙️ Configuration

### 1. Create the private keys file

Copy the example file:

```bash
cp pv.txt.example pv.txt
```

Open `pv.txt` and add your private keys (one per line):

```
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
```

**⚠️ IMPORTANT:**
- Never publish the `pv.txt` file publicly!
- `pv.txt` is already in `.gitignore` and will not be uploaded to the repository
- Keep your private keys secure

### 2. (Optional) Configure RPC URL

If you need to change the RPC URL, open `config.py` and adjust `RPC_URL`:

```python
CONFIG = {
    'RPC_URL': 'https://your-rpc-url-here',
    # ...
}
```

## 🚀 Usage

Run the bot:

```bash
python main.py
```

After launch you will see the menu with available modules. Choose an item and follow the prompts.

## 📚 Modules

### Core operations

- **[1] 📦 Deploy contracts** - Deploy simple Solidity contracts
- **[2] 💧 Faucet** - Receive test tokens from the faucet
- **[3] 💸 Send tokens** - Send ERC20 tokens to specified or random addresses
- **[4] 🪙 Create stablecoin** - Create new stablecoins via TIP-20 Factory

### DEX operations

- **[5] 🔄 Swap stablecoins** - Swap tokens via DEX (auto-liquidity placement)
- **[6] 💦 Add liquidity** - Add liquidity to Fee AMM pools
- **[11] 📊 Limit order** - Place limit orders on DEX
- **[12] 💧 Remove liquidity** - Withdraw liquidity from pools

### Token management

- **[7] ⚙️ Set fee token** - Set the token used to pay gas
- **[8] 🎯 Mint tokens** - Mint created tokens
- **[9] 🔥 Burn tokens** - Burn tokens
- **[10] 📝 Transfer with memo** - Transfer tokens with memo field
- **[13] 🛡️ Grant role (ISSUER/PAUSE)** - Grant token roles

### NFT and domains

- **[14] 🎨 NFT (Create + Mint)** - Create and mint NFT collections
- **[15] 🌐 InfinityName - Mint domain** - Register .tempo domains
- **[16] 🐕 Retriever NFT - MintAura** - Mint Retriever NFT collection

### Advanced features

- **[17] 📦 Batch Operations (EIP-7702)** - Batch operations to save gas
- **[18] 🔒 TIP-403 Policies - Whitelist/Blacklist** - Manage token transfer policies
- **[19] 📊 Analytics - Token balances** - Analytics for balances and LP positions
- **[20] 📈 Statistics - Activity database** - Statistics of all operations
- **[21] 🤖 Auto mode** - Automatically run all activities

## 📁 Project Structure

```
.
├── main.py                  # Entry point
├── config.py                # Configuration and ABIs
├── requirements.txt         # Python dependencies
├── pv.txt.example           # Example keys file
├── .gitignore               # Git ignore rules
├── README.md                # Documentation
│
├── modules/                 # Functionality modules
│   ├── __init__.py
│   ├── deploy.py            # Contract deployment
│   ├── faucet.py            # Faucet
│   ├── send.py              # Token sending
│   ├── token.py             # Token creation
│   ├── swap.py              # Token swaps
│   ├── liquidity.py         # Liquidity
│   ├── mint.py              # Token minting
│   ├── burn.py              # Token burning
│   ├── memo.py              # Transfers with memo
│   ├── limit.py             # Limit orders
│   ├── remove.py            # Liquidity removal
│   ├── role.py              # Role management
│   ├── fee.py               # Fee token setup
│   ├── nft.py               # NFT collections
│   ├── infinity.py          # InfinityName domains
│   ├── retriever.py         # Retriever NFT
│   ├── batch.py             # Batch operations
│   ├── tip403.py            # TIP-403 policies
│   ├── analytics.py         # Analytics
│   ├── stats.py             # Statistics
│   └── auto.py              # Automatic mode
│
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── helpers.py           # Helper functions
│   ├── wallet.py            # Wallet utilities
│   └── statistics.py        # Statistics database
│
├── contracts/               # Solidity contracts (optional)
│   └── BatchOperations.sol
│
└── data/                    # Data (auto-created)
    ├── created_tokens.json  # Created tokens
    └── wallet_stats.db      # Statistics database
```

## 📝 Notes

### Security

- ⚠️ **NEVER** publish `pv.txt` publicly
- ⚠️ Keep private keys secure
- ⚠️ Use on testnets only

### Database

- **Database is created automatically** on first run
- All transactions are recorded into SQLite (`data/wallet_stats.db`)
- Created tokens are stored in `data/created_tokens.json`
- Statistics sync automatically on view
- The `data/` folder is in `.gitignore` and will not be uploaded

### Features

- All modules work with multiple wallets simultaneously
- Automatic RPC error handling with retries
- Checksum address support for web3.py compatibility
- Automatic liquidity placement during swaps if none exists

### Balance requirements

- Most operations need a fee token (PathUSD, AlphaUSD, BetaUSD, ThetaUSD)
- Minimum balance for operations: ~0.1-0.5 token
- Get tokens from the faucet ([2]) before using other modules

## 🐛 Troubleshooting

### Error "insufficient funds for gas"

Ensure the wallet has enough fee token balance. Get tokens via the faucet.

### Error "web3.py only accepts checksum addresses"

This should be fixed across modules. If you see it, report via Issues.

### Solidity compilation error

Ensure Solidity compiler 0.8.20 is installed:

```bash
python -c "from solcx import install_solc; install_solc('0.8.20')"
```

## 🤝 Contributing

Improvements are welcome! Please open Issues and Pull Requests.

## 📄 License

MIT License

## 👤 Author

Shadow

---

**⚠️ Disclaimer:** This bot is for testnets only. Use at your own risk.

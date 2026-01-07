# Changelog

All notable changes to this project will be documented in this file.

## [2.0.1] - 2024-12-21

### Added
- Full support for all 21 modules
- Automatic statistics sync from `created_tokens.json`
- Automatic liquidity placement during swaps
- Support for all wallets in NFT, InfinityName, Retriever NFT, Batch Operations modules
- Fee token balance check before operations
- Improved error handling with retry mechanism

### Fixed
- `'SignedTransaction' object has no attribute 'rawTransaction'` across modules
- `'web3.py only accepts checksum addresses'` across modules
- Solidity compilation errors in deploy modules
- Issues saving and loading created tokens
- `'sqlite3.Row' object has no attribute 'get'` in statistics
- Display of the number of created tokens in statistics

### Changed
- All modules now work with all wallets from `pv.txt`
- Improved project structure for GitHub publishing
- Removed all JavaScript files (project now fully Python)

## [2.0.0] - 2024-12-17

### Added
- First Python port version
- Modular architecture
- Statistics database
- Support for core operations on Tempo Testnet
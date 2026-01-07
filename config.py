# ═══════════════════════════════════════════════════════════════════════════════
# TEMPO BOT v2.0.1 - CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Console colors
class COLORS:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"
    BLUE = "\033[34m"
    BOLD_GREEN = "\033[1;32m"
    BOLD_YELLOW = "\033[1;33m"
    BOLD_RED = "\033[1;31m"
    BOLD_CYAN = "\033[1;36m"
    BOLD_MAGENTA = "\033[1;35m"
    BOLD_WHITE = "\033[1;37m"
    BOLD_BLUE = "\033[1;34m"

# Version info
VERSION_INFO = {
    'VERSION': '2.0.1',
    'BUILD_DATE': '17.12.2024',
    'AUTHOR': 'Shadow'
}

# Core configuration
CONFIG = {
    'RPC_URL': 'https://rpc.testnet.tempo.xyz',
    'CHAIN_ID': 42429,
    'EXPLORER_URL': 'https://explore.tempo.xyz',
    'GAS_LIMIT': 3000000,
    'MIN_DELAY_BETWEEN_WALLETS': 5,
    'MAX_DELAY_BETWEEN_WALLETS': 30,
    'MIN_DELAY_BETWEEN_DEPLOYS': 3,
    'MAX_DELAY_BETWEEN_DEPLOYS': 10,
    'FAUCET_CLAIM_DELAY_SEC': 15,
    'FAUCET_FINISH_DELAY_SEC': 30,
    'FAUCET_PRE_CLAIM_MS': 4000,
    'TOKENS': {
        'PathUSD': '0x20c0000000000000000000000000000000000000',
        'AlphaUSD': '0x20c0000000000000000000000000000000000001',
        'BetaUSD': '0x20c0000000000000000000000000000000000002',
        'ThetaUSD': '0x20c0000000000000000000000000000000000003'
    },
    'FAUCET_TOKENS': [
        {'symbol': 'PathUSD', 'amount': '1,000,000'},
        {'symbol': 'AlphaUSD', 'amount': '1,000,000'},
        {'symbol': 'BetaUSD', 'amount': '1,000,000'},
        {'symbol': 'ThetaUSD', 'amount': '1,000,000'}
    ]
}

# System contract addresses
SYSTEM_CONTRACTS = {
    'TIP20_FACTORY': '0x20fc000000000000000000000000000000000000',
    'FEE_MANAGER': '0xfeec000000000000000000000000000000000000',
    'STABLECOIN_DEX': '0xdec0000000000000000000000000000000000000'
}

# Additional contract addresses
INFINITY_NAME_CONTRACT = '0x70a57af45cd15f1565808cf7b1070bac363afd8a'
RETRIEVER_NFT_CONTRACT = '0x603928C91Db2A58E2E689D42686A139Ad41CB51C'

# ERC20 ABI
ERC20_ABI = [
    {
        'constant': True,
        'inputs': [],
        'name': 'decimals',
        'outputs': [{'name': '', 'type': 'uint8'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [{'name': '_owner', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'name': 'balance', 'type': 'uint256'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [],
        'name': 'symbol',
        'outputs': [{'name': '', 'type': 'string'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'to', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'}
        ],
        'name': 'transfer',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'spender', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'}
        ],
        'name': 'approve',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'owner', 'type': 'address'},
            {'name': 'spender', 'type': 'address'}
        ],
        'name': 'allowance',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'type': 'function'
    }
]

# TIP-20 Extended ABI
TIP20_EXTENDED_ABI = ERC20_ABI + [
    {
        'constant': True,
        'inputs': [],
        'name': 'name',
        'outputs': [{'name': '', 'type': 'string'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'to', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'}
        ],
        'name': 'mint',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [{'name': 'amount', 'type': 'uint256'}],
        'name': 'burn',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'to', 'type': 'address'},
            {'name': 'amount', 'type': 'uint256'},
            {'name': 'memo', 'type': 'bytes32'}
        ],
        'name': 'transferWithMemo',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'role', 'type': 'bytes32'},
            {'name': 'account', 'type': 'address'}
        ],
        'name': 'hasRole',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function'
    }
]

# TIP-20 Factory ABI
TIP20_FACTORY_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'name', 'type': 'string'},
            {'name': 'symbol', 'type': 'string'},
            {'name': 'currency', 'type': 'string'},
            {'name': 'quoteToken', 'type': 'address'},
            {'name': 'admin', 'type': 'address'}
        ],
        'name': 'createToken',
        'outputs': [{'name': '', 'type': 'address'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [],
        'name': 'tokenIdCounter',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [{'name': 'token', 'type': 'address'}],
        'name': 'isTIP20',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function'
    },
    {
        'anonymous': False,
        'inputs': [
            {'indexed': True, 'name': 'token', 'type': 'address'},
            {'indexed': True, 'name': 'tokenId', 'type': 'uint256'},
            {'indexed': False, 'name': 'name', 'type': 'string'},
            {'indexed': False, 'name': 'symbol', 'type': 'string'},
            {'indexed': False, 'name': 'currency', 'type': 'string'},
            {'indexed': False, 'name': 'quoteToken', 'type': 'address'},
            {'indexed': False, 'name': 'admin', 'type': 'address'}
        ],
        'name': 'TokenCreated',
        'type': 'event'
    }
]

# Stablecoin DEX ABI
STABLECOIN_DEX_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'tokenIn', 'type': 'address'},
            {'name': 'tokenOut', 'type': 'address'},
            {'name': 'amountIn', 'type': 'uint128'},
            {'name': 'minAmountOut', 'type': 'uint128'}
        ],
        'name': 'swapExactAmountIn',
        'outputs': [{'name': 'amountOut', 'type': 'uint128'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'tokenIn', 'type': 'address'},
            {'name': 'tokenOut', 'type': 'address'},
            {'name': 'amountOut', 'type': 'uint128'},
            {'name': 'maxAmountIn', 'type': 'uint128'}
        ],
        'name': 'swapExactAmountOut',
        'outputs': [{'name': 'amountIn', 'type': 'uint128'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'tokenIn', 'type': 'address'},
            {'name': 'tokenOut', 'type': 'address'},
            {'name': 'amountIn', 'type': 'uint128'}
        ],
        'name': 'quoteSwapExactAmountIn',
        'outputs': [{'name': 'amountOut', 'type': 'uint128'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'user', 'type': 'address'},
            {'name': 'token', 'type': 'address'}
        ],
        'name': 'balanceOf',
        'outputs': [{'name': '', 'type': 'uint128'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'token', 'type': 'address'},
            {'name': 'amount', 'type': 'uint128'}
        ],
        'name': 'withdraw',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'token', 'type': 'address'},
            {'name': 'amount', 'type': 'uint128'},
            {'name': 'isBid', 'type': 'bool'},
            {'name': 'tick', 'type': 'int16'}
        ],
        'name': 'place',
        'outputs': [{'name': 'orderId', 'type': 'uint128'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [{'name': 'orderId', 'type': 'uint128'}],
        'name': 'cancel',
        'outputs': [],
        'type': 'function'
    }
]

# Fee Manager ABI
FEE_MANAGER_ABI = [
    {
        'constant': True,
        'inputs': [{'name': 'user', 'type': 'address'}],
        'name': 'userTokens',
        'outputs': [{'name': '', 'type': 'address'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [{'name': 'token', 'type': 'address'}],
        'name': 'setUserToken',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'userToken', 'type': 'address'},
            {'name': 'validatorToken', 'type': 'address'}
        ],
        'name': 'getPoolId',
        'outputs': [{'name': '', 'type': 'bytes32'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'userToken', 'type': 'address'},
            {'name': 'validatorToken', 'type': 'address'}
        ],
        'name': 'getPool',
        'outputs': [
            {'name': 'reserveUserToken', 'type': 'uint128'},
            {'name': 'reserveValidatorToken', 'type': 'uint128'}
        ],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'userToken', 'type': 'address'},
            {'name': 'validatorToken', 'type': 'address'},
            {'name': 'amountValidatorToken', 'type': 'uint256'},
            {'name': 'to', 'type': 'address'}
        ],
        'name': 'mintWithValidatorToken',
        'outputs': [{'name': 'liquidity', 'type': 'uint256'}],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'poolId', 'type': 'bytes32'},
            {'name': 'user', 'type': 'address'}
        ],
        'name': 'liquidityBalances',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'userToken', 'type': 'address'},
            {'name': 'validatorToken', 'type': 'address'},
            {'name': 'liquidity', 'type': 'uint256'},
            {'name': 'to', 'type': 'address'}
        ],
        'name': 'burn',
        'outputs': [
            {'name': 'amountUserToken', 'type': 'uint256'},
            {'name': 'amountValidatorToken', 'type': 'uint256'}
        ],
        'type': 'function'
    }
]

# Multicall3 for batch operations
MULTICALL3_ADDRESS = '0xcA11bde05977b3631167028862bE2a173976CA11'
MULTICALL3_ABI = [
    {
        'constant': False,
        'inputs': [{
            'name': 'calls',
            'type': 'tuple[]',
            'components': [
                {'name': 'target', 'type': 'address'},
                {'name': 'allowFailure', 'type': 'bool'},
                {'name': 'callData', 'type': 'bytes'}
            ]
        }],
        'name': 'aggregate3',
        'outputs': [{
            'name': 'returnData',
            'type': 'tuple[]',
            'components': [
                {'name': 'success', 'type': 'bool'},
                {'name': 'returnData', 'type': 'bytes'}
            ]
        }],
        'type': 'function'
    }
]

# EIP-7702 Default Delegation
DEFAULT_7702_IMPL = '0x7702c00000000000000000000000000000000000'
DEFAULT_ACCOUNT_REGISTRAR = '0x7702ac00000000000000000000000000000000000000'

# TIP-403 Registry ABI
TIP403_REGISTRY_ABI = [
    {
        'constant': False,
        'inputs': [
            {'name': 'admin', 'type': 'address'},
            {'name': 'policyType', 'type': 'uint8'}
        ],
        'name': 'createPolicy',
        'outputs': [{'name': '', 'type': 'uint64'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'admin', 'type': 'address'},
            {'name': 'policyType', 'type': 'uint8'},
            {'name': 'accounts', 'type': 'address[]'}
        ],
        'name': 'createPolicyWithAccounts',
        'outputs': [{'name': '', 'type': 'uint64'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'policyId', 'type': 'uint64'},
            {'name': 'account', 'type': 'address'},
            {'name': 'allowed', 'type': 'bool'}
        ],
        'name': 'modifyPolicyWhitelist',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [
            {'name': 'policyId', 'type': 'uint64'},
            {'name': 'account', 'type': 'address'},
            {'name': 'restricted', 'type': 'bool'}
        ],
        'name': 'modifyPolicyBlacklist',
        'outputs': [],
        'type': 'function'
    },
    {
        'constant': True,
        'inputs': [
            {'name': 'policyId', 'type': 'uint64'},
            {'name': 'user', 'type': 'address'}
        ],
        'name': 'isAuthorized',
        'outputs': [{'name': '', 'type': 'bool'}],
        'type': 'function'
    }
]

# TIP-403 Registry Address
TIP403_REGISTRY = '0x403c000000000000000000000000000000000000'

# TIP-20 Token ABI for policy management
TIP20_POLICY_ABI = [
    {
        'constant': True,
        'inputs': [],
        'name': 'transferPolicyId',
        'outputs': [{'name': '', 'type': 'uint64'}],
        'type': 'function'
    },
    {
        'constant': False,
        'inputs': [{'name': 'newPolicyId', 'type': 'uint64'}],
        'name': 'changeTransferPolicyId',
        'outputs': [],
        'type': 'function'
    }
]

# Export individual constants for convenience
RPC_URL = CONFIG['RPC_URL']
TOKENS = CONFIG['TOKENS']


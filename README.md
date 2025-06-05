# API Adapter Framework

A simple, incremental Python framework for building API data adapters with a focus on blockchain and DeFi integrations. Now includes comprehensive wallet persona analysis for Base chain.

## Features

- **BaseAdapter Pattern**: Extensible base class for creating specific API adapters
- **Built-in Error Handling**: Robust error management for network issues
- **Session Management**: Efficient request handling with connection pooling
- **Environment Configuration**: Secure credential management
- **Type Hints**: Better code clarity and IDE support
- **Multiple Blockchain APIs**: Ready-to-use adapters for Zerion, Etherscan, and Base chain APIs
- **Modular Design**: Organized adapters package for easy extension
- **Persona Analysis**: Advanced wallet behavior analysis and classification system
- **Portfolio Analytics**: Real-time portfolio valuation and composition analysis
- **Activity Tracking**: Comprehensive DeFi activity and swap analysis

## Architecture

The framework uses an adapter pattern where:

- `adapters.BaseAdapter`: Abstract base class for all API adapters
- `adapters.EtherscanAdapter`: Ethereum blockchain data via Etherscan API (supports Base chain with chainId 8453)
- `adapters.ZerionAdapter`: DeFi portfolio data via Zerion API
- `PersonaAnalyzer`: Wallet behavior analysis and classification for Base chain
- `PortfolioAnalyzer`: Portfolio composition and valuation analysis

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (see Environment Configuration section)

## Quick Start

### Using Etherscan Adapter for Base Chain

```python
from adapters.etherscan import EtherscanAdapter

# Initialize with Base chain ID (8453)
adapter = EtherscanAdapter(chain_id=8453)

# Test authentication
if adapter.authenticate():
    # Get Ether balance
    balance = adapter.get_ether_balance("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")

    # Get transaction history
    transactions = adapter.get_normal_transactions(
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        startblock=0,
        endblock=99999999,
        page=1,
        offset=10,
        sort="desc"
    )

    # Get ERC20 token transfers
    token_transfers = adapter.get_erc20_token_transfers(
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    )
```

### Using Etherscan Adapter for Ethereum

```python
from adapters.etherscan import EtherscanAdapter

# Initialize with Ethereum mainnet (chain ID 1)
adapter = EtherscanAdapter(chain_id=1)

# Same API methods available for Ethereum mainnet
```

### Using Zerion Adapter

```python
from adapters.zerion import ZerionAdapter

# Initialize with API key
adapter = ZerionAdapter(api_key="your_api_key")

# Or use environment variable ZERION_API_KEY
adapter = ZerionAdapter()

# Get wallet positions
positions = adapter.get_wallet_positions(
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    currency="usd",
    **{"page[size]": "10"}
)

# Get wallet portfolio
portfolio = adapter.get_wallet_portfolio("wallet_address")
```

### Creating Custom Adapters

```python
from adapters.base import BaseAdapter

class CustomAdapter(BaseAdapter):
    def __init__(self, api_key: str):
        headers = {"Authorization": f"Bearer {api_key}"}
        super().__init__(
            base_url="https://api.custom.com/v1",
            headers=headers
        )

    def authenticate(self) -> bool:
        # Implement authentication logic
        response = self.get("auth/test")
        return response is not None

    def validate_response(self, response: dict) -> bool:
        # Implement response validation
        return "status" in response and response["status"] == "1"
```

### Environment Configuration

Set your API credentials as environment variables:

```bash
# Etherscan API (used for both Ethereum and Base chain)
export ETHERSCAN_API_KEY=your_etherscan_api_key_here

# Zerion API
export ZERION_API_KEY=your_zerion_api_key_here
```

Or create a `.env` file:

```bash
ETHERSCAN_API_KEY=your_etherscan_api_key_here
ZERION_API_KEY=your_zerion_api_key_here
```

## Etherscan API Features

The `EtherscanAdapter` supports comprehensive blockchain data access and works with multiple networks:

### Account Operations

- **Balance Operations**: Single/multiple address Ether balances, historical balance
- **Transaction Operations**: Normal transactions, internal transactions, transaction by hash
- **Token Operations**: ERC20/ERC721/ERC1155 token transfers
- **Mining Operations**: Blocks mined by address, uncle blocks
- **Advanced Features**: Address funding analysis, beacon chain withdrawals

### Supported Networks

- Ethereum Mainnet (chain_id: 1)
- Base Chain (chain_id: 8453) - **Used for persona analysis**
- Ethereum Testnets (Goerli, Sepolia, etc.)
- Other EVM-compatible networks

## Zerion API Features

The `ZerionAdapter` supports DeFi portfolio management:

### Wallet Operations

- **Positions**: Fungible token positions and balances
- **Portfolio**: Portfolio overview and valuations
- **Transactions**: Transaction history across chains
- **NFTs**: NFT positions and metadata

### Asset & Chain Operations

- **Assets**: Fungible asset information and metadata
- **Chains**: Supported blockchain networks
- **Advanced Features**: Testnet support, pagination, filtering

## Running Examples

### Test Current Implementation

```bash
python main.py
```

This will run comprehensive tests of the Etherscan adapter including:

- Authentication validation
- Balance checking (single and multiple addresses)
- Transaction history retrieval
- Token transfer analysis
- Address funding information

## Project Structure

```
.
├── adapters/
│   ├── __init__.py         # Package initialization and exports
│   ├── base.py            # Abstract base adapter class
│   ├── etherscan.py       # Etherscan API adapter
│   └── zerion.py          # Zerion API adapter
├── persona_analyzer.py    # Base chain persona analysis system
├── portfolio_analyzer.py  # Portfolio composition and valuation
├── test_persona.py        # Persona analysis testing script
├── main.py                # Example usage and testing
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── .gitignore            # Git ignore rules
```

## API Rate Limits & Best Practices

### Etherscan API

- **Rate Limits**: 5 calls/second for free tier, 50 calls/second for pro
- **Timeout**: Reasonable timeout settings for network requests
- **Error Handling**: Comprehensive error handling for API responses
- **Chain Support**: Multi-chain support with chain-specific endpoints
- **Base Chain**: Uses same API key as Ethereum, configured with chainId 8453

### Zerion API

- **Timeout**: Set to 2 minutes (120s) as recommended
- **Retries**: Stop retries after 2 minutes if no 200 status
- **URL Length**: Keep request URLs under 2000 characters
- **Authentication**: Uses Basic auth with base64 encoded API key

## Next Steps

Extend the framework by adding:

1. **More Adapters**: CoinGecko, DeFiPulse, Alchemy, Infura, etc.
2. **Rate Limiting**: Built-in rate limit handling with backoff strategies
3. **Caching**: Redis/memory caching for API responses
4. **Async Support**: AsyncIO for concurrent requests
5. **Data Persistence**: Database integration for historical data
6. **Monitoring**: Logging and metrics collection
7. **Testing**: Unit tests and integration tests
8. **Documentation**: API documentation with examples

## Dependencies

- `requests`: HTTP library for API calls
- `python-dotenv`: Environment variable management
- `aiohttp`: Async HTTP library for price data fetching

## Contributing

1. Add new adapters to the `adapters/` directory
2. Inherit from `BaseAdapter` and implement required methods
3. Update `adapters/__init__.py` to export your adapter
4. Add comprehensive error handling and validation
5. Update documentation and examples

## Persona Analysis

The framework includes a comprehensive persona analysis system that evaluates Base chain wallets against behavioral metrics using **Zerion API for accurate portfolio data** and **Etherscan for transaction history**:

### Quick Start - Persona Analysis

```python
import asyncio
from persona_analyzer import PersonaAnalyzer

async def analyze_wallet():
    # Initialize with both API keys for best accuracy
    analyzer = PersonaAnalyzer(
        etherscan_api_key="your_etherscan_api_key",  # For transactions & Base chain data
        zerion_api_key="your_zerion_api_key"         # For accurate portfolio data (optional)
    )

    # Analyze a Base chain wallet
    results = await analyzer.analyze_wallet("0x742587695473b0fD5e4D8019Ab9E3ba2c9dB8B8B")

    print(f"Chain: {results['chain']}")  # Shows "Base (Chain ID: 8453)"
    print(f"Data Sources: {results['data_sources']}")  # Shows "Zerion + Etherscan" or "Etherscan"
    print(f"Persona Score: {results['persona_score']:.1f}%")
    print(f"Metrics Passed: {results['metrics_passed']}/{results['total_metrics']}")

    # Check portfolio summary
    portfolio = results['portfolio_summary']
    print(f"Total Value: ${portfolio['total_value_usd']:.2f}")
    print(f"Top Asset: {portfolio['top_asset'][0]} (${portfolio['top_asset'][1]:.2f})")

asyncio.run(analyze_wallet())
```

### Data Sources & Accuracy

The persona analyzer uses multiple data sources for comprehensive analysis:

#### **Zerion API** (Recommended for Portfolio Data)

- ✅ **Accurate token holdings** with real-time balances and prices
- ✅ **NFT collections** with floor prices and metadata
- ✅ **Multi-chain support** with Base chain filtering
- ✅ **Curated token data** with proper symbols and decimals
- 📍 **Source**: `GET /v1/wallets/{address}/positions/` and `/nft-collections/`

#### **Etherscan API** (Transaction History & Base Chain Data)

- ✅ **Complete transaction history** for activity analysis
- ✅ **Token transfer events** for holding period calculations
- ✅ **NFT transfer events** for acquisition dates
- ✅ **Swap activity detection** through transaction patterns
- 📍 **Source**: Base chain API with chainId 8453

#### **Fallback Mode** (Etherscan Only)

- ⚠️ **Basic portfolio estimation** when Zerion API key not provided
- ⚠️ **Limited token metadata** (known Base tokens only)
- ⚠️ **No real-time pricing** (uses DeFiLlama as backup)
- ⚠️ **Less accurate NFT valuation**

### Persona Metrics

The system evaluates wallets against 21 behavioral metrics:

#### Portfolio Concentration

- Token holding > 60% portfolio value
- Token holding > 50% portfolio value
- Token holding > 70% portfolio value

#### Holding Patterns

- Holding period > 12 months
- Longest holding token > 3 months
- Holding period < 3 months

#### Portfolio Value

- Top asset value < $5,000
- Top asset value $2,000 < x < $5,000
- Total portfolio value < $5,000

#### Wallet Age

- Wallet created < 2020
- Wallet created > 2023

#### Asset Types

- Holding ETH
- Top asset is token (not ETH)
- Top value is NFT

#### Activity Levels

- Active for over 120 days (last 12 months)
- Active for over 180 days (last 12 months)
- Active for over 30 days (last 12 months)

#### Trading Behavior

- Over 100 swap transactions (last 12 months)
- Interacted with NFT marketplace
- Total onchain transactions < 50

### Portfolio Analysis

The `PortfolioAnalyzer` provides detailed portfolio insights using both Zerion and Etherscan data:

```python
from portfolio_analyzer import PortfolioAnalyzer
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter

async def analyze_portfolio():
    # Create adapters
    base_adapter = EtherscanAdapter(api_key="your_etherscan_key", chain_id=8453)
    zerion_adapter = ZerionAdapter(api_key="your_zerion_key")  # Optional but recommended

    # Use context manager for proper async session handling
    async with PortfolioAnalyzer(base_adapter, zerion_adapter) as analyzer:
        portfolio = await analyzer.analyze_portfolio("0x742587695473b0fD5e4D8019Ab9E3ba2c9dB8B8B")

        print(f"Total Value: ${portfolio.total_value_usd:.2f}")
        print(f"Token Concentration: {portfolio.token_concentration_ratio:.1%}")
        print(f"Longest Holding: {portfolio.longest_holding_period} days")
        print(f"Top Asset is NFT: {portfolio.is_top_asset_nft}")

        # Show token holdings with acquisition dates
        for holding in portfolio.token_holdings[:5]:
            print(f"  {holding.symbol}: {holding.balance:.4f} (${holding.value_usd:.2f})")
            print(f"    Held for: {holding.holding_period_days} days")

        # Analyze trading activity (uses Etherscan data)
        activity = await analyzer.analyze_swap_activity("0x742587695473b0fD5e4D8019Ab9E3ba2c9dB8B8B")
        print(f"Swap Count: {activity['swap_count']}")
        print(f"Unique Tokens: {activity['unique_tokens']}")

asyncio.run(analyze_portfolio())
```

### Testing Persona Analysis

Use the included test script to analyze Base chain wallets:

```bash
# Test single wallet
python test_persona.py

# Compare multiple wallets
python test_persona.py compare
```

### Persona Classifications

Based on the analysis score, wallets are classified as:

- **🏆 Power User (80%+)**: Highly active DeFi user with diverse portfolio
- **📈 Active Trader (60-79%)**: Regular DeFi participant with moderate activity
- **🌱 Growing User (40-59%)**: Developing DeFi user with some activity
- **👶 New User (20-39%)**: Beginning DeFi journey with limited activity
- **😴 Inactive User (<20%)**: Minimal or no recent DeFi activity

## Environment Variables

Create a `.env` file in the project root:

```bash
# Required for Base chain analysis
ETHERSCAN_API_KEY=your_etherscan_api_key_here

# Recommended for accurate portfolio data
ZERION_API_KEY=your_zerion_api_key_here
```

Get API keys from:

- **Etherscan**: https://etherscan.io/apis (works for both Ethereum and Base chain)
- **Zerion**: https://developers.zerion.io/ (for accurate portfolio data)

### API Key Benefits

| Feature             | Etherscan Only    | Etherscan + Zerion |
| ------------------- | ----------------- | ------------------ |
| Transaction History | ✅ Complete       | ✅ Complete        |
| Activity Analysis   | ✅ Full           | ✅ Full            |
| Token Holdings      | ⚠️ Basic          | ✅ Accurate        |
| Token Prices        | ⚠️ External API   | ✅ Real-time       |
| NFT Collections     | ⚠️ Transfer-based | ✅ Curated         |
| Portfolio Valuation | ⚠️ Estimated      | ✅ Precise         |

## Base Chain Configuration

The persona analysis system automatically configures the EtherscanAdapter for Base chain:

- **Chain ID**: 8453 (Base mainnet)
- **API Endpoint**: Uses Etherscan's multi-chain API
- **Token Support**: Includes major Base chain tokens (USDC, WETH, DAI, USDbC)
- **Price Data**: Real-time prices via DeFiLlama API

# Modular Portfolio Analyzer

A clean, modular architecture for analyzing cryptocurrency wallets on Base chain with comprehensive persona classification.

## 🏗️ Architecture Overview

The codebase has been refactored into a modular structure for better maintainability, testability, and easier onboarding:

```
├── models/                     # Data models and structures
│   ├── __init__.py
│   └── portfolio_models.py     # TokenHolding, NFTHolding, PortfolioSnapshot
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── portfolio_service.py    # Portfolio data fetching and analysis
│   ├── activity_service.py     # Wallet activity analysis
│   └── pricing_service.py      # Token and ETH price fetching
├── persona/                    # Persona classification system
│   ├── __init__.py
│   └── persona_classifier.py   # Dynamic persona classification
├── adapters/                   # External API adapters
│   ├── __init__.py
│   ├── base.py                # BaseAdapter abstract class
│   ├── etherscan.py           # Etherscan API integration
│   └── zerion.py              # Zerion API integration
├── portfolio_analyzer_v2.py    # Main modular analyzer
├── portfolio_analyzer.py       # Legacy monolithic version
└── requirements.txt
```

## 🎯 Key Benefits of Modular Architecture

### 1. **Separation of Concerns**

- **Models**: Pure data structures with business logic
- **Services**: Focused business logic for specific domains
- **Persona**: Isolated classification logic
- **Adapters**: External API integrations

### 2. **Easy Testing**

- Each module can be unit tested independently
- Mock services for integration testing
- Clear interfaces between components

### 3. **Maintainability**

- Changes to one service don't affect others
- Easy to add new persona types or data sources
- Clear code organization

### 4. **Onboarding Friendly**

- New developers can focus on specific modules
- Clear documentation for each component
- Logical code organization

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter
from portfolio_analyzer_v2 import PortfolioAnalyzer

async def analyze_wallet():
    # Initialize adapters
    etherscan_adapter = EtherscanAdapter(api_key="your_key", chain_id=8453)
    zerion_adapter = ZerionAdapter(api_key="your_key")  # Optional

    # Use the modular analyzer
    async with PortfolioAnalyzer(etherscan_adapter, zerion_adapter) as analyzer:
        result = await analyzer.analyze_wallet("0x...")

        portfolio = result["portfolio"]
        activity = result["activity"]
        persona = result["persona"]

        print(f"Persona: {persona['classification']}")
        print(f"Portfolio Value: ${portfolio.total_value_usd:.2f}")

asyncio.run(analyze_wallet())
```

### Using Individual Services

```python
from services.portfolio_service import PortfolioService
from services.activity_service import ActivityService
from services.pricing_service import PricingService

# Use services independently
async with PortfolioService(etherscan_adapter, zerion_adapter) as portfolio_service:
    portfolio = await portfolio_service.analyze_portfolio("0x...")

activity_service = ActivityService(etherscan_adapter)
activity = await activity_service.calculate_activity_score("0x...")
```

## 📊 Persona Classification System

The system dynamically identifies four persona types:

### 🏆 OG (Conservative)

- Token holding > 60% portfolio value
- Holding period > 12 months
- Top asset value < $5,000
- Wallet created < 2020
- Holding ETH

### 💪 DeFi Chad (Moderate)

- Longest holding > 3 months
- Token holding > 50% portfolio value
- Active for over 120 days in last 12 months
- Top asset value $2,000 - $5,000

### 🎲 Degen (Aggressive)

- Active for over 180 days within 12 months
- Over 100 swap transactions within 12 months
- Holding period < 3 months
- Token holding > 70% portfolio value
- Top asset is token (not ETH)

### 🆕 Virgin CT (Newbie)

- Wallet created > 2023
- Active for over 30 days in last 12 months
- Total portfolio value < $5,000
- Total onchain transactions < 50

## 🔧 Module Details

### Models (`models/`)

**`portfolio_models.py`**

- `TokenHolding`: Represents token holdings with valuation and timing data
- `NFTHolding`: Represents NFT holdings with collection info
- `PortfolioSnapshot`: Complete portfolio state with computed properties

### Services (`services/`)

**`portfolio_service.py`**

- Fetches portfolio data from Zerion and Etherscan
- Handles token/NFT holdings analysis
- Manages pricing integration
- Provides fallback mechanisms

**`activity_service.py`**

- Analyzes wallet activity patterns
- Calculates activity scores and metrics
- Detects swap/DEX interactions
- Determines wallet creation dates

**`pricing_service.py`**

- Fetches real-time token prices from DeFiLlama
- Handles ETH price retrieval
- Manages HTTP sessions efficiently

### Persona Classification (`persona/`)

**`persona_classifier.py`**

- Dynamic persona classification logic
- Comprehensive criteria evaluation
- Formatted analysis output
- Extensible for new persona types

## 🔌 Adding New Features

### Adding a New Persona Type

1. **Update `persona_classifier.py`**:

```python
# Add new criteria in classify_persona method
if (new_criteria_check):
    return "New Persona Type", criteria
```

2. **Add formatting logic**:

```python
# Add new case in format_persona_analysis method
elif persona == "New Persona Type":
    output.append("✓ New criteria: {check}")
```

### Adding a New Data Source

1. **Create new adapter** in `adapters/`:

```python
from adapters.base import BaseAdapter

class NewAPIAdapter(BaseAdapter):
    # Implement required methods
```

2. **Update services** to use new adapter:

```python
# Add integration in portfolio_service.py or create new service
```

### Adding New Metrics

1. **Extend models** with new properties:

```python
@property
def new_metric(self) -> float:
    # Calculate new metric
```

2. **Update services** to populate new data:

```python
# Add calculation logic in appropriate service
```

## 🧪 Testing Strategy

### Unit Testing

```python
# Test individual models
def test_token_holding_properties():
    holding = TokenHolding(...)
    assert holding.holding_period_days == expected_days

# Test service methods
async def test_portfolio_service():
    service = PortfolioService(mock_adapter)
    result = await service.analyze_portfolio("0x...")
    assert result.total_value_usd > 0
```

### Integration Testing

```python
# Test full workflow
async def test_full_analysis():
    analyzer = PortfolioAnalyzer(etherscan_adapter, zerion_adapter)
    result = await analyzer.analyze_wallet("0x...")
    assert result["persona"]["classification"] in VALID_PERSONAS
```

## 📈 Performance Considerations

### Async Operations

- All I/O operations are async
- Concurrent API calls where possible
- Proper session management

### Caching Strategy

```python
# Add caching to services
from functools import lru_cache

@lru_cache(maxsize=128)
async def cached_price_fetch(token_address: str):
    # Cache expensive operations
```

### Rate Limiting

```python
# Add rate limiting to adapters
import asyncio

async def rate_limited_request():
    await asyncio.sleep(0.1)  # Respect API limits
```

## 🔒 Error Handling

### Service Level

```python
try:
    result = await service.method()
except SpecificAPIError:
    # Handle specific errors
    return fallback_result
except Exception as e:
    # Log and handle general errors
    logger.error(f"Unexpected error: {e}")
    return default_result
```

### Analyzer Level

```python
# Graceful degradation
if not zerion_adapter:
    # Fall back to Etherscan-only analysis
```

## 🚀 Migration from Legacy

To migrate from the monolithic `portfolio_analyzer.py`:

1. **Update imports**:

```python
# Old
from portfolio_analyzer import PortfolioAnalyzer

# New
from portfolio_analyzer_v2 import PortfolioAnalyzer
```

2. **API remains the same**:

```python
# Same usage pattern
async with PortfolioAnalyzer(adapters) as analyzer:
    result = await analyzer.analyze_wallet(address)
```

3. **Access to individual services**:

```python
# New capability - use services independently
portfolio_service = analyzer.portfolio_service
activity_service = analyzer.activity_service
```

## 📚 Next Steps

1. **Add comprehensive tests** for each module
2. **Implement caching** for expensive operations
3. **Add configuration management** for different environments
4. **Create CLI interface** for batch processing
5. **Add database integration** for historical analysis
6. **Implement webhook support** for real-time updates

## 🤝 Contributing

1. **Choose a module** to work on based on your expertise
2. **Follow the established patterns** in each module
3. **Add tests** for new functionality
4. **Update documentation** for any API changes
5. **Consider backward compatibility** when making changes

The modular architecture makes it easy to contribute to specific areas without understanding the entire codebase!

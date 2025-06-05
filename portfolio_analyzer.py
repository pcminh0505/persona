"""
Portfolio Analyzer for Base Chain Wallets

This module provides detailed portfolio analysis including token valuations,
holding periods, and composition metrics for persona building.
Uses Zerion API for accurate portfolio data and Etherscan for transaction history.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
import json


@dataclass
class TokenHolding:
    """Represents a token holding with valuation data."""

    contract_address: str
    symbol: str
    balance: float
    decimals: int
    price_usd: float
    value_usd: float
    first_acquired: Optional[datetime] = None
    last_acquired: Optional[datetime] = None

    @property
    def holding_period_days(self) -> int:
        """Calculate holding period in days."""
        if self.first_acquired:
            return (datetime.now() - self.first_acquired).days
        return 0


@dataclass
class NFTHolding:
    """Represents an NFT holding."""

    contract_address: str
    token_id: str
    collection_name: str
    estimated_value_usd: float = 0.0
    acquired_date: Optional[datetime] = None

    @property
    def holding_period_days(self) -> int:
        """Calculate holding period in days."""
        if self.acquired_date:
            return (datetime.now() - self.acquired_date).days
        return 0


@dataclass
class PortfolioSnapshot:
    """Represents a complete portfolio snapshot."""

    address: str
    eth_balance: float
    eth_value_usd: float
    token_holdings: List[TokenHolding]
    nft_holdings: List[NFTHolding]
    total_value_usd: float
    analysis_timestamp: datetime

    @property
    def top_asset_by_value(self) -> Tuple[str, float]:
        """Get the top asset by USD value."""
        assets = [("ETH", self.eth_value_usd)]
        assets.extend(
            [(holding.symbol, holding.value_usd) for holding in self.token_holdings]
        )
        assets.extend(
            [
                (f"NFT-{holding.collection_name}", holding.estimated_value_usd)
                for holding in self.nft_holdings
            ]
        )

        if assets:
            return max(assets, key=lambda x: x[1])
        return ("None", 0.0)

    @property
    def token_concentration_ratio(self) -> float:
        """Calculate the concentration ratio of top token holding."""
        if self.total_value_usd <= 0:
            return 0.0

        top_asset, top_value = self.top_asset_by_value
        return top_value / self.total_value_usd

    @property
    def is_top_asset_nft(self) -> bool:
        """Check if top asset is an NFT."""
        top_asset, _ = self.top_asset_by_value
        return top_asset.startswith("NFT-")

    @property
    def is_top_asset_token_not_eth(self) -> bool:
        """Check if top asset is a token but not ETH."""
        top_asset, _ = self.top_asset_by_value
        return top_asset != "ETH" and not top_asset.startswith("NFT-")

    @property
    def longest_holding_period(self) -> int:
        """Get the longest holding period in days."""
        periods = [holding.holding_period_days for holding in self.token_holdings]
        periods.extend([holding.holding_period_days for holding in self.nft_holdings])
        return max(periods) if periods else 0


class PortfolioAnalyzer:
    """Analyzes wallet portfolios for persona building using Zerion and Etherscan APIs."""

    def __init__(self, etherscan_adapter, zerion_adapter=None):
        """Initialize with EtherscanAdapter and optional ZerionAdapter."""
        self.etherscan_adapter = etherscan_adapter
        self.zerion_adapter = zerion_adapter
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def analyze_portfolio(self, address: str) -> PortfolioSnapshot:
        """Analyze a wallet's complete portfolio using Zerion and Etherscan data."""
        print(f"Analyzing portfolio for: {address}")

        # Initialize session if not in context manager
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Get portfolio data from Zerion if available
            if self.zerion_adapter:
                token_holdings, nft_holdings, eth_balance, eth_value_usd = (
                    await self._get_zerion_portfolio_data(address)
                )
            else:
                # Fallback to Etherscan-based analysis
                token_holdings = await self._get_token_holdings_etherscan(address)
                nft_holdings = await self._get_nft_holdings_etherscan(address)
                eth_balance = await self._get_eth_balance(address)

                # Get ETH price
                eth_price = await self._get_eth_price()
                eth_value_usd = eth_balance * eth_price

                # Get token prices for Etherscan-based holdings
                token_addresses = [
                    holding.contract_address for holding in token_holdings
                ]
                if token_addresses:
                    token_prices = await self._get_token_prices(token_addresses)
                    for holding in token_holdings:
                        price = token_prices.get(holding.contract_address.lower(), 0.0)
                        holding.price_usd = price
                        holding.value_usd = holding.balance * price

            # Enhance token holdings with acquisition dates from Etherscan
            await self._enhance_holdings_with_acquisition_dates(
                address, token_holdings, nft_holdings
            )

            # Calculate total portfolio value
            total_token_value = sum(holding.value_usd for holding in token_holdings)
            total_nft_value = sum(
                holding.estimated_value_usd for holding in nft_holdings
            )
            total_value_usd = eth_value_usd + total_token_value + total_nft_value

            return PortfolioSnapshot(
                address=address,
                eth_balance=eth_balance,
                eth_value_usd=eth_value_usd,
                token_holdings=token_holdings,
                nft_holdings=nft_holdings,
                total_value_usd=total_value_usd,
                analysis_timestamp=datetime.now(),
            )

        finally:
            # Only close session if we created it ourselves
            if self.session and not hasattr(self, "_context_managed"):
                await self.session.close()
                self.session = None

    async def _get_zerion_portfolio_data(
        self, address: str
    ) -> Tuple[List[TokenHolding], List[NFTHolding], float, float]:
        """Get portfolio data from Zerion API."""
        token_holdings = []
        nft_holdings = []
        eth_balance = 0.0
        eth_value_usd = 0.0

        try:
            # Get fungible positions from Zerion
            positions_response = self.zerion_adapter.get_wallet_positions(
                address,
                currency="usd",
                **{"filter[chain_ids]": "base", "page[size]": "100"},
            )

            if positions_response and positions_response.get("data"):
                for position in positions_response["data"]:
                    try:
                        attributes = position.get("attributes", {})
                        fungible_info = attributes.get("fungible_info", {})

                        if not fungible_info:
                            continue

                        # Extract token information
                        symbol = fungible_info.get("symbol", "UNKNOWN")
                        name = fungible_info.get("name", "Unknown Token")
                        implementations = fungible_info.get("implementations", [])

                        # Extract quantity and value from the correct fields with proper null handling
                        quantity_info = attributes.get("quantity", {})
                        balance = float(quantity_info.get("float", 0) or 0)
                        value_usd = float(attributes.get("value", 0) or 0)
                        price_usd = float(attributes.get("price", 0) or 0)

                        # Find Base chain implementation
                        contract_address = None
                        decimals = 18  # default

                        for impl in implementations:
                            if impl.get("chain_id") == "base":
                                contract_address = impl.get("address")
                                decimals = impl.get("decimals", 18)
                                break

                        # Handle ETH (native asset - no contract address)
                        if not contract_address and symbol.upper() == "ETH":
                            # This is native ETH
                            eth_balance += balance
                            eth_value_usd += value_usd
                            continue

                        # Handle ERC-20 tokens
                        if contract_address and balance > 0:
                            token_holdings.append(
                                TokenHolding(
                                    contract_address=contract_address.lower(),
                                    symbol=symbol,
                                    balance=balance,
                                    decimals=decimals,
                                    price_usd=price_usd,
                                    value_usd=value_usd,
                                )
                            )
                    except Exception as position_error:
                        print(f"Error processing position: {position_error}")
                        continue

            # Get NFT collections from Zerion
            nft_response = self.zerion_adapter.get_wallet_nft_collections(
                address, **{"filter[chain_ids]": "base", "page[size]": "100"}
            )

            if nft_response and nft_response.get("data"):
                for collection in nft_response["data"]:
                    try:
                        attributes = collection.get("attributes", {})
                        collection_info = attributes.get("collection_info", {})

                        collection_name = collection_info.get(
                            "name", "Unknown Collection"
                        )
                        nft_count = int(attributes.get("nfts_count", "0"))
                        total_floor_price_usd = float(
                            attributes.get("total_floor_price", 0)
                        )

                        # Extract contract address from relationships if available
                        contract_address = ""
                        nft_collection_id = ""
                        if "relationships" in collection:
                            nft_collection_data = (
                                collection["relationships"]
                                .get("nft_collection", {})
                                .get("data", {})
                            )
                            nft_collection_id = nft_collection_data.get("id", "")

                        # Create NFT holdings for each NFT in the collection
                        # Since we don't have individual NFT data, create placeholders
                        for i in range(nft_count):
                            estimated_value_per_nft = (
                                total_floor_price_usd / nft_count
                                if nft_count > 0
                                else 0.0
                            )

                            nft_holdings.append(
                                NFTHolding(
                                    contract_address=nft_collection_id,  # Use collection ID as identifier
                                    token_id=f"collection_{i}",  # Placeholder since individual token IDs aren't provided
                                    collection_name=collection_name,
                                    estimated_value_usd=estimated_value_per_nft,
                                )
                            )

                    except (ValueError, TypeError) as e:
                        print(f"Error parsing NFT collection: {e}")
                        continue

        except Exception as e:
            print(f"Error fetching Zerion portfolio data: {e}")
            # Fall back to Etherscan-based analysis
            return await self._get_etherscan_fallback_data(address)

        return token_holdings, nft_holdings, eth_balance, eth_value_usd

    async def _get_etherscan_fallback_data(
        self, address: str
    ) -> Tuple[List[TokenHolding], List[NFTHolding], float, float]:
        """Fallback to Etherscan-based portfolio analysis."""
        token_holdings = await self._get_token_holdings_etherscan(address)
        nft_holdings = await self._get_nft_holdings_etherscan(address)
        eth_balance = await self._get_eth_balance(address)

        eth_price = await self._get_eth_price()
        eth_value_usd = eth_balance * eth_price

        # Get token prices
        token_addresses = [holding.contract_address for holding in token_holdings]
        if token_addresses:
            token_prices = await self._get_token_prices(token_addresses)
            for holding in token_holdings:
                price = token_prices.get(holding.contract_address.lower(), 0.0)
                holding.price_usd = price
                holding.value_usd = holding.balance * price

        return token_holdings, nft_holdings, eth_balance, eth_value_usd

    async def _enhance_holdings_with_acquisition_dates(
        self,
        address: str,
        token_holdings: List[TokenHolding],
        nft_holdings: List[NFTHolding],
    ):
        """Enhance holdings with acquisition dates from Etherscan transaction history."""
        try:
            # Get token transfers to determine acquisition dates
            token_response = self.etherscan_adapter.get_erc20_token_transfers(
                address, page=1, offset=10000
            )
            if token_response and self.etherscan_adapter.validate_response(
                token_response
            ):
                transfers = token_response.get("result", [])

                # Group transfers by contract address
                transfer_dates = defaultdict(list)
                for transfer in transfers:
                    if (
                        transfer.get("contractAddress")
                        and transfer.get("to", "").lower() == address.lower()
                    ):
                        contract_addr = transfer["contractAddress"].lower()
                        if transfer.get("timeStamp"):
                            transfer_dates[contract_addr].append(
                                datetime.fromtimestamp(int(transfer["timeStamp"]))
                            )

                # Update token holdings with acquisition dates
                for holding in token_holdings:
                    dates = transfer_dates.get(holding.contract_address.lower(), [])
                    if dates:
                        holding.first_acquired = min(dates)
                        holding.last_acquired = max(dates)

            # Get NFT transfers for acquisition dates
            nft_response = self.etherscan_adapter.get_erc721_token_transfers(
                address, page=1, offset=1000
            )
            if nft_response and self.etherscan_adapter.validate_response(nft_response):
                transfers = nft_response.get("result", [])

                nft_dates = defaultdict(list)
                for transfer in transfers:
                    if (
                        transfer.get("contractAddress")
                        and transfer.get("to", "").lower() == address.lower()
                    ):
                        contract_addr = transfer["contractAddress"].lower()
                        if transfer.get("timeStamp"):
                            nft_dates[contract_addr].append(
                                datetime.fromtimestamp(int(transfer["timeStamp"]))
                            )

                # Update NFT holdings with acquisition dates
                for holding in nft_holdings:
                    dates = nft_dates.get(holding.contract_address.lower(), [])
                    if dates:
                        holding.acquired_date = min(dates)

        except Exception as e:
            print(f"Error enhancing holdings with acquisition dates: {e}")

    async def _get_eth_balance(self, address: str) -> float:
        """Get ETH balance for an address."""
        try:
            response = self.etherscan_adapter.get_ether_balance(address)
            if response and self.etherscan_adapter.validate_response(response):
                balance_wei = int(response.get("result", "0"))
                return balance_wei / 1e18
        except Exception as e:
            print(f"Error getting ETH balance: {e}")
        return 0.0

    async def _get_token_holdings_etherscan(self, address: str) -> List[TokenHolding]:
        """Get token holdings using Etherscan (fallback method)."""
        holdings = []

        # Known Base chain token contracts
        known_tokens = {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {
                "symbol": "USDC",
                "decimals": 6,
            },
            "0x4200000000000000000000000000000000000006": {
                "symbol": "WETH",
                "decimals": 18,
            },
            "0x50c5725949a6f0c72e6c4a641f24049a917db0cb": {
                "symbol": "DAI",
                "decimals": 18,
            },
            "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": {
                "symbol": "USDbC",
                "decimals": 6,
            },
        }

        try:
            response = self.etherscan_adapter.get_erc20_token_transfers(
                address, page=1, offset=10000
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return holdings

            transfers = response.get("result", [])
            token_transfers = defaultdict(list)

            for transfer in transfers:
                if transfer.get("contractAddress"):
                    token_transfers[transfer["contractAddress"].lower()].append(
                        transfer
                    )

            for contract_address, token_transfers_list in token_transfers.items():
                balance = await self._calculate_token_balance(
                    address, contract_address, token_transfers_list
                )

                if balance > 0:
                    token_info = known_tokens.get(contract_address, {})
                    symbol = token_info.get("symbol", f"TOKEN-{contract_address[:6]}")
                    decimals = token_info.get("decimals", 18)
                    actual_balance = balance / (10**decimals)

                    holdings.append(
                        TokenHolding(
                            contract_address=contract_address,
                            symbol=symbol,
                            balance=actual_balance,
                            decimals=decimals,
                            price_usd=0.0,
                            value_usd=0.0,
                        )
                    )

        except Exception as e:
            print(f"Error getting token holdings: {e}")

        return holdings

    async def _calculate_token_balance(
        self, address: str, contract_address: str, transfers: List[Dict]
    ) -> float:
        """Calculate current token balance from transfer history."""
        balance = 0.0

        for transfer in transfers:
            try:
                value = float(transfer.get("value", "0"))
                from_addr = transfer.get("from", "").lower()
                to_addr = transfer.get("to", "").lower()
                address_lower = address.lower()

                if to_addr == address_lower:
                    balance += value
                elif from_addr == address_lower:
                    balance -= value
            except (ValueError, TypeError):
                continue

        return max(0.0, balance)

    async def _get_nft_holdings_etherscan(self, address: str) -> List[NFTHolding]:
        """Get NFT holdings using Etherscan (fallback method)."""
        holdings = []

        try:
            response = self.etherscan_adapter.get_erc721_token_transfers(
                address, page=1, offset=1000
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return holdings

            transfers = response.get("result", [])
            nft_transfers = defaultdict(list)

            for transfer in transfers:
                if transfer.get("contractAddress") and transfer.get("tokenID"):
                    key = (transfer["contractAddress"].lower(), transfer["tokenID"])
                    nft_transfers[key].append(transfer)

            for (
                contract_address,
                token_id,
            ), token_transfers_list in nft_transfers.items():
                latest_transfer = max(
                    token_transfers_list, key=lambda x: int(x.get("timeStamp", "0"))
                )

                if latest_transfer.get("to", "").lower() == address.lower():
                    acquired_date = datetime.fromtimestamp(
                        int(latest_transfer.get("timeStamp", "0"))
                    )
                    collection_name = latest_transfer.get(
                        "tokenName", f"Collection-{contract_address[:6]}"
                    )

                    holdings.append(
                        NFTHolding(
                            contract_address=contract_address,
                            token_id=token_id,
                            collection_name=collection_name,
                            estimated_value_usd=0.0,
                            acquired_date=acquired_date,
                        )
                    )

        except Exception as e:
            print(f"Error getting NFT holdings: {e}")

        return holdings

    async def _get_token_prices(
        self, token_addresses: List[str], chain: str = "base"
    ) -> Dict[str, float]:
        """Get token prices from DeFiLlama API."""
        if not self.session or not token_addresses:
            return {}

        try:
            addresses_str = ",".join([f"{chain}:{addr}" for addr in token_addresses])
            url = f"https://coins.llama.fi/prices/current/{addresses_str}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = {}

                    for key, value in data.get("coins", {}).items():
                        if ":" in key:
                            address = key.split(":", 1)[1]
                            prices[address.lower()] = value.get("price", 0.0)

                    return prices
        except Exception as e:
            print(f"Error fetching token prices: {e}")

        return {}

    async def _get_eth_price(self) -> float:
        """Get current ETH price."""
        if not self.session:
            return 0.0

        try:
            url = "https://coins.llama.fi/prices/current/ethereum:0x0000000000000000000000000000000000000000"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return (
                        data.get("coins", {})
                        .get("ethereum:0x0000000000000000000000000000000000000000", {})
                        .get("price", 0.0)
                    )
        except Exception as e:
            print(f"Error fetching ETH price: {e}")

        return 0.0

    async def analyze_swap_activity(
        self, address: str, days: int = 365
    ) -> Dict[str, Any]:
        """Analyze swap/DEX activity for an address using Etherscan data."""
        try:
            since_date = datetime.now() - timedelta(days=days)

            response = self.etherscan_adapter.get_erc20_token_transfers(
                address, page=1, offset=10000
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return {"swap_count": 0, "unique_tokens": 0, "dex_interactions": 0}

            transfers = response.get("result", [])
            tx_transfers = defaultdict(list)
            unique_tokens = set()
            swap_count = 0

            for transfer in transfers:
                if transfer.get("timeStamp"):
                    transfer_date = datetime.fromtimestamp(int(transfer["timeStamp"]))
                    if transfer_date >= since_date:
                        tx_hash = transfer.get("hash")
                        if tx_hash:
                            tx_transfers[tx_hash].append(transfer)
                            if transfer.get("contractAddress"):
                                unique_tokens.add(transfer["contractAddress"].lower())

            for tx_hash, tx_transfer_list in tx_transfers.items():
                if len(tx_transfer_list) >= 2:
                    swap_count += 1

            return {
                "swap_count": swap_count,
                "unique_tokens": len(unique_tokens),
                "dex_interactions": len(tx_transfers),
            }

        except Exception as e:
            print(f"Error analyzing swap activity: {e}")
            return {"swap_count": 0, "unique_tokens": 0, "dex_interactions": 0}

    async def calculate_activity_score(
        self, address: str, days: int = 365
    ) -> Dict[str, int]:
        """Calculate wallet activity metrics using Etherscan data."""
        try:
            since_date = datetime.now() - timedelta(days=days)

            response = self.etherscan_adapter.get_normal_transactions(
                address, page=1, offset=10000
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return {"active_days": 0, "total_transactions": 0}

            transactions = response.get("result", [])
            active_days = set()
            total_transactions = 0

            for tx in transactions:
                if tx.get("timeStamp"):
                    tx_date = datetime.fromtimestamp(int(tx["timeStamp"]))
                    if tx_date >= since_date:
                        active_days.add(tx_date.date())
                        total_transactions += 1

            return {
                "active_days": len(active_days),
                "total_transactions": total_transactions,
            }

        except Exception as e:
            print(f"Error calculating activity score: {e}")
            return {"active_days": 0, "total_transactions": 0}


# Example usage
async def main():
    """Example usage of the PortfolioAnalyzer with Zerion integration."""
    from adapters.etherscan import EtherscanAdapter
    from adapters.zerion import ZerionAdapter

    # Initialize adapters
    etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
    zerion_api_key = os.getenv("ZERION_API_KEY")

    if not etherscan_api_key:
        print("Please set ETHERSCAN_API_KEY environment variable")
        return

    # Create adapters
    base_adapter = EtherscanAdapter(api_key=etherscan_api_key, chain_id=8453)
    zerion_adapter = ZerionAdapter(api_key=zerion_api_key) if zerion_api_key else None

    # Use context manager for proper session handling
    async with PortfolioAnalyzer(base_adapter, zerion_adapter) as analyzer:
        # Example wallet address
        test_address = "0x6c34c667632dc1aaf04f362516e6f44d006a58fa"

        # Analyze portfolio
        portfolio = await analyzer.analyze_portfolio(test_address)

        print(f"\n=== Portfolio Analysis (Zerion + Etherscan) ===")
        print(f"Address: {portfolio.address}")
        print(f"Total Value: ${portfolio.total_value_usd:.2f}")
        print(
            f"ETH Balance: {portfolio.eth_balance:.4f} ETH (${portfolio.eth_value_usd:.2f})"
        )
        print(f"Token Holdings: {len(portfolio.token_holdings)}")
        print(f"NFT Holdings: {len(portfolio.nft_holdings)}")

        print(f"\n=== Key Metrics ===")
        top_asset, top_value = portfolio.top_asset_by_value
        print(f"Top Asset: {top_asset} (${top_value:.2f})")
        print(f"Token Concentration: {portfolio.token_concentration_ratio:.1%}")
        print(f"Longest Holding Period: {portfolio.longest_holding_period} days")
        print(f"Top Asset is NFT: {portfolio.is_top_asset_nft}")
        print(f"Top Asset is Token (not ETH): {portfolio.is_top_asset_token_not_eth}")

        # Show token holdings details
        if portfolio.token_holdings:
            print(f"\n=== Token Holdings ===")
            for holding in portfolio.token_holdings[:5]:  # Show top 5
                holding_days = holding.holding_period_days
                print(
                    f"  {holding.symbol}: {holding.balance:.4f} (${holding.value_usd:.2f}) - Held for {holding_days} days"
                )

        # Analyze activity
        activity = await analyzer.calculate_activity_score(test_address)
        swap_activity = await analyzer.analyze_swap_activity(test_address)

        print(f"\n=== Activity Metrics ===")
        print(f"Active Days (last 365): {activity['active_days']}")
        print(f"Total Transactions: {activity['total_transactions']}")
        print(f"Swap Count: {swap_activity['swap_count']}")
        print(f"Unique Tokens Traded: {swap_activity['unique_tokens']}")


if __name__ == "__main__":
    asyncio.run(main())

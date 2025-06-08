"""
Portfolio service for fetching and analyzing wallet portfolios.

This service handles portfolio data collection from various sources including
Zerion and Etherscan, token/NFT holdings analysis, and portfolio composition.
"""

import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from models.portfolio_models import TokenHolding, NFTHolding, PortfolioSnapshot
from services.pricing_service import PricingService


class PortfolioService:
    """Service for fetching and analyzing wallet portfolios."""

    def __init__(self, etherscan_adapter, zerion_adapter=None):
        """Initialize with EtherscanAdapter and optional ZerionAdapter."""
        self.etherscan_adapter = etherscan_adapter
        self.zerion_adapter = zerion_adapter
        self.session: Optional[aiohttp.ClientSession] = None
        self.pricing_service: Optional[PricingService] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        self.pricing_service = PricingService(self.session)
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
            self.pricing_service = PricingService(self.session)

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
                eth_price = await self.pricing_service.get_eth_price()
                eth_value_usd = eth_balance * eth_price

                # Get token prices for Etherscan-based holdings
                token_addresses = [
                    holding.contract_address for holding in token_holdings
                ]
                if token_addresses:
                    token_prices = await self.pricing_service.get_token_prices(
                        token_addresses
                    )
                    for holding in token_holdings:
                        price = token_prices.get(holding.contract_address.lower(), 0.0)
                        holding.price_usd = price
                        holding.value_usd = holding.balance * price

            # Enhance token holdings with acquisition dates from Etherscan
            await self._enhance_holdings_with_acquisition_dates(
                address, token_holdings, nft_holdings
            )

            # Print detailed portfolio breakdown
            await self._print_portfolio_breakdown(
                address, token_holdings, nft_holdings, eth_balance, eth_value_usd
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

    async def _print_portfolio_breakdown(
        self,
        address: str,
        token_holdings: List[TokenHolding],
        nft_holdings: List[NFTHolding],
        eth_balance: float,
        eth_value_usd: float,
    ):
        """Print detailed portfolio breakdown ordered by value."""
        print(f"\n💰 PORTFOLIO BREAKDOWN FOR {address}")
        print("=" * 80)

        # Calculate total portfolio value
        total_token_value = sum(holding.value_usd for holding in token_holdings)
        total_nft_value = sum(holding.estimated_value_usd for holding in nft_holdings)
        total_value_usd = eth_value_usd + total_token_value + total_nft_value

        print(f"📊 Total Portfolio Value: ${total_value_usd:,.2f}")
        print(f"   💎 ETH: ${eth_value_usd:,.2f} ({eth_balance:.4f} ETH)")
        print(f"   🪙 Tokens: ${total_token_value:,.2f}")
        print(f"   🖼️  NFTs: ${total_nft_value:,.2f}")

        # Calculate significant positions (>$5)
        significant_tokens = [t for t in token_holdings if t.value_usd > 5.0]
        significant_nfts = [n for n in nft_holdings if n.estimated_value_usd > 5.0]
        significant_eth = eth_value_usd > 5.0

        significant_token_value = sum(t.value_usd for t in significant_tokens)
        significant_nft_value = sum(n.estimated_value_usd for n in significant_nfts)
        significant_eth_value = eth_value_usd if significant_eth else 0
        total_significant_value = (
            significant_eth_value + significant_token_value + significant_nft_value
        )

        # Calculate dust positions (<$5)
        dust_tokens = [t for t in token_holdings if 0 < t.value_usd <= 5.0]
        dust_nfts = [n for n in nft_holdings if 0 < n.estimated_value_usd <= 5.0]
        dust_eth = 0 < eth_value_usd <= 5.0

        dust_token_value = sum(t.value_usd for t in dust_tokens)
        dust_nft_value = sum(n.estimated_value_usd for n in dust_nfts)
        dust_eth_value = eth_value_usd if dust_eth else 0
        total_dust_value = dust_eth_value + dust_token_value + dust_nft_value

        total_significant_positions = (
            (1 if significant_eth else 0)
            + len(significant_tokens)
            + len(significant_nfts)
        )
        total_dust_positions = (
            (1 if dust_eth else 0) + len(dust_tokens) + len(dust_nfts)
        )

        print(f"\n🔍 POSITION ANALYSIS:")
        print(
            f"   💰 Significant positions (>$5): {total_significant_positions} positions, ${total_significant_value:,.2f} ({total_significant_value/total_value_usd*100:.1f}%)"
        )
        print(
            f"   🧹 Dust positions (≤$5): {total_dust_positions} positions, ${total_dust_value:,.2f} ({total_dust_value/total_value_usd*100:.1f}%)"
        )

        # Print fungible positions ordered by value
        await self._print_fungible_positions(token_holdings, eth_balance, eth_value_usd)

        # Print NFT collections ordered by value
        await self._print_nft_collections(nft_holdings)

    async def _print_fungible_positions(
        self,
        token_holdings: List[TokenHolding],
        eth_balance: float,
        eth_value_usd: float,
    ):
        """Print fungible positions ordered by value with holding periods."""
        print(f"\n🪙 FUNGIBLE POSITIONS (Ordered by Value, >$5 USD)")
        print("-" * 80)

        # Create combined list with ETH and tokens
        all_positions = []

        # Add ETH position (only if value > $5)
        if eth_balance > 0 and eth_value_usd > 5.0:
            all_positions.append(
                {
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "balance": eth_balance,
                    "value_usd": eth_value_usd,
                    "price_usd": eth_value_usd / eth_balance if eth_balance > 0 else 0,
                    "contract_address": "native",
                    "holding_period_days": (
                        getattr(token_holdings[0], "holding_period_days", 0)
                        if token_holdings
                        else 0
                    ),
                    "acquisition_date": (
                        getattr(token_holdings[0], "acquisition_date", None)
                        if token_holdings
                        else None
                    ),
                }
            )

        # Add token positions (only if value > $5)
        for holding in token_holdings:
            if holding.value_usd > 5.0:
                all_positions.append(
                    {
                        "symbol": holding.symbol,
                        "name": getattr(holding, "name", holding.symbol),
                        "balance": holding.balance,
                        "value_usd": holding.value_usd,
                        "price_usd": holding.price_usd,
                        "contract_address": holding.contract_address,
                        "holding_period_days": holding.holding_period_days,
                        "acquisition_date": holding.acquisition_date,
                    }
                )

        # Sort by value (descending)
        all_positions.sort(key=lambda x: x["value_usd"], reverse=True)

        if not all_positions:
            print("   No fungible positions found with value > $5")
            return

        print(f"   Found {len(all_positions)} positions with value > $5")
        print()
        print(
            f"{'Rank':<4} {'Symbol':<12} {'Balance':<18} {'Value (USD)':<15} {'Price':<12} {'Holding Period':<15} {'Acquired':<12}"
        )
        print("-" * 80)

        for i, position in enumerate(all_positions, 1):
            balance_str = f"{position['balance']:,.4f}".rstrip("0").rstrip(".")
            value_str = f"${position['value_usd']:,.2f}"
            price_str = (
                f"${position['price_usd']:,.4f}" if position["price_usd"] > 0 else "N/A"
            )

            # Format holding period
            holding_period = position["holding_period_days"]
            if holding_period > 0:
                if holding_period >= 365:
                    period_str = f"{holding_period/365:.1f}y"
                elif holding_period >= 30:
                    period_str = f"{holding_period/30:.1f}m"
                else:
                    period_str = f"{holding_period}d"
            else:
                period_str = "Unknown"

            # Format acquisition date
            acq_date = position["acquisition_date"]
            acq_str = acq_date.strftime("%Y-%m-%d") if acq_date else "Unknown"

            print(
                f"{i:<4} {position['symbol']:<12} {balance_str:<18} {value_str:<15} {price_str:<12} {period_str:<15} {acq_str:<12}"
            )

            # Show percentage of portfolio
            total_portfolio = sum(p["value_usd"] for p in all_positions)
            if total_portfolio > 0:
                percentage = (position["value_usd"] / total_portfolio) * 100
                print(f"     📈 {percentage:.1f}% of portfolio")

            # Show contract address for tokens
            if position["contract_address"] != "native":
                print(f"     📄 Contract: {position['contract_address']}")

            print()

    async def _print_nft_collections(self, nft_holdings: List[NFTHolding]):
        """Print NFT collections ordered by value with holding periods."""
        print(f"\n🖼️  NFT COLLECTIONS (Ordered by Value, >$5 USD)")
        print("-" * 80)

        if not nft_holdings:
            print("   No NFT collections found")
            return

        # Filter NFT holdings by value > $5
        filtered_nfts = [nft for nft in nft_holdings if nft.estimated_value_usd > 5.0]

        if not filtered_nfts:
            print("   No NFT collections found with value > $5")
            return

        # Sort NFT holdings by estimated value (descending)
        sorted_nfts = sorted(
            filtered_nfts, key=lambda x: x.estimated_value_usd, reverse=True
        )

        print(f"   Found {len(sorted_nfts)} collections with value > $5")
        print()
        print(
            f"{'Rank':<4} {'Collection':<25} {'Count':<8} {'Est. Value':<15} {'Floor Price':<12} {'Holding Period':<15} {'Acquired':<12}"
        )
        print("-" * 80)

        for i, nft in enumerate(sorted_nfts, 1):
            collection_name = (
                nft.collection_name[:22] + "..."
                if len(nft.collection_name) > 25
                else nft.collection_name
            )
            value_str = f"${nft.estimated_value_usd:,.2f}"
            floor_str = (
                f"${nft.floor_price_usd:,.2f}" if nft.floor_price_usd > 0 else "N/A"
            )

            # Format holding period
            holding_period = nft.holding_period_days
            if holding_period > 0:
                if holding_period >= 365:
                    period_str = f"{holding_period/365:.1f}y"
                elif holding_period >= 30:
                    period_str = f"{holding_period/30:.1f}m"
                else:
                    period_str = f"{holding_period}d"
            else:
                period_str = "Unknown"

            # Format acquisition date
            acq_str = (
                nft.acquisition_date.strftime("%Y-%m-%d")
                if nft.acquisition_date
                else "Unknown"
            )

            print(
                f"{i:<4} {collection_name:<25} {nft.token_count:<8} {value_str:<15} {floor_str:<12} {period_str:<15} {acq_str:<12}"
            )

            # Show percentage of NFT portfolio
            total_nft_value = sum(n.estimated_value_usd for n in sorted_nfts)
            if total_nft_value > 0:
                percentage = (nft.estimated_value_usd / total_nft_value) * 100
                print(f"     📈 {percentage:.1f}% of NFT portfolio")

            # Show contract address
            print(f"     📄 Contract: {nft.contract_address}")

            # Show individual token IDs if available and count is reasonable
            if hasattr(nft, "token_ids") and nft.token_ids and len(nft.token_ids) <= 10:
                token_ids_str = ", ".join(map(str, nft.token_ids[:5]))
                if len(nft.token_ids) > 5:
                    token_ids_str += f" ... (+{len(nft.token_ids) - 5} more)"
                print(f"     🏷️  Token IDs: {token_ids_str}")

            print()

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
                **{"filter[chain_ids]": "base,ethereum", "page[size]": "100"},
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

                        if value_usd < 1:
                            continue

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
                address, **{"filter[chain_ids]": "base,ethereum", "page[size]": "100"}
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

                        if total_floor_price_usd < 1:
                            continue

                        # Calculate floor price per NFT
                        floor_price_per_nft = (
                            total_floor_price_usd / nft_count if nft_count > 0 else 0.0
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

                            # Try to extract actual contract address from the collection ID
                            # Zerion collection IDs often contain the contract address
                            if ":" in nft_collection_id:
                                parts = nft_collection_id.split(":")
                                if len(parts) >= 2:
                                    contract_address = parts[
                                        1
                                    ]  # Usually format is "chain:address"
                            else:
                                contract_address = nft_collection_id

                        # Create a single NFT holding representing the entire collection
                        # This is more efficient than creating individual entries for each NFT
                        if nft_count > 0:
                            nft_holdings.append(
                                NFTHolding(
                                    contract_address=contract_address
                                    or nft_collection_id,
                                    token_id="collection",  # Indicates this is a collection-level entry
                                    collection_name=collection_name,
                                    estimated_value_usd=total_floor_price_usd,
                                    floor_price_usd=floor_price_per_nft,
                                    token_count=nft_count,
                                    token_ids=None,  # Will be populated later if needed
                                )
                            )

                            print(
                                f"   🖼️  Found collection: {collection_name} ({nft_count} NFTs, ${total_floor_price_usd:.2f})"
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

        eth_price = await self.pricing_service.get_eth_price()
        eth_value_usd = eth_balance * eth_price

        # Get token prices
        token_addresses = [holding.contract_address for holding in token_holdings]
        if token_addresses:
            token_prices = await self.pricing_service.get_token_prices(token_addresses)
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
        """Enhanced holdings with detailed acquisition dates and holding periods from Etherscan."""
        print("🔍 Calculating holding periods from on-chain activities...")

        try:
            # Enhanced ERC20 token analysis
            await self._analyze_erc20_holding_periods(address, token_holdings)

            # Enhanced ERC721 NFT analysis
            await self._analyze_erc721_holding_periods(address, nft_holdings)

            # Also analyze ERC1155 tokens if any
            await self._analyze_erc1155_holding_periods(address, nft_holdings)

        except Exception as e:
            print(f"Error enhancing holdings with acquisition dates: {e}")

    async def _analyze_erc20_holding_periods(
        self, address: str, token_holdings: List[TokenHolding]
    ):
        """Analyze ERC20 token holding periods with detailed transaction history from multiple chains."""
        try:
            # Get comprehensive ERC20 transfer history from all supported chains
            print(f"📊 Fetching ERC20 transfers from all chains...")

            # Use the new multi-chain method if available
            if hasattr(self.etherscan_adapter, "get_erc20_token_transfers_all_chains"):
                # Multi-chain adapter - get data from all chains
                all_chains_response = (
                    self.etherscan_adapter.get_erc20_token_transfers_all_chains(
                        address, page=1, offset=10000
                    )
                )

                # Aggregate transfers from all chains
                all_transfers = []
                for chain_id, chain_response in all_chains_response.items():
                    if chain_response and self.etherscan_adapter.validate_response(
                        chain_response
                    ):
                        chain_transfers = chain_response.get("result", [])
                        # Add chain_id to each transfer for tracking
                        for transfer in chain_transfers:
                            transfer["source_chain_id"] = chain_id
                        all_transfers.extend(chain_transfers)
                        chain_name = getattr(
                            self.etherscan_adapter, "chain_names", {}
                        ).get(chain_id, f"Chain {chain_id}")
                        print(f"   🔗 {chain_name}: {len(chain_transfers)} transfers")
                    else:
                        chain_name = getattr(
                            self.etherscan_adapter, "chain_names", {}
                        ).get(chain_id, f"Chain {chain_id}")
                        print(f"   ❌ {chain_name}: Failed to fetch transfers")

                print(
                    f"📊 Total ERC20 transfers across all chains: {len(all_transfers)}"
                )

            else:
                # Fallback to single-chain adapter
                token_response = self.etherscan_adapter.get_erc20_token_transfers(
                    address, page=1, offset=10000
                )

                if not token_response or not self.etherscan_adapter.validate_response(
                    token_response
                ):
                    print("⚠️  Could not fetch ERC20 transfer history")
                    return

                all_transfers = token_response.get("result", [])
                print(f"📊 Analyzing {len(all_transfers)} ERC20 transfers...")

            # Group transfers by contract address
            contract_transfers = defaultdict(list)
            for transfer in all_transfers:
                if transfer.get("contractAddress"):
                    contract_addr = transfer["contractAddress"].lower()
                    contract_transfers[contract_addr].append(transfer)

            # Analyze each token holding
            for holding in token_holdings:
                contract_addr = holding.contract_address.lower()
                transfers_for_token = contract_transfers.get(contract_addr, [])

                if not transfers_for_token:
                    continue

                # Sort transfers by timestamp
                transfers_for_token.sort(key=lambda x: int(x.get("timeStamp", "0")))

                # Calculate detailed holding metrics
                holding_analysis = self._calculate_detailed_holding_metrics(
                    address, transfers_for_token, "ERC20"
                )

                # Update holding with calculated metrics
                holding.acquisition_date = holding_analysis["first_acquisition"]
                holding.last_activity_date = holding_analysis["last_activity"]
                holding.holding_period_days = holding_analysis["holding_period_days"]
                holding.total_acquired = holding_analysis["total_acquired"]
                holding.total_sold = holding_analysis["total_sold"]
                holding.acquisition_transactions = holding_analysis["acquisition_count"]
                holding.sale_transactions = holding_analysis["sale_count"]

                # Log which chains this token was active on
                chains_involved = set(
                    t.get("source_chain_id")
                    for t in transfers_for_token
                    if t.get("source_chain_id")
                )
                if chains_involved and hasattr(self.etherscan_adapter, "chain_names"):
                    chain_names = [
                        self.etherscan_adapter.chain_names.get(cid, f"Chain {cid}")
                        for cid in chains_involved
                    ]
                    print(
                        f"   🪙 {holding.symbol}: {holding.holding_period_days} days holding period (active on: {', '.join(chain_names)})"
                    )

        except Exception as e:
            print(f"Error analyzing ERC20 holding periods: {e}")

    async def _analyze_erc721_holding_periods(
        self, address: str, nft_holdings: List[NFTHolding]
    ):
        """Analyze ERC721 NFT holding periods with detailed transaction history from multiple chains."""
        try:
            # Get ERC721 transfer history from all supported chains
            print(f"🖼️  Fetching ERC721 transfers from all chains...")

            # Use the new multi-chain method if available
            if hasattr(self.etherscan_adapter, "get_erc721_token_transfers_all_chains"):
                # Multi-chain adapter - get data from all chains
                all_chains_response = (
                    self.etherscan_adapter.get_erc721_token_transfers_all_chains(
                        address, page=1, offset=1000
                    )
                )

                # Aggregate transfers from all chains
                all_transfers = []
                for chain_id, chain_response in all_chains_response.items():
                    if chain_response and self.etherscan_adapter.validate_response(
                        chain_response
                    ):
                        chain_transfers = chain_response.get("result", [])
                        # Add chain_id to each transfer for tracking
                        for transfer in chain_transfers:
                            transfer["source_chain_id"] = chain_id
                        all_transfers.extend(chain_transfers)
                        chain_name = getattr(
                            self.etherscan_adapter, "chain_names", {}
                        ).get(chain_id, f"Chain {chain_id}")
                        print(f"   🔗 {chain_name}: {len(chain_transfers)} transfers")
                    else:
                        chain_name = getattr(
                            self.etherscan_adapter, "chain_names", {}
                        ).get(chain_id, f"Chain {chain_id}")
                        print(f"   ❌ {chain_name}: Failed to fetch transfers")

                print(
                    f"🖼️  Total ERC721 transfers across all chains: {len(all_transfers)}"
                )

            else:
                # Fallback to single-chain adapter
                nft_response = self.etherscan_adapter.get_erc721_token_transfers(
                    address, page=1, offset=1000
                )

                if not nft_response or not self.etherscan_adapter.validate_response(
                    nft_response
                ):
                    print("⚠️  Could not fetch ERC721 transfer history")
                    return

                all_transfers = nft_response.get("result", [])
                print(f"🖼️  Analyzing {len(all_transfers)} ERC721 transfers...")

            # Group transfers by contract address and token ID
            nft_transfers = defaultdict(list)
            collection_transfers = defaultdict(list)

            for transfer in all_transfers:
                if transfer.get("contractAddress"):
                    contract_addr = transfer["contractAddress"].lower()
                    token_id = transfer.get("tokenID", "")

                    # Group by individual NFT
                    nft_key = (contract_addr, token_id)
                    nft_transfers[nft_key].append(transfer)

                    # Group by collection
                    collection_transfers[contract_addr].append(transfer)

            # Analyze each NFT holding
            for holding in nft_holdings:
                contract_addr = holding.contract_address.lower()

                # For individual NFTs
                if hasattr(holding, "token_id") and holding.token_id:
                    nft_key = (contract_addr, str(holding.token_id))
                    transfers_for_nft = nft_transfers.get(nft_key, [])

                    if transfers_for_nft:
                        transfers_for_nft.sort(
                            key=lambda x: int(x.get("timeStamp", "0"))
                        )
                        holding_analysis = self._calculate_detailed_holding_metrics(
                            address, transfers_for_nft, "ERC721"
                        )

                        holding.acquisition_date = holding_analysis["first_acquisition"]
                        holding.holding_period_days = holding_analysis[
                            "holding_period_days"
                        ]

                # For collections (aggregate data)
                else:
                    collection_transfers_list = collection_transfers.get(
                        contract_addr, []
                    )
                    if collection_transfers_list:
                        collection_transfers_list.sort(
                            key=lambda x: int(x.get("timeStamp", "0"))
                        )

                        # Find earliest acquisition for this collection
                        acquisitions = [
                            t
                            for t in collection_transfers_list
                            if t.get("to", "").lower() == address.lower()
                        ]

                        if acquisitions:
                            earliest_acquisition = min(
                                acquisitions, key=lambda x: int(x.get("timeStamp", "0"))
                            )
                            holding.acquisition_date = datetime.fromtimestamp(
                                int(earliest_acquisition["timeStamp"])
                            )
                            holding.holding_period_days = (
                                datetime.now() - holding.acquisition_date
                            ).days

                            # Log which chains this collection was active on
                            chains_involved = set(
                                t.get("source_chain_id")
                                for t in collection_transfers_list
                                if t.get("source_chain_id")
                            )
                            if chains_involved and hasattr(
                                self.etherscan_adapter, "chain_names"
                            ):
                                chain_names = [
                                    self.etherscan_adapter.chain_names.get(
                                        cid, f"Chain {cid}"
                                    )
                                    for cid in chains_involved
                                ]
                                print(
                                    f"   🖼️  {holding.collection_name}: {holding.holding_period_days} days holding period (active on: {', '.join(chain_names)})"
                                )

        except Exception as e:
            print(f"Error analyzing ERC721 holding periods: {e}")

    async def _analyze_erc1155_holding_periods(
        self, address: str, nft_holdings: List[NFTHolding]
    ):
        """Analyze ERC1155 token holding periods from multiple chains."""
        try:
            # Get ERC1155 transfer history from all supported chains
            print(f"🎨 Fetching ERC1155 transfers from all chains...")

            # Use the new multi-chain method if available
            if hasattr(
                self.etherscan_adapter, "get_erc1155_token_transfers_all_chains"
            ):
                # Multi-chain adapter - get data from all chains
                all_chains_response = (
                    self.etherscan_adapter.get_erc1155_token_transfers_all_chains(
                        address, page=1, offset=1000
                    )
                )

                # Aggregate transfers from all chains
                all_transfers = []
                for chain_id, chain_response in all_chains_response.items():
                    if chain_response and self.etherscan_adapter.validate_response(
                        chain_response
                    ):
                        chain_transfers = chain_response.get("result", [])
                        # Add chain_id to each transfer for tracking
                        for transfer in chain_transfers:
                            transfer["source_chain_id"] = chain_id
                        all_transfers.extend(chain_transfers)
                        chain_name = getattr(
                            self.etherscan_adapter, "chain_names", {}
                        ).get(chain_id, f"Chain {chain_id}")
                        if chain_transfers:
                            print(
                                f"   🔗 {chain_name}: {len(chain_transfers)} transfers"
                            )
                    else:
                        chain_name = getattr(
                            self.etherscan_adapter, "chain_names", {}
                        ).get(chain_id, f"Chain {chain_id}")
                        if (
                            chain_response is not None
                        ):  # Only log if there was actually an error
                            print(f"   ❌ {chain_name}: Failed to fetch transfers")

                if all_transfers:
                    print(
                        f"🎨 Total ERC1155 transfers across all chains: {len(all_transfers)}"
                    )

            else:
                # Fallback to single-chain adapter
                erc1155_response = self.etherscan_adapter.get_erc1155_token_transfers(
                    address, page=1, offset=1000
                )

                if (
                    not erc1155_response
                    or not self.etherscan_adapter.validate_response(erc1155_response)
                ):
                    return

                all_transfers = erc1155_response.get("result", [])
                if all_transfers:
                    print(f"🎨 Analyzing {len(all_transfers)} ERC1155 transfers...")

            if not all_transfers:
                return

            # Group transfers by contract address and token ID
            erc1155_transfers = defaultdict(list)

            for transfer in all_transfers:
                if transfer.get("contractAddress"):
                    contract_addr = transfer["contractAddress"].lower()
                    token_id = transfer.get("tokenID", "")

                    nft_key = (contract_addr, token_id)
                    erc1155_transfers[nft_key].append(transfer)

            # Update existing NFT holdings or create new ones for ERC1155
            for (contract_addr, token_id), transfers_list in erc1155_transfers.items():
                transfers_list.sort(key=lambda x: int(x.get("timeStamp", "0")))

                # Check if we have current balance
                latest_transfer = max(
                    transfers_list, key=lambda x: int(x.get("timeStamp", "0"))
                )
                if latest_transfer.get("to", "").lower() == address.lower():
                    holding_analysis = self._calculate_detailed_holding_metrics(
                        address, transfers_list, "ERC1155"
                    )

                    # Find existing holding or create new one
                    existing_holding = None
                    for holding in nft_holdings:
                        if (
                            holding.contract_address.lower() == contract_addr
                            and hasattr(holding, "token_id")
                            and str(holding.token_id) == token_id
                        ):
                            existing_holding = holding
                            break

                    if existing_holding:
                        existing_holding.acquisition_date = holding_analysis[
                            "first_acquisition"
                        ]
                        existing_holding.holding_period_days = holding_analysis[
                            "holding_period_days"
                        ]

                        # Log which chains this token was active on
                        chains_involved = set(
                            t.get("source_chain_id")
                            for t in transfers_list
                            if t.get("source_chain_id")
                        )
                        if chains_involved and hasattr(
                            self.etherscan_adapter, "chain_names"
                        ):
                            chain_names = [
                                self.etherscan_adapter.chain_names.get(
                                    cid, f"Chain {cid}"
                                )
                                for cid in chains_involved
                            ]
                            print(
                                f"   🎨 ERC1155 {token_id}: {existing_holding.holding_period_days} days holding period (active on: {', '.join(chain_names)})"
                            )

        except Exception as e:
            print(f"Error analyzing ERC1155 holding periods: {e}")

    def _calculate_detailed_holding_metrics(
        self, address: str, transfers: List[Dict], token_type: str
    ) -> Dict:
        """Calculate detailed holding metrics from transfer history."""
        address_lower = address.lower()

        # Initialize metrics
        metrics = {
            "first_acquisition": None,
            "last_activity": None,
            "holding_period_days": 0,
            "total_acquired": 0,
            "total_sold": 0,
            "acquisition_count": 0,
            "sale_count": 0,
            "current_balance": 0,
        }

        acquisitions = []
        sales = []
        current_balance = 0

        for transfer in transfers:
            try:
                timestamp = int(transfer.get("timeStamp", "0"))
                transfer_date = datetime.fromtimestamp(timestamp)
                from_addr = transfer.get("from", "").lower()
                to_addr = transfer.get("to", "").lower()

                if token_type == "ERC721":
                    # For NFTs, each transfer is 1 token
                    value = 1
                elif token_type == "ERC1155":
                    # For ERC1155, use the value field
                    value = int(transfer.get("value", "0"))
                else:
                    # For ERC20, use the value field
                    value = float(transfer.get("value", "0"))

                # Track acquisitions (incoming transfers)
                if to_addr == address_lower:
                    acquisitions.append(
                        {"date": transfer_date, "value": value, "from": from_addr}
                    )
                    current_balance += value
                    metrics["acquisition_count"] += 1
                    metrics["total_acquired"] += value

                # Track sales (outgoing transfers)
                elif from_addr == address_lower:
                    sales.append({"date": transfer_date, "value": value, "to": to_addr})
                    current_balance -= value
                    metrics["sale_count"] += 1
                    metrics["total_sold"] += value

                # Update last activity
                if (
                    metrics["last_activity"] is None
                    or transfer_date > metrics["last_activity"]
                ):
                    metrics["last_activity"] = transfer_date

            except (ValueError, TypeError) as e:
                continue

        # Calculate first acquisition date
        if acquisitions:
            metrics["first_acquisition"] = min(acquisitions, key=lambda x: x["date"])[
                "date"
            ]

            # Calculate holding period from first acquisition to now
            if metrics["first_acquisition"]:
                metrics["holding_period_days"] = (
                    datetime.now() - metrics["first_acquisition"]
                ).days

        metrics["current_balance"] = max(0, current_balance)

        return metrics

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

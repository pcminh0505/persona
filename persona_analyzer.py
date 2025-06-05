"""
Persona Analyzer for Base Chain Wallets

This module analyzes wallet addresses on Base chain and evaluates them against
predefined persona metrics to build user behavior profiles.
Uses Zerion API for accurate portfolio data and Etherscan for transaction history.
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter
from portfolio_analyzer import PortfolioAnalyzer


@dataclass
class PersonaMetric:
    """Represents a single persona metric with evaluation criteria."""

    name: str
    description: str
    threshold_value: Any
    comparison_operator: str  # 'gt', 'lt', 'gte', 'lte', 'eq', 'between'
    data_source: str  # 'base_chain', 'zerion', 'calculated'

    def evaluate(self, value: Any) -> bool:
        """Evaluate if the given value meets this metric's criteria."""
        if self.comparison_operator == "gt":
            return value > self.threshold_value
        elif self.comparison_operator == "lt":
            return value < self.threshold_value
        elif self.comparison_operator == "gte":
            return value >= self.threshold_value
        elif self.comparison_operator == "lte":
            return value <= self.threshold_value
        elif self.comparison_operator == "eq":
            return value == self.threshold_value
        elif self.comparison_operator == "between":
            if (
                isinstance(self.threshold_value, tuple)
                and len(self.threshold_value) == 2
            ):
                min_val, max_val = self.threshold_value
                return min_val < value < max_val
            return False
        return False


class PersonaAnalyzer:
    """Analyzes wallet addresses against persona metrics."""

    def __init__(self, etherscan_api_key: str = None, zerion_api_key: str = None):
        """Initialize the persona analyzer with Base chain configuration and optional Zerion integration."""
        # Use EtherscanAdapter with Base chain ID (8453)
        self.base_adapter = EtherscanAdapter(api_key=etherscan_api_key, chain_id=8453)

        # Initialize Zerion adapter if API key is provided
        self.zerion_adapter = (
            ZerionAdapter(api_key=zerion_api_key) if zerion_api_key else None
        )

        # Initialize portfolio analyzer with both adapters
        self.portfolio_analyzer = PortfolioAnalyzer(
            self.base_adapter, self.zerion_adapter
        )

        # Define persona metrics based on the provided criteria
        self.metrics = self._define_metrics()

    def _define_metrics(self) -> List[PersonaMetric]:
        """Define the persona metrics for evaluation."""
        return [
            # Portfolio concentration metrics
            PersonaMetric(
                "token_holding_60_percent",
                "Token holding > 60% portfolio value",
                0.60,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "token_holding_50_percent",
                "Token holding > 50% portfolio value",
                0.50,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "token_holding_70_percent",
                "Token holding > 70% portfolio value",
                0.70,
                "gt",
                "calculated",
            ),
            # Holding period metrics
            PersonaMetric(
                "holding_period_12_months",
                "Holding period > 12 months",
                365,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "longest_holding_3_months",
                "Longest holding token > 3 months",
                90,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "holding_period_short",
                "Holding period < 3 months",
                90,
                "lt",
                "calculated",
            ),
            # Portfolio value metrics
            PersonaMetric(
                "top_asset_under_5k",
                "Top asset value < $5,000",
                5000,
                "lt",
                "calculated",
            ),
            PersonaMetric(
                "top_asset_2k_to_5k",
                "Top asset value $2,000 < x < $5,000",
                (2000, 5000),
                "between",
                "calculated",
            ),
            PersonaMetric(
                "total_portfolio_under_5k",
                "Total portfolio value < $5,000",
                5000,
                "lt",
                "calculated",
            ),
            # Wallet age metrics
            PersonaMetric(
                "wallet_created_before_2020",
                "Wallet created < 2020",
                datetime(2020, 1, 1),
                "lt",
                "calculated",
            ),
            PersonaMetric(
                "wallet_created_after_2023",
                "Wallet created > 2023",
                datetime(2023, 1, 1),
                "gt",
                "calculated",
            ),
            # Asset type metrics
            PersonaMetric("holding_eth", "Holding ETH", 0, "gt", "base_chain"),
            PersonaMetric(
                "top_asset_is_token_not_eth",
                "Top asset is token, but not ETH",
                True,
                "eq",
                "calculated",
            ),
            PersonaMetric(
                "top_value_is_nft", "Top value is NFT", True, "eq", "calculated"
            ),
            # Activity metrics
            PersonaMetric(
                "active_120_days",
                "Active for over 120 days for the last 12 months",
                120,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "active_180_days",
                "Active for over 180 days within 12 months",
                180,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "active_30_days",
                "Active for over 30 days for the last 12 months",
                30,
                "gt",
                "calculated",
            ),
            # Transaction metrics
            PersonaMetric(
                "over_100_swaps",
                "Over 100 swap transactions within 12 months",
                100,
                "gt",
                "calculated",
            ),
            PersonaMetric(
                "nft_marketplace_interaction",
                "Interacted with NFT marketplace",
                True,
                "eq",
                "calculated",
            ),
            PersonaMetric(
                "total_transactions_under_50",
                "Total onchain transactions < 50",
                50,
                "lt",
                "base_chain",
            ),
        ]

    async def analyze_wallet(self, address: str) -> Dict[str, Any]:
        """Analyze a wallet address against all persona metrics."""
        print(f"Analyzing wallet on Base chain: {address}")
        data_source = "Zerion + Etherscan" if self.zerion_adapter else "Etherscan"
        print(f"Data sources: {data_source}")

        # Gather all necessary data including detailed portfolio analysis
        wallet_data = await self._gather_wallet_data(address)

        # Get comprehensive portfolio analysis using context manager
        async with self.portfolio_analyzer as analyzer:
            portfolio = await analyzer.analyze_portfolio(address)
            activity_data = await analyzer.calculate_activity_score(address)
            swap_data = await analyzer.analyze_swap_activity(address)

        # Combine all data
        wallet_data.update(
            {
                "portfolio": portfolio,
                "activity": activity_data,
                "swap_activity": swap_data,
            }
        )

        # Evaluate each metric
        results = {}
        for metric in self.metrics:
            try:
                value = self._calculate_metric_value(metric, wallet_data)
                passed = metric.evaluate(value)
                results[metric.name] = {
                    "description": metric.description,
                    "value": value,
                    "threshold": metric.threshold_value,
                    "passed": passed,
                }
            except Exception as e:
                results[metric.name] = {
                    "description": metric.description,
                    "value": None,
                    "threshold": metric.threshold_value,
                    "passed": False,
                    "error": str(e),
                }

        # Calculate persona score
        total_metrics = len(self.metrics)
        passed_metrics = sum(1 for r in results.values() if r.get("passed", False))
        persona_score = (passed_metrics / total_metrics) * 100

        return {
            "address": address,
            "chain": "Base (Chain ID: 8453)",
            "data_sources": data_source,
            "persona_score": persona_score,
            "metrics_passed": passed_metrics,
            "total_metrics": total_metrics,
            "detailed_results": results,
            "portfolio_summary": {
                "total_value_usd": portfolio.total_value_usd,
                "eth_balance": portfolio.eth_balance,
                "token_count": len(portfolio.token_holdings),
                "nft_count": len(portfolio.nft_holdings),
                "top_asset": portfolio.top_asset_by_value,
                "concentration_ratio": portfolio.token_concentration_ratio,
            },
            "activity_summary": {
                "active_days_365": activity_data["active_days"],
                "total_transactions": activity_data["total_transactions"],
                "swap_count": swap_data["swap_count"],
                "unique_tokens_traded": swap_data["unique_tokens"],
            },
            "analysis_timestamp": datetime.now().isoformat(),
        }

    async def _gather_wallet_data(self, address: str) -> Dict[str, Any]:
        """Gather all necessary data for a wallet address."""
        data = {
            "address": address,
            "balance": None,
            "transactions": [],
            "token_transfers": [],
            "nft_transfers": [],
            "first_transaction_date": None,
            "last_transaction_date": None,
        }

        try:
            # Get ETH balance
            balance_response = self.base_adapter.get_ether_balance(address)
            if balance_response and self.base_adapter.validate_response(
                balance_response
            ):
                data["balance"] = int(balance_response.get("result", "0"))

            # Get transactions (last 12 months worth)
            twelve_months_ago = datetime.now() - timedelta(days=365)

            # Get normal transactions
            tx_response = self.base_adapter.get_normal_transactions(
                address, page=1, offset=10000
            )
            if tx_response and self.base_adapter.validate_response(tx_response):
                data["transactions"] = tx_response.get("result", [])

            # Get token transfers
            token_response = self.base_adapter.get_erc20_token_transfers(
                address, page=1, offset=10000
            )
            if token_response and self.base_adapter.validate_response(token_response):
                data["token_transfers"] = token_response.get("result", [])

            # Get NFT transfers
            nft_response = self.base_adapter.get_erc721_token_transfers(
                address, page=1, offset=10000
            )
            if nft_response and self.base_adapter.validate_response(nft_response):
                data["nft_transfers"] = nft_response.get("result", [])

            # Calculate first and last transaction dates
            all_transactions = (
                data["transactions"] + data["token_transfers"] + data["nft_transfers"]
            )
            if all_transactions:
                timestamps = [
                    int(tx.get("timeStamp", 0))
                    for tx in all_transactions
                    if tx.get("timeStamp")
                ]
                if timestamps:
                    data["first_transaction_date"] = datetime.fromtimestamp(
                        min(timestamps)
                    )
                    data["last_transaction_date"] = datetime.fromtimestamp(
                        max(timestamps)
                    )

        except Exception as e:
            print(f"Error gathering wallet data: {e}")

        return data

    def _calculate_metric_value(
        self, metric: PersonaMetric, wallet_data: Dict[str, Any]
    ) -> Any:
        """Calculate the value for a specific metric based on wallet data."""
        portfolio = wallet_data.get("portfolio")
        activity = wallet_data.get("activity", {})
        swap_activity = wallet_data.get("swap_activity", {})

        if metric.name == "holding_eth":
            return portfolio.eth_balance if portfolio else 0.0

        elif metric.name == "total_transactions_under_50":
            return activity.get("total_transactions", 0)

        elif (
            metric.name == "wallet_created_before_2020"
            or metric.name == "wallet_created_after_2023"
        ):
            first_tx_date = wallet_data.get("first_transaction_date")
            return first_tx_date if first_tx_date else datetime.now()

        # Portfolio concentration metrics
        elif metric.name in [
            "token_holding_60_percent",
            "token_holding_50_percent",
            "token_holding_70_percent",
        ]:
            return portfolio.token_concentration_ratio if portfolio else 0.0

        # Portfolio value metrics
        elif metric.name == "total_portfolio_under_5k":
            return portfolio.total_value_usd if portfolio else 0.0

        elif metric.name == "top_asset_under_5k":
            if portfolio:
                _, top_value = portfolio.top_asset_by_value
                return top_value
            return 0.0

        elif metric.name == "top_asset_2k_to_5k":
            if portfolio:
                _, top_value = portfolio.top_asset_by_value
                return top_value
            return 0.0

        # Asset type metrics
        elif metric.name == "top_asset_is_token_not_eth":
            return portfolio.is_top_asset_token_not_eth if portfolio else False

        elif metric.name == "top_value_is_nft":
            return portfolio.is_top_asset_nft if portfolio else False

        # Holding period metrics
        elif metric.name == "longest_holding_3_months":
            return portfolio.longest_holding_period if portfolio else 0

        elif metric.name == "holding_period_12_months":
            if portfolio and portfolio.token_holdings:
                max_holding = max(
                    holding.holding_period_days for holding in portfolio.token_holdings
                )
                return max_holding
            return 0

        elif metric.name == "holding_period_short":
            if portfolio and portfolio.token_holdings:
                avg_holding = sum(
                    holding.holding_period_days for holding in portfolio.token_holdings
                ) / len(portfolio.token_holdings)
                return avg_holding
            return 0

        # Activity metrics
        elif "active_" in metric.name and "days" in metric.name:
            return activity.get("active_days", 0)

        elif metric.name == "over_100_swaps":
            return swap_activity.get("swap_count", 0)

        elif metric.name == "nft_marketplace_interaction":
            return len(portfolio.nft_holdings) > 0 if portfolio else False

        else:
            return 0  # Default fallback


# Example usage
async def main():
    """Example usage of the PersonaAnalyzer."""
    # Initialize analyzer with both API keys
    etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
    zerion_api_key = os.getenv("ZERION_API_KEY")

    if not etherscan_api_key:
        print("Please set ETHERSCAN_API_KEY environment variable")
        print("This will be used with Base chain (chainId 8453)")
        return

    if zerion_api_key:
        print("✅ Zerion API key found - will use Zerion for portfolio data")
    else:
        print(
            "⚠️  No Zerion API key found - will fallback to Etherscan for portfolio data"
        )
        print(
            "Set ZERION_API_KEY environment variable for more accurate portfolio data"
        )

    analyzer = PersonaAnalyzer(etherscan_api_key, zerion_api_key)

    # Example wallet address on Base chain
    test_address = "0x742587695473b0fD5e4D8019Ab9E3ba2c9dB8B8B"

    # Analyze the wallet
    results = await analyzer.analyze_wallet(test_address)

    # Print results
    print(f"\n=== Persona Analysis Results ===")
    print(f"Address: {results['address']}")
    print(f"Chain: {results['chain']}")
    print(f"Data Sources: {results['data_sources']}")
    print(f"Persona Score: {results['persona_score']:.1f}%")
    print(f"Metrics Passed: {results['metrics_passed']}/{results['total_metrics']}")
    print(f"\n=== Detailed Results ===")

    for metric_name, result in results["detailed_results"].items():
        status = "✅" if result["passed"] else "❌"
        print(
            f"{status} {result['description']}: {result['value']} (threshold: {result['threshold']})"
        )


if __name__ == "__main__":
    asyncio.run(main())

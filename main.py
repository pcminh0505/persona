import os
import asyncio
from portfolio_analyzer import PortfolioAnalyzer


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

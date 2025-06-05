#!/usr/bin/env python3
"""Test script for Zerion portfolio parsing."""

import asyncio
import os
from portfolio_analyzer import PortfolioAnalyzer
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter


async def test_zerion_parsing():
    """Test if the updated Zerion parsing works correctly."""
    print("🧪 Testing Zerion Portfolio Parsing...")

    # Check for API keys
    etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
    zerion_api_key = os.getenv("ZERION_API_KEY")

    if not etherscan_api_key:
        print("❌ Missing ETHERSCAN_API_KEY")
        return

    if not zerion_api_key:
        print("❌ Missing ZERION_API_KEY")
        return

    try:
        etherscan_adapter = EtherscanAdapter(api_key=etherscan_api_key, chain_id=8453)
        zerion_adapter = ZerionAdapter(api_key=zerion_api_key)

        async with PortfolioAnalyzer(etherscan_adapter, zerion_adapter) as analyzer:
            # Test with the address from the JSON file
            test_address = "0x6c34c667632dc1aaf04f362516e6f44d006a58fa"
            print(f"📊 Analyzing: {test_address}")

            portfolio = await analyzer.analyze_portfolio(test_address)

            print(f"\n✅ RESULTS:")
            print(f"   Total Portfolio Value: ${portfolio.total_value_usd:.2f}")
            print(
                f"   ETH Balance: {portfolio.eth_balance:.4f} ETH (${portfolio.eth_value_usd:.2f})"
            )
            print(f"   Token Holdings: {len(portfolio.token_holdings)}")
            print(f"   NFT Holdings: {len(portfolio.nft_holdings)}")

            if portfolio.token_holdings:
                print(f"\n🪙 TOP TOKEN HOLDINGS:")
                for i, token in enumerate(portfolio.token_holdings[:5], 1):
                    print(
                        f"   {i}. {token.symbol}: {token.balance:.4f} @ ${token.price_usd:.4f} = ${token.value_usd:.2f}"
                    )
            else:
                print("\n⚠️  No token holdings found")

            if portfolio.total_value_usd > 0:
                print(
                    f"\n🎉 SUCCESS: Portfolio value is ${portfolio.total_value_usd:.2f} (non-zero!)"
                )
            else:
                print(f"\n❌ FAILED: Portfolio value is still $0.00")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_zerion_parsing())

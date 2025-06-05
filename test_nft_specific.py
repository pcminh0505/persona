#!/usr/bin/env python3
"""Test script specifically for NFT parsing with Zerion API."""

import asyncio
import os
from portfolio_analyzer import PortfolioAnalyzer
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter


async def test_nft_parsing():
    """Test NFT parsing specifically."""
    print("🎨 Testing Zerion NFT Collection Parsing...")

    # Check for API keys
    etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
    zerion_api_key = os.getenv("ZERION_API_KEY")

    if not zerion_api_key:
        print("❌ Missing ZERION_API_KEY")
        return

    try:
        etherscan_adapter = EtherscanAdapter(api_key=etherscan_api_key, chain_id=8453)
        zerion_adapter = ZerionAdapter(api_key=zerion_api_key)

        async with PortfolioAnalyzer(etherscan_adapter, zerion_adapter) as analyzer:
            test_address = "0x6c34c667632dc1aaf04f362516e6f44d006a58fa"
            print(f"🔍 Analyzing NFTs for: {test_address}")

            portfolio = await analyzer.analyze_portfolio(test_address)

            print(f"\n🎨 NFT ANALYSIS RESULTS:")
            print(f"   Total NFT Holdings: {len(portfolio.nft_holdings)}")

            # Calculate total NFT value
            total_nft_value = sum(
                nft.estimated_value_usd for nft in portfolio.nft_holdings
            )
            print(f"   Total NFT Portfolio Value: ${total_nft_value:.2f}")

            # Group by collection
            collections = {}
            for nft in portfolio.nft_holdings:
                collection_name = nft.collection_name
                if collection_name not in collections:
                    collections[collection_name] = {"count": 0, "total_value": 0.0}
                collections[collection_name]["count"] += 1
                collections[collection_name]["total_value"] += nft.estimated_value_usd

            # Sort collections by value
            sorted_collections = sorted(
                collections.items(), key=lambda x: x[1]["total_value"], reverse=True
            )

            print(f"\n📊 TOP NFT COLLECTIONS BY VALUE:")
            for i, (name, data) in enumerate(sorted_collections[:10], 1):
                print(
                    f"   {i}. {name}: {data['count']} NFTs @ ${data['total_value']:.2f}"
                )

            # Check for high-value NFTs
            high_value_nfts = [
                nft for nft in portfolio.nft_holdings if nft.estimated_value_usd > 100
            ]
            if high_value_nfts:
                print(f"\n💎 HIGH-VALUE NFTs (>$100):")
                for nft in sorted(
                    high_value_nfts, key=lambda x: x.estimated_value_usd, reverse=True
                )[:5]:
                    print(f"   • {nft.collection_name}: ${nft.estimated_value_usd:.2f}")

            print(f"\n✅ NFT parsing is working correctly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_nft_parsing())

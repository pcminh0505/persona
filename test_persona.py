"""
Test script for the Persona Analyzer

This script demonstrates how to use the persona analyzer to evaluate
a Base chain wallet against various behavioral metrics.
Supports both Etherscan-only and Zerion+Etherscan data sources.
"""

import os
import asyncio
from persona_analyzer import PersonaAnalyzer


async def test_persona_analysis():
    """Test the persona analyzer with a sample address."""

    # Check for API keys
    etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
    zerion_api_key = os.getenv("ZERION_API_KEY")

    if not etherscan_api_key:
        print("❌ Please set ETHERSCAN_API_KEY environment variable")
        print("This will be used for Base chain analysis (chainId 8453)")
        print("You can get a free API key from: https://etherscan.io/apis")
        return

    # Initialize analyzer
    print("🚀 Initializing Persona Analyzer for Base Chain...")

    if zerion_api_key:
        print(
            "✅ Using Zerion API for accurate portfolio data + Etherscan for transactions"
        )
    else:
        print(
            "⚠️  Using Etherscan only - consider adding ZERION_API_KEY for better portfolio data"
        )
        print("You can get a Zerion API key from: https://developers.zerion.io/")

    analyzer = PersonaAnalyzer(etherscan_api_key, zerion_api_key)

    # Test with a well-known Base address (Coinbase's official address)
    # This is just an example - replace with any Base chain address
    test_address = "0x6c34c667632dc1aaf04f362516e6f44d006a58fa"

    print(f"\n📊 Analyzing wallet: {test_address}")
    print("This may take a moment to fetch all the data...\n")

    try:
        # Run the analysis
        results = await analyzer.analyze_wallet(test_address)

        # Display results
        print("=" * 60)
        print("🎯 PERSONA ANALYSIS RESULTS")
        print("=" * 60)

        print(f"📍 Address: {results['address']}")
        print(f"⛓️  Chain: {results['chain']}")
        print(f"📡 Data Sources: {results['data_sources']}")
        print(f"📈 Persona Score: {results['persona_score']:.1f}%")
        print(
            f"✅ Metrics Passed: {results['metrics_passed']}/{results['total_metrics']}"
        )

        # Portfolio Summary
        portfolio = results.get("portfolio_summary", {})
        print(f"\n💰 PORTFOLIO SUMMARY")
        print(f"   Total Value: ${portfolio.get('total_value_usd', 0):.2f}")
        print(f"   ETH Balance: {portfolio.get('eth_balance', 0):.4f} ETH")
        print(f"   Token Holdings: {portfolio.get('token_count', 0)}")
        print(f"   NFT Holdings: {portfolio.get('nft_count', 0)}")

        top_asset = portfolio.get("top_asset", ("None", 0))
        print(f"   Top Asset: {top_asset[0]} (${top_asset[1]:.2f})")
        print(f"   Concentration Ratio: {portfolio.get('concentration_ratio', 0):.1%}")

        # Activity Summary
        activity = results.get("activity_summary", {})
        print(f"\n📊 ACTIVITY SUMMARY (Last 365 Days)")
        print(f"   Active Days: {activity.get('active_days_365', 0)}")
        print(f"   Total Transactions: {activity.get('total_transactions', 0)}")
        print(f"   Swap Count: {activity.get('swap_count', 0)}")
        print(f"   Unique Tokens Traded: {activity.get('unique_tokens_traded', 0)}")

        # Detailed Metrics
        print(f"\n📋 DETAILED METRICS")
        print("-" * 60)

        passed_metrics = []
        failed_metrics = []

        for metric_name, result in results["detailed_results"].items():
            status = "✅" if result["passed"] else "❌"
            description = result["description"]
            value = result["value"]
            threshold = result["threshold"]

            line = f"{status} {description}"
            if result.get("error"):
                line += f" (Error: {result['error']})"
            else:
                line += f": {value} (threshold: {threshold})"

            if result["passed"]:
                passed_metrics.append(line)
            else:
                failed_metrics.append(line)

        # Show passed metrics first
        if passed_metrics:
            print("\n✅ PASSED METRICS:")
            for metric in passed_metrics:
                print(f"   {metric}")

        if failed_metrics:
            print("\n❌ FAILED METRICS:")
            for metric in failed_metrics:
                print(f"   {metric}")

        # Persona Classification
        print(f"\n🎭 PERSONA CLASSIFICATION")
        print("-" * 30)

        score = results["persona_score"]
        if score >= 80:
            persona_type = "🏆 Power User"
            description = "Highly active DeFi user with diverse portfolio"
        elif score >= 60:
            persona_type = "📈 Active Trader"
            description = "Regular DeFi participant with moderate activity"
        elif score >= 40:
            persona_type = "🌱 Growing User"
            description = "Developing DeFi user with some activity"
        elif score >= 20:
            persona_type = "👶 New User"
            description = "Beginning DeFi journey with limited activity"
        else:
            persona_type = "😴 Inactive User"
            description = "Minimal or no recent DeFi activity"

        print(f"Type: {persona_type}")
        print(f"Description: {description}")

        # Data source recommendation
        if not zerion_api_key:
            print(
                f"\n💡 TIP: Add ZERION_API_KEY for more accurate token holdings and NFT data"
            )
            print(
                f"Current analysis used Etherscan only - Zerion provides better portfolio insights"
            )

        print(f"\n⏰ Analysis completed at: {results['analysis_timestamp']}")

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print("This might be due to:")
        print("- Invalid API key")
        print("- Network connectivity issues")
        print("- Invalid wallet address")
        print("- API rate limits")
        print("- Base chain API endpoint issues")


if __name__ == "__main__":
    print("🎯 Base Chain Persona Analyzer Test")
    print("=" * 40)

    asyncio.run(test_persona_analysis())

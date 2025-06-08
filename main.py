#!/usr/bin/env python3
"""
Test script for detailed persona metric calculations.

This script demonstrates how the enhanced persona classification system
shows detailed calculations for each trait and metric.
"""

import os
import asyncio
from dotenv import load_dotenv
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter
from portfolio_analyzer import PortfolioAnalyzer

# Load environment variables
load_dotenv()


async def test_detailed_metrics():
    """Test the detailed metrics functionality."""

    # Get API keys
    etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
    zerion_api_key = os.getenv("ZERION_API_KEY")

    if not etherscan_api_key:
        print("❌ ETHERSCAN_API_KEY environment variable is required")
        print("Please set your Etherscan API key in a .env file")
        return

    print("🚀 Testing Detailed Persona Metrics")
    print("=" * 60)

    # Initialize adapters
    base_adapter = EtherscanAdapter(api_key=etherscan_api_key, chain_id=8453)
    zerion_adapter = ZerionAdapter(api_key=zerion_api_key) if zerion_api_key else None

    # Test wallet addresses (replace with real addresses for testing)
    test_addresses = [
        "0x6c34c667632dc1aaf04f362516e6f44d006a58fa",  # Replace with actual Base wallet
        "0x55Fce96D44c96Ef27f296aEB37aD0eb360505015",
    ]

    async with PortfolioAnalyzer(base_adapter, zerion_adapter) as analyzer:

        for address in test_addresses:
            print(f"\n🎯 Testing wallet: {address}")
            print("=" * 60)

            try:
                # Analyze with detailed metrics
                result = await analyzer.analyze_wallet(
                    address, show_detailed_metrics=True
                )

                if result.get("error"):
                    print(f"❌ Error: {result['error']}")
                    continue

                # Additional detailed breakdown
                persona_data = result.get("persona", {})
                detailed_metrics = persona_data.get("detailed_metrics", [])

                if detailed_metrics:
                    print(f"\n🔬 METRIC BREAKDOWN SUMMARY")
                    print("-" * 40)

                    # Group by persona type and show pass/fail counts
                    persona_scores = {}
                    for metric in detailed_metrics:
                        persona_type = metric["persona_type"]
                        if persona_type not in persona_scores:
                            persona_scores[persona_type] = {"passed": 0, "total": 0}

                        persona_scores[persona_type]["total"] += 1
                        if metric["passes"]:
                            persona_scores[persona_type]["passed"] += 1

                    for persona_type, scores in persona_scores.items():
                        percentage = (scores["passed"] / scores["total"]) * 100
                        status = (
                            "🟢"
                            if percentage >= 80
                            else "🟡" if percentage >= 50 else "🔴"
                        )
                        print(
                            f"{status} {persona_type}: {scores['passed']}/{scores['total']} ({percentage:.1f}%)"
                        )

                    persona = result["persona"]["classification"]
                    print(f"\n🎯 Result: Classified as '{persona}'")

                    # Show scoring details if available
                    if hasattr(analyzer.persona_classifier, "_last_persona_scores"):
                        scores = analyzer.persona_classifier._last_persona_scores
                        best_score = analyzer.persona_classifier._last_best_score

                        print(f"\n📊 Detailed Scoring Breakdown:")
                        print("-" * 40)

                        # Sort personas by score
                        sorted_personas = sorted(
                            scores.items(),
                            key=lambda x: (
                                x[1]["total_score"] / x[1]["max_possible"]
                                if x[1]["max_possible"] > 0
                                else 0
                            ),
                            reverse=True,
                        )

                        for rank, (persona_type, score_data) in enumerate(
                            sorted_personas, 1
                        ):
                            if score_data["max_possible"] > 0:
                                percentage = (
                                    score_data["total_score"]
                                    / score_data["max_possible"]
                                ) * 100
                                status = "👑 WINNER" if rank == 1 else f"#{rank}"
                                print(
                                    f"{status} {persona_type}: "
                                    f"{score_data['total_score']}/{score_data['max_possible']} points "
                                    f"({score_data['passed_metrics']}/{score_data['total_metrics']} criteria) "
                                    f"= {percentage:.1f}%"
                                )

                        print(f"\n✨ Overall confidence: {best_score * 100:.1f}%")

                print(f"\n✅ Analysis complete for {address}")

            except Exception as e:
                print(f"❌ Error analyzing {address}: {e}")
                continue

        print(f"\n🎉 Testing complete!")


if __name__ == "__main__":
    asyncio.run(test_detailed_metrics())

"""
Modular Portfolio Analyzer for Base Chain Wallets

This is the main entry point for portfolio analysis using a modular architecture.
The analyzer coordinates between different services to provide comprehensive
wallet analysis and persona classification with detailed metric calculations.
"""

import os
import asyncio
from adapters.etherscan import EtherscanAdapter
from adapters.zerion import ZerionAdapter
from services.portfolio_service import PortfolioService
from services.activity_service import ActivityService
from persona.persona_classifier import PersonaClassifier


class PortfolioAnalyzer:
    """Main portfolio analyzer coordinating all services."""

    def __init__(self, etherscan_adapter, zerion_adapter=None):
        """Initialize with adapters."""
        self.etherscan_adapter = etherscan_adapter
        self.zerion_adapter = zerion_adapter

        # Initialize services
        self.portfolio_service = PortfolioService(etherscan_adapter, zerion_adapter)
        self.activity_service = ActivityService(etherscan_adapter)
        self.persona_classifier = PersonaClassifier(
            self.portfolio_service, self.activity_service
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.portfolio_service.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.portfolio_service.__aexit__(exc_type, exc_val, exc_tb)

    async def analyze_wallet(
        self, address: str, show_detailed_metrics: bool = True
    ) -> dict:
        """
        Perform comprehensive wallet analysis including portfolio and persona classification.

        Args:
            address: Wallet address to analyze
            show_detailed_metrics: Whether to display detailed metric calculations

        Returns:
            Dictionary containing portfolio data, activity metrics, and persona classification
        """
        try:
            print(f"\n🔍 Analyzing wallet: {address}")
            print("=" * 60)

            # Get portfolio analysis
            print("📊 Fetching portfolio data...")
            portfolio = await self.portfolio_service.analyze_portfolio(address)

            # Get activity metrics
            print("⚡ Calculating activity metrics...")
            activity = await self.activity_service.calculate_activity_score(address)
            swap_activity = await self.activity_service.analyze_swap_activity(address)
            wallet_creation_date = await self.activity_service.get_wallet_creation_date(
                address
            )

            # Classify persona with detailed metrics (pass the already-computed portfolio)
            print("🎯 Classifying persona with detailed calculations...")
            persona, persona_details, detailed_metrics = (
                await self.persona_classifier.classify_persona_with_details(
                    address, portfolio
                )
            )

            # Display detailed metrics if requested
            if show_detailed_metrics:
                print("\n" + "=" * 60)
                print("🔬 DETAILED METRIC CALCULATIONS")
                print("=" * 60)

                # Show metrics for the classified persona first
                if persona != "Unclassified" and persona != "Error":
                    print(f"\n🎯 CLASSIFIED AS: {persona.upper()}")
                    detailed_output = self.persona_classifier.format_detailed_metrics(
                        detailed_metrics, target_persona=persona
                    )
                    print(detailed_output)

                # Show all persona metrics for comparison
                print(f"\n📋 ALL PERSONA METRICS COMPARISON")
                print("-" * 40)
                all_metrics_output = self.persona_classifier.format_detailed_metrics(
                    detailed_metrics
                )
                print(all_metrics_output)

            # Display traditional persona analysis
            print("\n" + "=" * 60)
            print("📈 PERSONA ANALYSIS SUMMARY")
            print("=" * 60)
            formatted_analysis = self.persona_classifier.format_persona_analysis(
                persona, persona_details
            )
            print(formatted_analysis)

            return {
                "address": address,
                "portfolio": portfolio,
                "activity": {
                    "active_days": activity["active_days"],
                    "total_transactions": activity["total_transactions"],
                    "swap_count": swap_activity["swap_count"],
                    "unique_tokens": swap_activity["unique_tokens"],
                    "wallet_creation_date": wallet_creation_date,
                },
                "persona": {
                    "classification": persona,
                    "details": persona_details,
                    "detailed_metrics": detailed_metrics,
                    "formatted_analysis": formatted_analysis,
                },
            }

        except Exception as e:
            print(f"❌ Error analyzing wallet {address}: {e}")
            return {
                "address": address,
                "error": str(e),
                "portfolio": None,
                "activity": None,
                "persona": None,
            }

    async def analyze_multiple_wallets(
        self, addresses: list, show_detailed_metrics: bool = False
    ) -> dict:
        """
        Analyze multiple wallets and return aggregated results.

        Args:
            addresses: List of wallet addresses to analyze
            show_detailed_metrics: Whether to show detailed metrics for each wallet

        Returns:
            Dictionary with individual results and summary statistics
        """
        results = {}
        persona_counts = {}

        print(f"\n🚀 Starting analysis of {len(addresses)} wallets...")
        print("=" * 60)

        for i, address in enumerate(addresses, 1):
            print(f"\n[{i}/{len(addresses)}] Analyzing wallet: {address}")
            result = await self.analyze_wallet(address, show_detailed_metrics)
            results[address] = result

            # Count personas
            if result.get("persona") and result["persona"].get("classification"):
                persona = result["persona"]["classification"]
                persona_counts[persona] = persona_counts.get(persona, 0) + 1

        # Display summary
        print("\n" + "=" * 60)
        print("📊 BATCH ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total wallets analyzed: {len(addresses)}")
        print(
            f"Successful analyses: {len([r for r in results.values() if not r.get('error')])}"
        )
        print(
            f"Failed analyses: {len([r for r in results.values() if r.get('error')])}"
        )

        if persona_counts:
            print(f"\n🎯 Persona Distribution:")
            for persona, count in sorted(
                persona_counts.items(), key=lambda x: x[1], reverse=True
            ):
                percentage = (count / len(addresses)) * 100
                print(f"  {persona}: {count} wallets ({percentage:.1f}%)")

            most_common = max(persona_counts.items(), key=lambda x: x[1])[0]
            print(f"\n🏆 Most common persona: {most_common}")

        return {
            "individual_results": results,
            "summary": {
                "total_wallets": len(addresses),
                "successful_analyses": len(
                    [r for r in results.values() if not r.get("error")]
                ),
                "persona_distribution": persona_counts,
                "most_common_persona": (
                    max(persona_counts.items(), key=lambda x: x[1])[0]
                    if persona_counts
                    else "None"
                ),
            },
        }

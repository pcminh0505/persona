"""
Persona classification system for wallet analysis.

This module handles the classification of wallet addresses into different persona types
based on their on-chain behavior, portfolio composition, and activity patterns.
"""

from datetime import datetime
from typing import Dict, Any, Tuple, List
import json
from services.activity_service import ActivityService
from services.portfolio_service import PortfolioService


class PersonaClassifier:
    """Classifier for determining wallet personas based on on-chain behavior."""

    def __init__(
        self, portfolio_service: PortfolioService, activity_service: ActivityService
    ):
        """Initialize with required services."""
        self.portfolio_service = portfolio_service
        self.activity_service = activity_service

    async def classify_persona_with_details(
        self, address: str, portfolio=None
    ) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
        """
        Classify persona with detailed metric calculations.
        Returns (persona_name, criteria_details, detailed_metrics)

        Args:
            address: Wallet address to analyze
            portfolio: Optional pre-computed portfolio data to avoid duplicate analysis
        """
        try:
            # Get portfolio data (use provided one or fetch it)
            if portfolio is None:
                portfolio = await self.portfolio_service.analyze_portfolio(address)

            # Get activity metrics
            activity = await self.activity_service.calculate_activity_score(address)
            swap_activity = await self.activity_service.analyze_swap_activity(address)

            # Get wallet creation date
            wallet_creation_date = await self.activity_service.get_wallet_creation_date(
                address
            )

            # Calculate derived metrics
            wallet_age_years = 0
            if wallet_creation_date:
                wallet_age_years = (datetime.now() - wallet_creation_date).days / 365.25

            top_asset, top_value = portfolio.top_asset_by_value

            # Prepare criteria details
            criteria = {
                "portfolio": portfolio,
                "wallet_creation_date": wallet_creation_date,
                "wallet_age_years": wallet_age_years,
                "active_days": activity["active_days"],
                "total_transactions": activity["total_transactions"],
                "swap_count": swap_activity["swap_count"],
                "unique_tokens": swap_activity["unique_tokens"],
                "top_asset": top_asset,
                "top_value": top_value,
                "token_concentration": portfolio.token_concentration_ratio,
                "longest_holding_days": portfolio.longest_holding_period,
                "has_eth": portfolio.eth_balance > 0,
                "is_top_asset_token_not_eth": portfolio.is_top_asset_token_not_eth,
                "total_portfolio_value": portfolio.total_value_usd,
            }

            # Calculate detailed metrics for all persona types
            detailed_metrics = self._calculate_detailed_metrics(criteria)

            # Check personas in priority order
            persona = self._determine_persona(criteria)

            return persona, criteria, detailed_metrics

        except Exception as e:
            print(f"Error classifying persona: {e}")
            return "Error", {}, []

    def _calculate_detailed_metrics(
        self, criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate detailed metrics for all persona types."""
        metrics = []

        # OG (Conservative) Metrics
        og_metrics = self._calculate_og_metrics(criteria)
        metrics.extend(og_metrics)

        # DeFi Chad (Moderate) Metrics
        defi_chad_metrics = self._calculate_defi_chad_metrics(criteria)
        metrics.extend(defi_chad_metrics)

        # Degen (Aggressive) Metrics
        degen_metrics = self._calculate_degen_metrics(criteria)
        metrics.extend(degen_metrics)

        # Virgin CT (Newbie) Metrics
        virgin_ct_metrics = self._calculate_virgin_ct_metrics(criteria)
        metrics.extend(virgin_ct_metrics)

        return metrics

    def _calculate_og_metrics(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate OG (Conservative) persona metrics."""
        metrics = []
        persona_type = "OG (Conservative)"

        # Token concentration > 60%
        token_concentration = criteria.get("token_concentration", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Token Concentration",
                "description": "Token holding > 60% of portfolio value",
                "calculation": f"{token_concentration:.1%} > 60%",
                "actual_value": token_concentration,
                "threshold": 0.6,
                "operator": ">",
                "passes": token_concentration > 0.6,
                "weight": "High",
            }
        )

        # Holding period > 12 months
        longest_holding = criteria.get("longest_holding_days", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Holding Period",
                "description": "Longest holding period > 12 months (365 days)",
                "calculation": f"{longest_holding} days > 365 days",
                "actual_value": longest_holding,
                "threshold": 365,
                "operator": ">",
                "passes": longest_holding > 365,
                "weight": "High",
            }
        )

        # Top asset value < $5,000
        top_value = criteria.get("top_value", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Top Asset Value",
                "description": "Top asset value < $5,000",
                "calculation": f"${top_value:.2f} < $5,000",
                "actual_value": top_value,
                "threshold": 5000,
                "operator": "<",
                "passes": top_value < 5000,
                "weight": "Medium",
            }
        )

        # Wallet created before 2020
        wallet_creation = criteria.get("wallet_creation_date")
        wallet_year = wallet_creation.year if wallet_creation else 9999
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Wallet Age",
                "description": "Wallet created before 2020",
                "calculation": f"Created in {wallet_year} < 2020",
                "actual_value": wallet_year,
                "threshold": 2020,
                "operator": "<",
                "passes": wallet_creation and wallet_year < 2020,
                "weight": "High",
            }
        )

        # Holding ETH
        has_eth = criteria.get("has_eth", False)
        eth_balance = (
            criteria.get("portfolio").eth_balance if criteria.get("portfolio") else 0
        )
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "ETH Holdings",
                "description": "Currently holding ETH",
                "calculation": f"ETH Balance: {eth_balance:.4f} ETH > 0",
                "actual_value": eth_balance,
                "threshold": 0,
                "operator": ">",
                "passes": has_eth,
                "weight": "Medium",
            }
        )

        return metrics

    def _calculate_defi_chad_metrics(
        self, criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate DeFi Chad (Moderate) persona metrics."""
        metrics = []
        persona_type = "DeFi Chad (Moderate)"

        # Longest holding > 3 months
        longest_holding = criteria.get("longest_holding_days", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Holding Period",
                "description": "Longest holding > 3 months (90 days)",
                "calculation": f"{longest_holding} days > 90 days",
                "actual_value": longest_holding,
                "threshold": 90,
                "operator": ">",
                "passes": longest_holding > 90,
                "weight": "High",
            }
        )

        # Token concentration > 50%
        token_concentration = criteria.get("token_concentration", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Token Concentration",
                "description": "Token holding > 50% of portfolio value",
                "calculation": f"{token_concentration:.1%} > 50%",
                "actual_value": token_concentration,
                "threshold": 0.5,
                "operator": ">",
                "passes": token_concentration > 0.5,
                "weight": "High",
            }
        )

        # Active > 120 days
        active_days = criteria.get("active_days", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Activity Level",
                "description": "Active > 120 days in last 12 months",
                "calculation": f"{active_days} days > 120 days",
                "actual_value": active_days,
                "threshold": 120,
                "operator": ">",
                "passes": active_days > 120,
                "weight": "High",
            }
        )

        # Top asset value between $2,000-$5,000
        top_value = criteria.get("top_value", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Top Asset Value Range",
                "description": "Top asset value between $2,000 and $5,000",
                "calculation": f"$2,000 < ${top_value:.2f} < $5,000",
                "actual_value": top_value,
                "threshold": (2000, 5000),
                "operator": "between",
                "passes": 2000 < top_value < 5000,
                "weight": "Medium",
            }
        )

        return metrics

    def _calculate_degen_metrics(
        self, criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate Degen (Aggressive) persona metrics."""
        metrics = []
        persona_type = "Degen (Aggressive)"

        # Active > 180 days
        active_days = criteria.get("active_days", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "High Activity",
                "description": "Active > 180 days in 12 months",
                "calculation": f"{active_days} days > 180 days",
                "actual_value": active_days,
                "threshold": 180,
                "operator": ">",
                "passes": active_days > 180,
                "weight": "High",
            }
        )

        # Swaps > 100
        swap_count = criteria.get("swap_count", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Swap Activity",
                "description": "Over 100 swap transactions in 12 months",
                "calculation": f"{swap_count} swaps > 100 swaps",
                "actual_value": swap_count,
                "threshold": 100,
                "operator": ">",
                "passes": swap_count > 100,
                "weight": "High",
            }
        )

        # Holding period < 3 months
        longest_holding = criteria.get("longest_holding_days", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Short Holding Period",
                "description": "Holding period < 3 months (90 days)",
                "calculation": f"{longest_holding} days < 90 days",
                "actual_value": longest_holding,
                "threshold": 90,
                "operator": "<",
                "passes": longest_holding < 90,
                "weight": "High",
            }
        )

        # Token concentration > 70%
        token_concentration = criteria.get("token_concentration", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "High Token Concentration",
                "description": "Token holding > 70% of portfolio value",
                "calculation": f"{token_concentration:.1%} > 70%",
                "actual_value": token_concentration,
                "threshold": 0.7,
                "operator": ">",
                "passes": token_concentration > 0.7,
                "weight": "Medium",
            }
        )

        # Top asset is token (not ETH)
        is_top_asset_token_not_eth = criteria.get("is_top_asset_token_not_eth", False)
        top_asset = criteria.get("top_asset", "Unknown")
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Non-ETH Top Asset",
                "description": "Top asset is token but not ETH",
                "calculation": f"Top asset '{top_asset}' is not ETH",
                "actual_value": top_asset,
                "threshold": "not ETH",
                "operator": "!=",
                "passes": is_top_asset_token_not_eth,
                "weight": "Medium",
            }
        )

        return metrics

    def _calculate_virgin_ct_metrics(
        self, criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate Virgin CT (Newbie) persona metrics."""
        metrics = []
        persona_type = "Virgin CT (Newbie)"

        # Wallet created after 2023
        wallet_creation = criteria.get("wallet_creation_date")
        wallet_year = wallet_creation.year if wallet_creation else 0
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Recent Wallet",
                "description": "Wallet created after 2023",
                "calculation": f"Created in {wallet_year} > 2023",
                "actual_value": wallet_year,
                "threshold": 2023,
                "operator": ">",
                "passes": wallet_creation and wallet_year > 2023,
                "weight": "High",
            }
        )

        # Active > 30 days
        active_days = criteria.get("active_days", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Moderate Activity",
                "description": "Active > 30 days in last 12 months",
                "calculation": f"{active_days} days > 30 days",
                "actual_value": active_days,
                "threshold": 30,
                "operator": ">",
                "passes": active_days > 30,
                "weight": "Medium",
            }
        )

        # Portfolio value < $5,000
        portfolio_value = criteria.get("total_portfolio_value", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Small Portfolio",
                "description": "Total portfolio value < $5,000",
                "calculation": f"${portfolio_value:.2f} < $5,000",
                "actual_value": portfolio_value,
                "threshold": 5000,
                "operator": "<",
                "passes": portfolio_value < 5000,
                "weight": "High",
            }
        )

        # Total transactions < 50
        total_transactions = criteria.get("total_transactions", 0)
        metrics.append(
            {
                "persona_type": persona_type,
                "metric_name": "Low Transaction Count",
                "description": "Total onchain transactions < 50",
                "calculation": f"{total_transactions} transactions < 50",
                "actual_value": total_transactions,
                "threshold": 50,
                "operator": "<",
                "passes": total_transactions < 50,
                "weight": "Medium",
            }
        )

        return metrics

    def _determine_persona(self, criteria: Dict[str, Any]) -> str:
        """Determine persona based on weighted scoring of all criteria."""
        # Calculate detailed metrics for scoring
        detailed_metrics = self._calculate_detailed_metrics(criteria)

        # Group metrics by persona type and calculate weighted scores
        persona_scores = {}
        weight_values = {"High": 3, "Medium": 2, "Low": 1}

        for metric in detailed_metrics:
            persona_type = metric["persona_type"]
            if persona_type not in persona_scores:
                persona_scores[persona_type] = {
                    "total_score": 0,
                    "max_possible": 0,
                    "passed_metrics": 0,
                    "total_metrics": 0,
                }

            weight_value = weight_values.get(metric["weight"], 1)
            persona_scores[persona_type]["max_possible"] += weight_value
            persona_scores[persona_type]["total_metrics"] += 1

            if metric["passes"]:
                persona_scores[persona_type]["total_score"] += weight_value
                persona_scores[persona_type]["passed_metrics"] += 1

        # Calculate percentage scores and find the best match
        best_persona = None
        best_score = -1

        for persona_type, scores in persona_scores.items():
            if scores["max_possible"] > 0:
                percentage_score = scores["total_score"] / scores["max_possible"]

                # Prefer personas with higher percentage scores
                # In case of ties, prefer the one with more total points
                if percentage_score > best_score or (
                    percentage_score == best_score
                    and scores["total_score"]
                    > persona_scores[best_persona]["total_score"]
                ):
                    best_score = percentage_score
                    best_persona = persona_type

        # Store scoring details for later use in formatting
        self._last_persona_scores = persona_scores
        self._last_best_score = best_score

        return best_persona if best_persona else "Unclassified"

    def _determine_persona_legacy(self, criteria: Dict[str, Any]) -> str:
        """Legacy persona determination logic (kept for reference)."""
        portfolio = criteria.get("portfolio")
        activity = criteria
        wallet_creation_date = criteria.get("wallet_creation_date")

        # 1. OG (Conservative)
        if (
            criteria.get("token_concentration", 0) > 0.6
            and criteria.get("longest_holding_days", 0) > 365
            and criteria.get("top_value", 0) < 5000
            and wallet_creation_date
            and wallet_creation_date.year < 2020
            and criteria.get("has_eth", False)
        ):
            return "OG (Conservative)"

        # 2. DeFi Chad (Moderate)
        if (
            criteria.get("longest_holding_days", 0) > 90
            and criteria.get("token_concentration", 0) > 0.5
            and criteria.get("active_days", 0) > 120
            and 2000 < criteria.get("top_value", 0) < 5000
        ):
            return "DeFi Chad (Moderate)"

        # 3. Degen (Aggressive)
        if (
            criteria.get("active_days", 0) > 180
            and criteria.get("swap_count", 0) > 100
            and criteria.get("longest_holding_days", 0) < 90
            and criteria.get("token_concentration", 0) > 0.7
            and criteria.get("is_top_asset_token_not_eth", False)
        ):
            return "Degen (Aggressive)"

        # 4. Virgin CT (Newbie)
        if (
            wallet_creation_date
            and wallet_creation_date.year > 2023
            and criteria.get("active_days", 0) > 30
            and criteria.get("total_portfolio_value", 0) < 5000
            and criteria.get("total_transactions", 0) < 50
        ):
            return "Virgin CT (Newbie)"

        # Default: Unclassified
        return "Unclassified"

    # Keep the original methods for backward compatibility
    async def classify_persona(
        self, address: str, portfolio=None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Dynamically classify user persona based on comprehensive criteria.
        Returns (persona_name, criteria_details)

        Args:
            address: Wallet address to analyze
            portfolio: Optional pre-computed portfolio data to avoid duplicate analysis
        """
        persona, criteria, _ = await self.classify_persona_with_details(
            address, portfolio
        )
        return persona, criteria

    def format_detailed_metrics(
        self, detailed_metrics: List[Dict[str, Any]], target_persona: str = None
    ) -> str:
        """Format detailed metrics for display."""
        if not detailed_metrics:
            return "❌ No detailed metrics available"

        output = []

        # Group metrics by persona type
        persona_metrics = {}
        for metric in detailed_metrics:
            persona_type = metric["persona_type"]
            if persona_type not in persona_metrics:
                persona_metrics[persona_type] = []
            persona_metrics[persona_type].append(metric)

        # Display metrics for each persona type
        for persona_type, metrics in persona_metrics.items():
            if target_persona and persona_type != target_persona:
                continue

            output.append(f"\n🔍 === {persona_type.upper()} METRICS ===")

            passed_count = sum(1 for m in metrics if m["passes"])
            total_count = len(metrics)

            output.append(f"Overall Score: {passed_count}/{total_count} criteria met")

            for metric in metrics:
                status = "✅" if metric["passes"] else "❌"
                weight_icon = (
                    "🔥"
                    if metric["weight"] == "High"
                    else "⚡" if metric["weight"] == "Medium" else "💡"
                )

                output.append(f"\n{status} {weight_icon} {metric['metric_name']}")
                output.append(f"   Description: {metric['description']}")
                output.append(f"   Calculation: {metric['calculation']}")
                output.append(f"   Result: {'PASS' if metric['passes'] else 'FAIL'}")
                output.append(f"   Weight: {metric['weight']}")

        return "\n".join(output)

    def format_persona_analysis(self, persona: str, criteria: Dict[str, Any]) -> str:
        """Format persona analysis results for display."""
        if persona == "Error":
            return "❌ Error occurred during persona classification"

        portfolio = criteria.get("portfolio")
        if not portfolio:
            return "❌ No portfolio data available"

        output = []

        # Header with confidence score
        confidence_info = ""
        if hasattr(self, "_last_persona_scores") and hasattr(self, "_last_best_score"):
            confidence_percentage = self._last_best_score * 100
            if confidence_percentage >= 80:
                confidence_emoji = "🎯"
                confidence_level = "High"
            elif confidence_percentage >= 60:
                confidence_emoji = "⚡"
                confidence_level = "Medium"
            elif confidence_percentage >= 40:
                confidence_emoji = "🤔"
                confidence_level = "Low"
            else:
                confidence_emoji = "❓"
                confidence_level = "Very Low"

            confidence_info = f" | {confidence_emoji} {confidence_level} Confidence ({confidence_percentage:.1f}%)"

        if persona == "Unclassified":
            output.append(f"❓ PERSONA: UNCLASSIFIED{confidence_info}")
        else:
            output.append(f"🎯 PERSONA: {persona.upper()}{confidence_info}")

        # Add scoring summary if available
        if hasattr(self, "_last_persona_scores"):
            output.append("\n=== Persona Scoring Summary ===")
            sorted_personas = sorted(
                self._last_persona_scores.items(),
                key=lambda x: (
                    x[1]["total_score"] / x[1]["max_possible"]
                    if x[1]["max_possible"] > 0
                    else 0
                ),
                reverse=True,
            )

            for i, (persona_type, scores) in enumerate(sorted_personas, 1):
                if scores["max_possible"] > 0:
                    percentage = (scores["total_score"] / scores["max_possible"]) * 100
                    status = "👑" if i == 1 else f"{i}."
                    output.append(
                        f"{status} {persona_type}: {scores['total_score']}/{scores['max_possible']} points "
                        f"({scores['passed_metrics']}/{scores['total_metrics']} criteria) = {percentage:.1f}%"
                    )

        output.append("\n=== Portfolio Overview ===")
        output.append(f"Total Value: ${criteria.get('total_portfolio_value', 0):.2f}")
        output.append(f"ETH Balance: {portfolio.eth_balance:.4f} ETH")
        output.append(f"Token Holdings: {len(portfolio.token_holdings)}")
        output.append(f"NFT Holdings: {len(portfolio.nft_holdings)}")
        output.append(
            f"Top Asset: {criteria.get('top_asset', 'Unknown')} (${criteria.get('top_value', 0):.2f})"
        )

        output.append("\n=== Activity Metrics ===")
        output.append(f"Active Days (last 365): {criteria.get('active_days', 0)}")
        output.append(f"Total Transactions: {criteria.get('total_transactions', 0)}")
        output.append(f"Swap Count: {criteria.get('swap_count', 0)}")
        output.append(f"Unique Tokens Traded: {criteria.get('unique_tokens', 0)}")

        wallet_creation = criteria.get("wallet_creation_date")
        if wallet_creation:
            output.append(
                f"Wallet Created: {wallet_creation.strftime('%Y-%m-%d')} ({criteria.get('wallet_age_years', 0):.1f} years ago)"
            )
        else:
            output.append("Wallet Created: Unknown")

        output.append("\n=== Holding Patterns ===")
        output.append(
            f"Token Concentration: {criteria.get('token_concentration', 0):.1%}"
        )
        output.append(
            f"Longest Holding Period: {criteria.get('longest_holding_days', 0)} days"
        )
        output.append(f"Holding ETH: {criteria.get('has_eth', False)}")
        output.append(
            f"Top Asset is Token (not ETH): {criteria.get('is_top_asset_token_not_eth', False)}"
        )

        # Persona-specific criteria check
        output.append(f"\n=== {persona} Criteria Analysis ===")

        if persona == "OG (Conservative)":
            output.append(
                f"✓ Token holding > 60%: {criteria.get('token_concentration', 0) > 0.6} ({criteria.get('token_concentration', 0):.1%})"
            )
            output.append(
                f"✓ Holding period > 12 months: {criteria.get('longest_holding_days', 0) > 365} ({criteria.get('longest_holding_days', 0)} days)"
            )
            output.append(
                f"✓ Top asset value < $5,000: {criteria.get('top_value', 0) < 5000} (${criteria.get('top_value', 0):.2f})"
            )
            output.append(
                f"✓ Wallet created < 2020: {wallet_creation and wallet_creation.year < 2020} ({wallet_creation.year if wallet_creation else 'Unknown'})"
            )
            output.append(f"✓ Holding ETH: {criteria.get('has_eth', False)}")

        elif persona == "DeFi Chad (Moderate)":
            output.append(
                f"✓ Longest holding > 3 months: {criteria.get('longest_holding_days', 0) > 90} ({criteria.get('longest_holding_days', 0)} days)"
            )
            output.append(
                f"✓ Token holding > 50%: {criteria.get('token_concentration', 0) > 0.5} ({criteria.get('token_concentration', 0):.1%})"
            )
            output.append(
                f"✓ Active > 120 days: {criteria.get('active_days', 0) > 120} ({criteria.get('active_days', 0)} days)"
            )
            output.append(
                f"✓ Top asset $2,000-$5,000: {2000 < criteria.get('top_value', 0) < 5000} (${criteria.get('top_value', 0):.2f})"
            )

        elif persona == "Degen (Aggressive)":
            output.append(
                f"✓ Active > 180 days: {criteria.get('active_days', 0) > 180} ({criteria.get('active_days', 0)} days)"
            )
            output.append(
                f"✓ Swaps > 100: {criteria.get('swap_count', 0) > 100} ({criteria.get('swap_count', 0)} swaps)"
            )
            output.append(
                f"✓ Holding period < 3 months: {criteria.get('longest_holding_days', 0) < 90} ({criteria.get('longest_holding_days', 0)} days)"
            )
            output.append(
                f"✓ Token holding > 70%: {criteria.get('token_concentration', 0) > 0.7} ({criteria.get('token_concentration', 0):.1%})"
            )
            output.append(
                f"✓ Top asset is token (not ETH): {criteria.get('is_top_asset_token_not_eth', False)}"
            )

        elif persona == "Virgin CT (Newbie)":
            output.append(
                f"✓ Wallet created > 2023: {wallet_creation and wallet_creation.year > 2023} ({wallet_creation.year if wallet_creation else 'Unknown'})"
            )
            output.append(
                f"✓ Active > 30 days: {criteria.get('active_days', 0) > 30} ({criteria.get('active_days', 0)} days)"
            )
            output.append(
                f"✓ Portfolio < $5,000: {criteria.get('total_portfolio_value', 0) < 5000} (${criteria.get('total_portfolio_value', 0):.2f})"
            )
            output.append(
                f"✓ Transactions < 50: {criteria.get('total_transactions', 0) < 50} ({criteria.get('total_transactions', 0)} txs)"
            )

        return "\n".join(output)

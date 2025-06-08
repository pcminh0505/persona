"""
Data models for portfolio analysis.

This module contains the core data structures used throughout the portfolio analysis system.
"""

from datetime import datetime
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TokenHolding:
    """Represents a token holding with valuation data and detailed transaction history."""

    contract_address: str
    symbol: str
    balance: float
    decimals: int
    price_usd: float
    value_usd: float

    # Enhanced holding period tracking
    acquisition_date: Optional[datetime] = None  # First acquisition date
    last_activity_date: Optional[datetime] = None  # Last transaction date
    holding_period_days: int = 0  # Calculated holding period

    # Transaction analysis
    total_acquired: float = 0.0  # Total amount acquired
    total_sold: float = 0.0  # Total amount sold
    acquisition_transactions: int = 0  # Number of buy transactions
    sale_transactions: int = 0  # Number of sell transactions

    # Legacy fields for backward compatibility
    first_acquired: Optional[datetime] = None
    last_acquired: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization to handle legacy field mapping."""
        # Map legacy fields to new fields for backward compatibility
        if self.first_acquired and not self.acquisition_date:
            self.acquisition_date = self.first_acquired
        if self.last_acquired and not self.last_activity_date:
            self.last_activity_date = self.last_acquired

        # Calculate holding period if not set
        if self.holding_period_days == 0 and self.acquisition_date:
            self.holding_period_days = (datetime.now() - self.acquisition_date).days

    @property
    def net_position(self) -> float:
        """Calculate net position (acquired - sold)."""
        return self.total_acquired - self.total_sold

    @property
    def trading_activity_ratio(self) -> float:
        """Calculate trading activity ratio (sales / acquisitions)."""
        if self.total_acquired > 0:
            return self.total_sold / self.total_acquired
        return 0.0

    @property
    def is_active_trader(self) -> bool:
        """Check if this is an actively traded position."""
        return self.sale_transactions > 0 and self.trading_activity_ratio > 0.1


@dataclass
class NFTHolding:
    """Represents an NFT holding with enhanced tracking."""

    contract_address: str
    token_id: str
    collection_name: str
    estimated_value_usd: float = 0.0
    floor_price_usd: float = 0.0
    token_count: int = 1  # For collections, number of tokens

    # Enhanced holding period tracking
    acquisition_date: Optional[datetime] = None
    holding_period_days: int = 0

    # Collection-level data
    token_ids: Optional[List[str]] = None  # List of token IDs in collection

    # Legacy field for backward compatibility
    acquired_date: Optional[datetime] = None

    def __post_init__(self):
        """Post-initialization to handle legacy field mapping."""
        # Map legacy fields to new fields for backward compatibility
        if self.acquired_date and not self.acquisition_date:
            self.acquisition_date = self.acquired_date

        # Calculate holding period if not set
        if self.holding_period_days == 0 and self.acquisition_date:
            self.holding_period_days = (datetime.now() - self.acquisition_date).days

    @property
    def average_value_per_nft(self) -> float:
        """Calculate average value per NFT in the collection."""
        if self.token_count > 0:
            return self.estimated_value_usd / self.token_count
        return 0.0


@dataclass
class PortfolioSnapshot:
    """Represents a complete portfolio snapshot with enhanced analytics."""

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

    @property
    def total_token_value(self) -> float:
        """Get total value of token holdings."""
        return sum(holding.value_usd for holding in self.token_holdings)

    @property
    def total_nft_value(self) -> float:
        """Get total value of NFT holdings."""
        return sum(holding.estimated_value_usd for holding in self.nft_holdings)

    @property
    def portfolio_composition(self) -> dict:
        """Get portfolio composition breakdown."""
        if self.total_value_usd <= 0:
            return {"eth": 0.0, "tokens": 0.0, "nfts": 0.0}

        return {
            "eth": self.eth_value_usd / self.total_value_usd,
            "tokens": self.total_token_value / self.total_value_usd,
            "nfts": self.total_nft_value / self.total_value_usd,
        }

    @property
    def active_trading_positions(self) -> List[TokenHolding]:
        """Get positions that show active trading behavior."""
        return [holding for holding in self.token_holdings if holding.is_active_trader]

    @property
    def long_term_holdings(self) -> List[TokenHolding]:
        """Get positions held for more than 1 year."""
        return [
            holding
            for holding in self.token_holdings
            if holding.holding_period_days > 365
        ]

    @property
    def recent_acquisitions(self) -> List[TokenHolding]:
        """Get positions acquired in the last 30 days."""
        return [
            holding
            for holding in self.token_holdings
            if holding.holding_period_days <= 30
        ]

    def get_significant_token_holdings(
        self, min_value_usd: float = 5.0
    ) -> List[TokenHolding]:
        """Get token holdings with value above the specified threshold."""
        return [
            holding
            for holding in self.token_holdings
            if holding.value_usd >= min_value_usd
        ]

    def get_significant_nft_holdings(
        self, min_value_usd: float = 5.0
    ) -> List[NFTHolding]:
        """Get NFT holdings with value above the specified threshold."""
        return [
            holding
            for holding in self.nft_holdings
            if holding.estimated_value_usd >= min_value_usd
        ]

    def get_all_significant_positions(self, min_value_usd: float = 5.0) -> dict:
        """Get all positions (ETH, tokens, NFTs) with value above the specified threshold."""
        positions = {
            "eth": self.eth_value_usd >= min_value_usd,
            "eth_value": (
                self.eth_value_usd if self.eth_value_usd >= min_value_usd else 0
            ),
            "tokens": self.get_significant_token_holdings(min_value_usd),
            "nfts": self.get_significant_nft_holdings(min_value_usd),
        }

        # Calculate total significant value
        total_significant_value = positions["eth_value"]
        total_significant_value += sum(t.value_usd for t in positions["tokens"])
        total_significant_value += sum(n.estimated_value_usd for n in positions["nfts"])

        positions["total_significant_value"] = total_significant_value
        positions["significant_position_count"] = (
            (1 if positions["eth"] else 0)
            + len(positions["tokens"])
            + len(positions["nfts"])
        )

        return positions

    @property
    def dust_positions_count(self) -> int:
        """Count positions with value less than $5 (dust positions)."""
        dust_count = 0

        # Count ETH if less than $5
        if 0 < self.eth_value_usd < 5.0:
            dust_count += 1

        # Count tokens less than $5
        dust_count += len([t for t in self.token_holdings if 0 < t.value_usd < 5.0])

        # Count NFTs less than $5
        dust_count += len(
            [n for n in self.nft_holdings if 0 < n.estimated_value_usd < 5.0]
        )

        return dust_count

    @property
    def dust_value_usd(self) -> float:
        """Total value of dust positions (less than $5)."""
        dust_value = 0.0

        # Add ETH if less than $5
        if 0 < self.eth_value_usd < 5.0:
            dust_value += self.eth_value_usd

        # Add tokens less than $5
        dust_value += sum(
            t.value_usd for t in self.token_holdings if 0 < t.value_usd < 5.0
        )

        # Add NFTs less than $5
        dust_value += sum(
            n.estimated_value_usd
            for n in self.nft_holdings
            if 0 < n.estimated_value_usd < 5.0
        )

        return dust_value

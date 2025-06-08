"""
Pricing service for fetching token and ETH prices.

This service handles all price-related operations including token prices from DeFiLlama
and ETH price fetching.
"""

import aiohttp
from typing import Dict, List, Optional


class PricingService:
    """Service for fetching cryptocurrency and token prices."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize with optional aiohttp session."""
        self.session = session
        self._own_session = session is None

    async def __aenter__(self):
        """Async context manager entry."""
        if self._own_session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._own_session and self.session:
            await self.session.close()

    async def get_token_prices(
        self, token_addresses: List[str], chain: str = "base"
    ) -> Dict[str, float]:
        """Get token prices from DeFiLlama API."""
        if not self.session or not token_addresses:
            return {}

        try:
            addresses_str = ",".join([f"{chain}:{addr}" for addr in token_addresses])
            url = f"https://coins.llama.fi/prices/current/{addresses_str}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = {}

                    for key, value in data.get("coins", {}).items():
                        if ":" in key:
                            address = key.split(":", 1)[1]
                            prices[address.lower()] = value.get("price", 0.0)

                    return prices
        except Exception as e:
            print(f"Error fetching token prices: {e}")

        return {}

    async def get_eth_price(self) -> float:
        """Get current ETH price."""
        if not self.session:
            return 0.0

        try:
            url = "https://coins.llama.fi/prices/current/ethereum:0x0000000000000000000000000000000000000000"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return (
                        data.get("coins", {})
                        .get("ethereum:0x0000000000000000000000000000000000000000", {})
                        .get("price", 0.0)
                    )
        except Exception as e:
            print(f"Error fetching ETH price: {e}")

        return 0.0

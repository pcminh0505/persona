#!/usr/bin/env python3
"""
Zerion API Adapter
Specific adapter for fetching data from Zerion API.
Documentation: https://developers.zerion.io/reference/listwalletpositions
"""

import os
import base64
from typing import Dict, Optional, Any, List

from .base import BaseAdapter


class ZerionAdapter(BaseAdapter):
    """Adapter for Zerion API to fetch wallet positions and blockchain data."""

    def __init__(self, api_key: str = None, use_testnet: bool = False):
        """
        Initialize Zerion adapter.

        Args:
            api_key: Zerion API key (can also be set via ZERION_API_KEY env var)
            use_testnet: Whether to use testnet data (sets X-Env header)
        """

        raw_api_key = api_key or os.getenv("ZERION_API_KEY")
        encoded_bytes = base64.b64encode(f"{raw_api_key}:".encode("utf-8"))
        self.api_key = encoded_bytes.decode("utf-8")
        self.use_testnet = use_testnet

        # Set up headers for Zerion API
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Basic {self.api_key}"

        if self.use_testnet:
            headers["X-Env"] = "testnet"

        # Initialize base adapter with Zerion API URL
        super().__init__(
            base_url="https://api.zerion.io/v1",
            headers=headers,
            timeout=120,  # Zerion recommends 2 minutes timeout
        )

    def authenticate(self) -> bool:
        """
        Authenticate with Zerion API by testing a simple endpoint.

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.api_key:
            self._handle_error("No API key provided for Zerion authentication")
            return False

        try:
            # Test authentication with chains endpoint
            response = self.get_chains()
            return response is not None and self.validate_response(response)
        except Exception as e:
            self._handle_error(f"Authentication failed: {e}")
            return False

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate Zerion API response format.

        Args:
            response: API response dictionary

        Returns:
            True if response is valid, False otherwise
        """
        # Basic validation for Zerion API response structure
        if not isinstance(response, dict):
            return False

        # Check for typical Zerion response structure
        # Most Zerion responses have 'data' field
        return "data" in response or "links" in response or "meta" in response

    def get_wallet_positions(self, wallet_address: str, **kwargs) -> Optional[Dict]:
        """
        Get list of wallet's fungible positions.

        Args:
            wallet_address: Wallet address to fetch positions for
            **kwargs: Additional query parameters (currency, sort, etc.)

        Returns:
            Wallet positions data or None if failed
        """
        endpoint = f"wallets/{wallet_address}/positions"

        # Build query parameters
        params = {}

        # Common parameters from Zerion API docs
        supported_params = [
            "currency",
            "sort",
            "page[size]",
            "page[before]",
            "page[after]",
            "filter[positions]",
            "filter[trash]",
            "filter[dust]",
            "filter[chain_ids]",
        ]

        for param in supported_params:
            if param in kwargs:
                params[param] = kwargs[param]

        return self.get(endpoint, params=params)

    def get_wallet_portfolio(self, wallet_address: str, **kwargs) -> Optional[Dict]:
        """
        Get wallet's portfolio overview.

        Args:
            wallet_address: Wallet address to fetch portfolio for
            **kwargs: Additional query parameters

        Returns:
            Portfolio data or None if failed
        """
        endpoint = f"wallets/{wallet_address}/portfolio"
        return self.get(endpoint, params=kwargs)

    def get_wallet_transactions(self, wallet_address: str, **kwargs) -> Optional[Dict]:
        """
        Get list of wallet's transactions.

        Args:
            wallet_address: Wallet address to fetch transactions for
            **kwargs: Additional query parameters

        Returns:
            Transactions data or None if failed
        """
        endpoint = f"wallets/{wallet_address}/transactions"
        return self.get(endpoint, params=kwargs)

    def get_wallet_nft_collections(
        self, wallet_address: str, **kwargs
    ) -> Optional[Dict]:
        """
        Get list of wallet's NFT collections.

        Args:
            wallet_address: Wallet address to fetch NFT collections for
            **kwargs: Additional query parameters

        Returns:
            NFT collections data or None if failed
        """
        endpoint = f"wallets/{wallet_address}/nft-collections"
        return self.get(endpoint, params=kwargs)

    def get_fungible_assets(self, **kwargs) -> Optional[Dict]:
        """
        Get list of fungible assets.

        Args:
            **kwargs: Query parameters for filtering assets

        Returns:
            Fungible assets data or None if failed
        """
        return self.get("fungibles", params=kwargs)

    def get_fungible_asset_by_id(self, asset_id: str) -> Optional[Dict]:
        """
        Get specific fungible asset by ID.

        Args:
            asset_id: Asset ID to fetch

        Returns:
            Asset data or None if failed
        """
        return self.get(f"fungibles/{asset_id}")

    def get_chains(self) -> Optional[Dict]:
        """
        Get list of all supported chains.

        Returns:
            Chains data or None if failed
        """
        return self.get("chains")

    def get_chain_by_id(self, chain_id: str) -> Optional[Dict]:
        """
        Get specific chain by ID.

        Args:
            chain_id: Chain ID to fetch

        Returns:
            Chain data or None if failed
        """
        return self.get(f"chains/{chain_id}")

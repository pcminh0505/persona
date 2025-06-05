#!/usr/bin/env python3
"""
Etherscan API v2 Adapter
Specific adapter for fetching data from Etherscan API v2.
Documentation: https://docs.etherscan.io/etherscan-v2/api-endpoints/accounts
"""

import os
from typing import Dict, Optional, Any, List, Union
from .base import BaseAdapter


class EtherscanAdapter(BaseAdapter):
    """Adapter for Etherscan API v2 to fetch Ethereum blockchain data."""

    def __init__(self, api_key: str = None, chain_id: int = 1):
        """
        Initialize Etherscan adapter.

        Args:
            api_key: Etherscan API key (can also be set via ETHERSCAN_API_KEY env var)
            chain_id: Chain ID (1 for Ethereum mainnet, 5 for Goerli, etc.)
        """
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY")
        self.chain_id = chain_id

        if not self.api_key:
            raise ValueError(
                "Etherscan API key is required. Set ETHERSCAN_API_KEY env var or pass api_key parameter."
            )

        # Initialize base adapter with Etherscan API URL
        super().__init__(base_url="https://api.etherscan.io/v2/api", timeout=30)

    def authenticate(self) -> bool:
        """
        Authenticate with Etherscan API by testing a simple endpoint.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Test authentication with a simple balance check
            response = self.get_ether_balance(
                "0x0000000000000000000000000000000000000000"
            )
            return response is not None and self.validate_response(response)
        except Exception as e:
            self._handle_error(f"Authentication failed: {e}")
            return False

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate Etherscan API response format.

        Args:
            response: API response dictionary

        Returns:
            True if response is valid, False otherwise
        """
        # Basic validation for Etherscan API response structure
        if not isinstance(response, dict):
            return False

        # Check for typical Etherscan response structure
        return "status" in response and "message" in response and "result" in response

    def _build_params(self, **kwargs) -> Dict[str, Any]:
        """Build common parameters for Etherscan API requests."""
        params = {"chainid": self.chain_id, "apikey": self.api_key}
        params.update(kwargs)
        return params

    # === Balance Endpoints ===

    def get_ether_balance(self, address: str, tag: str = "latest") -> Optional[Dict]:
        """
        Get Ether balance for a single address.

        Args:
            address: Ethereum address to check balance for
            tag: Block parameter ('earliest', 'pending', or 'latest')

        Returns:
            Balance data or None if failed
        """
        params = self._build_params(
            module="account", action="balance", address=address, tag=tag
        )
        return self.get("", params=params)

    def get_ether_balance_multi(
        self, addresses: List[str], tag: str = "latest"
    ) -> Optional[Dict]:
        """
        Get Ether balance for multiple addresses in a single call.

        Args:
            addresses: List of Ethereum addresses (up to 20 addresses)
            tag: Block parameter ('earliest', 'pending', or 'latest')

        Returns:
            Balance data for all addresses or None if failed
        """
        if len(addresses) > 20:
            raise ValueError("Maximum 20 addresses allowed per call")

        params = self._build_params(
            module="account",
            action="balancemulti",
            address=",".join(addresses),
            tag=tag,
        )
        return self.get("", params=params)

    def get_historical_ether_balance(
        self, address: str, block_no: int
    ) -> Optional[Dict]:
        """
        Get historical Ether balance for a single address by block number.
        Note: This endpoint is throttled to 2 calls/second regardless of API Pro tier.

        Args:
            address: Ethereum address to check balance for
            block_no: Block number to check balance at

        Returns:
            Historical balance data or None if failed
        """
        params = self._build_params(
            module="account", action="balancehistory", address=address, blockno=block_no
        )
        return self.get("", params=params)

    # === Transaction Endpoints ===

    def get_normal_transactions(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 10,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get list of normal transactions by address.

        Args:
            address: Ethereum address to get transactions for
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of transactions per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            Transaction list or None if failed
        """
        params = self._build_params(
            module="account",
            action="txlist",
            address=address,
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )
        return self.get("", params=params)

    def get_internal_transactions(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 10,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get list of internal transactions by address.

        Args:
            address: Ethereum address to get internal transactions for
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of transactions per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            Internal transaction list or None if failed
        """
        params = self._build_params(
            module="account",
            action="txlistinternal",
            address=address,
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )
        return self.get("", params=params)

    def get_internal_transactions_by_hash(self, txhash: str) -> Optional[Dict]:
        """
        Get internal transactions by transaction hash.

        Args:
            txhash: Transaction hash to get internal transactions for

        Returns:
            Internal transaction data or None if failed
        """
        params = self._build_params(
            module="account", action="txlistinternal", txhash=txhash
        )
        return self.get("", params=params)

    def get_internal_transactions_by_block_range(
        self,
        startblock: int,
        endblock: int,
        page: int = 1,
        offset: int = 10,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get internal transactions by block range.

        Args:
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of transactions per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            Internal transaction list or None if failed
        """
        params = self._build_params(
            module="account",
            action="txlistinternal",
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )
        return self.get("", params=params)

    # === Token Transfer Endpoints ===

    def get_erc20_token_transfers(
        self,
        address: str,
        contractaddress: str = None,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get list of ERC20 token transfer events by address.

        Args:
            address: Ethereum address to get token transfers for
            contractaddress: Token contract address (optional, for specific token)
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of transfers per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            ERC20 token transfer list or None if failed
        """
        params = self._build_params(
            module="account",
            action="tokentx",
            address=address,
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )

        if contractaddress:
            params["contractaddress"] = contractaddress

        return self.get("", params=params)

    def get_erc721_token_transfers(
        self,
        address: str,
        contractaddress: str = None,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get list of ERC721 token transfer events by address.

        Args:
            address: Ethereum address to get NFT transfers for
            contractaddress: NFT contract address (optional, for specific collection)
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of transfers per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            ERC721 token transfer list or None if failed
        """
        params = self._build_params(
            module="account",
            action="tokennfttx",
            address=address,
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )

        if contractaddress:
            params["contractaddress"] = contractaddress

        return self.get("", params=params)

    def get_erc1155_token_transfers(
        self,
        address: str,
        contractaddress: str = None,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get list of ERC1155 token transfer events by address.

        Args:
            address: Ethereum address to get ERC1155 transfers for
            contractaddress: ERC1155 contract address (optional, for specific collection)
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of transfers per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            ERC1155 token transfer list or None if failed
        """
        params = self._build_params(
            module="account",
            action="token1155tx",
            address=address,
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )

        if contractaddress:
            params["contractaddress"] = contractaddress

        return self.get("", params=params)

    # === Other Account Endpoints ===

    def get_address_funded_by(self, address: str) -> Optional[Dict]:
        """
        Get the address that funded an address and its relative age.

        Args:
            address: Ethereum address to check funding for

        Returns:
            Funding information or None if failed
        """
        params = self._build_params(
            module="account", action="fundedby", address=address
        )
        return self.get("", params=params)

    def get_mined_blocks(
        self, address: str, blocktype: str = "blocks", page: int = 1, offset: int = 10
    ) -> Optional[Dict]:
        """
        Get list of blocks validated by address.

        Args:
            address: Ethereum address (miner/validator)
            blocktype: Type of blocks ('blocks' for canonical, 'uncles' for uncle blocks)
            page: Page number for pagination
            offset: Number of blocks per page

        Returns:
            Mined blocks list or None if failed
        """
        params = self._build_params(
            module="account",
            action="getminedblocks",
            address=address,
            blocktype=blocktype,
            page=page,
            offset=offset,
        )
        return self.get("", params=params)

    def get_beacon_withdrawals(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = "asc",
    ) -> Optional[Dict]:
        """
        Get beacon chain withdrawals by address and block range.

        Args:
            address: Ethereum address to check withdrawals for
            startblock: Starting block number
            endblock: Ending block number
            page: Page number for pagination
            offset: Number of withdrawals per page
            sort: Sort order ('asc' or 'desc')

        Returns:
            Beacon withdrawal list or None if failed
        """
        params = self._build_params(
            module="account",
            action="txsBeaconWithdrawal",
            address=address,
            startblock=startblock,
            endblock=endblock,
            page=page,
            offset=offset,
            sort=sort,
        )
        return self.get("", params=params)


def example_usage():
    """Example usage of the Etherscan adapter."""

    # Initialize adapter (API key should be in environment or passed directly)
    try:
        adapter = EtherscanAdapter(chain_id=1)  # Ethereum mainnet
    except ValueError as e:
        print(f"❌ {e}")
        print("Please set ETHERSCAN_API_KEY environment variable")
        return

    # Test authentication
    if not adapter.authenticate():
        print("❌ Authentication failed. Please check your API key.")
        return

    print("✅ Authentication successful!")

    # Example Ethereum address (Vitalik's address)
    example_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    print(f"\nFetching data for address: {example_address}")

    # Get Ether balance
    print("\n💰 Fetching Ether balance...")
    balance = adapter.get_ether_balance(example_address)
    if balance and adapter.validate_response(balance):
        balance_wei = balance.get("result", "0")
        balance_eth = int(balance_wei) / 10**18 if balance_wei.isdigit() else 0
        print(f"Balance: {balance_eth:.4f} ETH ({balance_wei} wei)")
    else:
        print("Failed to fetch balance")

    # Get recent transactions
    print("\n📝 Fetching recent transactions...")
    transactions = adapter.get_normal_transactions(
        example_address, startblock=0, endblock=99999999, page=1, offset=5, sort="desc"
    )

    if transactions and adapter.validate_response(transactions):
        tx_list = transactions.get("result", [])
        print(f"Found {len(tx_list)} recent transactions:")
        for i, tx in enumerate(tx_list[:3]):  # Show first 3
            value_eth = (
                int(tx.get("value", "0")) / 10**18
                if tx.get("value", "0").isdigit()
                else 0
            )
            print(
                f"  {i+1}. Hash: {tx.get('hash', 'N/A')[:20]}... Value: {value_eth:.4f} ETH"
            )
    else:
        print("Failed to fetch transactions")

    # Get multiple balances
    print("\n🏦 Fetching multiple balances...")
    test_addresses = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Vitalik
        "0x0000000000000000000000000000000000000000",  # Zero address
    ]

    multi_balance = adapter.get_ether_balance_multi(test_addresses)
    if multi_balance and adapter.validate_response(multi_balance):
        balances = multi_balance.get("result", [])
        for balance_info in balances:
            addr = balance_info.get("account", "Unknown")
            balance_wei = balance_info.get("balance", "0")
            balance_eth = int(balance_wei) / 10**18 if balance_wei.isdigit() else 0
            print(f"  {addr[:10]}... : {balance_eth:.4f} ETH")
    else:
        print("Failed to fetch multiple balances")


if __name__ == "__main__":
    example_usage()

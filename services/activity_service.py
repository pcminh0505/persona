"""
Activity service for analyzing wallet activity patterns.

This service handles transaction analysis, swap detection, and activity scoring
for wallet addresses using blockchain data.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict


class ActivityService:
    """Service for analyzing wallet activity patterns."""

    def __init__(self, etherscan_adapter):
        """Initialize with EtherscanAdapter."""
        self.etherscan_adapter = etherscan_adapter

    async def get_wallet_creation_date(self, address: str) -> Optional[datetime]:
        """Get the wallet creation date (first transaction) using Etherscan data."""
        try:
            response = self.etherscan_adapter.get_normal_transactions(
                address, page=1, offset=10000, sort="asc"
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return None

            transactions = response.get("result", [])
            if transactions:
                first_tx = transactions[0]
                if first_tx.get("timeStamp"):
                    return datetime.fromtimestamp(int(first_tx["timeStamp"]))

        except Exception as e:
            print(f"Error getting wallet creation date: {e}")

        return None

    async def calculate_activity_score(
        self, address: str, days: int = 365
    ) -> Dict[str, int]:
        """Calculate wallet activity metrics using Etherscan data."""
        try:
            since_date = datetime.now() - timedelta(days=days)

            response = self.etherscan_adapter.get_normal_transactions(
                address, page=1, offset=10000
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return {"active_days": 0, "total_transactions": 0}

            transactions = response.get("result", [])
            active_days = set()
            total_transactions = 0

            for tx in transactions:
                if tx.get("timeStamp"):
                    tx_date = datetime.fromtimestamp(int(tx["timeStamp"]))
                    if tx_date >= since_date:
                        active_days.add(tx_date.date())
                        total_transactions += 1

            return {
                "active_days": len(active_days),
                "total_transactions": total_transactions,
            }

        except Exception as e:
            print(f"Error calculating activity score: {e}")
            return {"active_days": 0, "total_transactions": 0}

    async def analyze_swap_activity(
        self, address: str, days: int = 365
    ) -> Dict[str, Any]:
        """Analyze swap/DEX activity for an address using Etherscan data."""
        try:
            since_date = datetime.now() - timedelta(days=days)

            response = self.etherscan_adapter.get_erc20_token_transfers(
                address, page=1, offset=10000
            )
            if not response or not self.etherscan_adapter.validate_response(response):
                return {"swap_count": 0, "unique_tokens": 0, "dex_interactions": 0}

            transfers = response.get("result", [])
            tx_transfers = defaultdict(list)
            unique_tokens = set()
            swap_count = 0

            for transfer in transfers:
                if transfer.get("timeStamp"):
                    transfer_date = datetime.fromtimestamp(int(transfer["timeStamp"]))
                    if transfer_date >= since_date:
                        tx_hash = transfer.get("hash")
                        if tx_hash:
                            tx_transfers[tx_hash].append(transfer)
                            if transfer.get("contractAddress"):
                                unique_tokens.add(transfer["contractAddress"].lower())

            for tx_hash, tx_transfer_list in tx_transfers.items():
                if len(tx_transfer_list) >= 2:
                    swap_count += 1

            return {
                "swap_count": swap_count,
                "unique_tokens": len(unique_tokens),
                "dex_interactions": len(tx_transfers),
            }

        except Exception as e:
            print(f"Error analyzing swap activity: {e}")
            return {"swap_count": 0, "unique_tokens": 0, "dex_interactions": 0}

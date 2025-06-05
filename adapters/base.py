#!/usr/bin/env python3
"""
Base Adapter for Data Source Integrations
A foundational class for creating specific API adapters.
"""

import os
import json
import requests
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# Load environment variables from .env file
load_dotenv()


class BaseAdapter(ABC):
    """Base adapter class for API integrations with common functionality."""

    def __init__(
        self, base_url: str = None, headers: Dict[str, str] = None, timeout: int = 30
    ):
        """
        Initialize the base adapter.

        Args:
            base_url: Base URL for API endpoints
            headers: Default headers for requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or ""
        self.headers = headers or {}
        self.timeout = timeout
        self.session = requests.Session()

        # Set default headers
        if self.headers:
            self.session.headers.update(self.headers)

    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Perform a GET request to the specified endpoint.

        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters

        Returns:
            JSON response as dictionary or None if failed
        """
        try:
            url = self._build_url(endpoint)
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(f"Error fetching data from {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            self._handle_error(f"Error parsing JSON response: {e}")
            return None

    def post(
        self,
        endpoint: str,
        data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
    ) -> Optional[Dict]:
        """
        Perform a POST request to the specified endpoint.

        Args:
            endpoint: API endpoint
            data: Form data to send
            json_data: JSON data to send

        Returns:
            JSON response as dictionary or None if failed
        """
        try:
            url = self._build_url(endpoint)
            response = self.session.post(
                url, data=data, json=json_data, timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(f"Error posting data to {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            self._handle_error(f"Error parsing JSON response: {e}")
            return None

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint."""
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _handle_error(self, message: str) -> None:
        """Handle error messages. Can be overridden by subclasses."""
        print(message)

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the API service.
        Must be implemented by subclasses.

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate API response format.
        Must be implemented by subclasses.

        Args:
            response: API response dictionary

        Returns:
            True if response is valid, False otherwise
        """
        pass

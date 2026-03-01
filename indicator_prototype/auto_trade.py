"""
auto_trade.py

Minimal, unofficial Robinhood Crypto helper for basic trading actions.

Usage:
 - Set environment variable `ROBINHOOD_TOKEN` with an API token (preferred).
 - Or provide `username`/`password` to authenticate (not implemented here).

This module provides a small `RobinhoodClient` with `get_quote`, `place_order`,
`get_order`, and `cancel_order` helpers. Use at your own risk — test in a sandbox
or with minimal sizes first.
"""
from __future__ import annotations

import os
import time
from typing import Optional, Dict, Any

import requests


class RobinhoodError(Exception):
    pass


class RobinhoodClient:
    """Simple Robinhood crypto client (unofficial).

    This implements a minimal subset of endpoints described in the Robinhood
    crypto trading docs. It expects an auth token set in the `ROBINHOOD_TOKEN`
    environment variable or passed as `auth_token`.
    """

    def __init__(self, auth_token: Optional[str] = None, base_url: str = "https://api.robinhood.com"):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or os.environ.get("ROBINHOOD_TOKEN")
        self.session = requests.Session()
        if self.auth_token:
            self.session.headers.update({"Authorization": f"Token {self.auth_token}"})
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, timeout=20, **kwargs)
        except requests.RequestException as exc:
            raise RobinhoodError(f"network error: {exc}") from exc

        if not resp.ok:
            # Try to extract JSON error
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RobinhoodError(f"HTTP {resp.status_code}: {detail}")

        try:
            return resp.json()
        except Exception:
            return {"raw_text": resp.text}

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get latest quote for a crypto symbol.

        symbol: string symbol like 'BTC' or 'ETH'.
        Returns parsed JSON response (may contain price and other fields).
        """
        # Using the crypto quotes endpoint; path may vary by API version.
        path = f"/crypto/quotes/?symbols={symbol}"
        return self._request("GET", path)

    def place_order(self, symbol: str, side: str, quantity: float, price: Optional[float] = None, order_type: str = "market", time_in_force: str = "gtc") -> Dict[str, Any]:
        """Place a crypto order.

        side: 'buy' or 'sell'
        order_type: 'market' or 'limit'
        price: required for limit orders
        quantity: number of coins (or fractional amount)
        """
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        if order_type == "limit" and price is None:
            raise ValueError("limit orders require a price")

        path = "/crypto/orders/"
        payload: Dict[str, Any] = {
            "currency_pair": symbol,
            "side": side,
            "quantity": str(quantity),
            "time_in_force": time_in_force,
            "type": order_type,
        }
        if price is not None:
            payload["price"] = str(price)

        return self._request("POST", path, json=payload)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        path = f"/crypto/orders/{order_id}/"
        return self._request("GET", path)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        path = f"/crypto/orders/{order_id}/cancel/"
        return self._request("POST", path)


def auto_trade_example():
    """Example: fetch quote and (optionally) place a small market buy.

    WARNING: This will place real orders if `ROBINHOOD_TOKEN` is valid.
    Test carefully and use small quantities.
    """
    client = RobinhoodClient()
    if not client.auth_token:
        raise RuntimeError("No ROBINHOOD_TOKEN found in environment; set ROBINHOOD_TOKEN to continue")

    symbol = "BTC"  # change to desired symbol
    print(f"Fetching quote for {symbol}...")
    quote = client.get_quote(symbol)
    print("Quote:", quote)

    # Example: place a tiny market buy (uncomment to execute)
    # try:
    #     print("Placing market buy for 0.0001 BTC...")
    #     order = client.place_order(symbol, side="buy", quantity=0.0001, order_type="market")
    #     print("Order response:", order)
    # except RobinhoodError as e:
    #     print("Order failed:", e)


if __name__ == "__main__":
    try:
        auto_trade_example()
    except Exception as exc:
        print("Error:", exc)

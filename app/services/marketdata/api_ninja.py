from __future__ import annotations

from typing import Any, Dict, List

import httpx


BASE_URL = "https://api.api-ninjas.com/v1"


class ApiNinjaClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("API_NINJA_APIKEY is required")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def contract_list(self) -> List[Dict[str, Any]]:
        url = f"{BASE_URL}/commoditycontractlist"
        resp = httpx.get(url, headers=self._headers(), timeout=20.0)
        resp.raise_for_status()
        return resp.json()

    def contract_symbols(self) -> List[str]:
        data = self.contract_list()
        symbols: List[str] = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    symbols.append(item)
                elif isinstance(item, dict) and "symbol" in item:
                    symbols.append(str(item["symbol"]))
        elif isinstance(data, dict):
            for item in data.get("symbols", []):
                if isinstance(item, str):
                    symbols.append(item)
        return symbols

    def contract_quote(self, symbol: str) -> Dict[str, Any]:
        url = f"{BASE_URL}/commoditycontract"
        resp = httpx.get(url, headers=self._headers(), params={"symbol": symbol}, timeout=20.0)
        resp.raise_for_status()
        return resp.json()

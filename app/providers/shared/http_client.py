import httpx
from typing import Dict, Any
from app.providers.shared.exceptions import ProviderTimeoutError, ProviderUnavailableError

class SharedHTTPClient:
    """
    Shared async HTTP pooling for non-blocking I/O.
    """
    def __init__(self, timeout_ms: int = 5000):
        self.timeout = httpx.Timeout(timeout_ms / 1000.0)
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def get(self, url: str, params: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"Request to {url} timed out.")
        except httpx.RequestError as e:
            raise ProviderUnavailableError(f"Request failed: {str(e)}")

    async def close(self):
        await self.client.aclose()

from typing import Dict, Any

class ProviderConfig:
    """
    Base configuration for all providers. Passed in via dependency injection.
    """
    def __init__(self, api_key: str = "", base_url: str = "", timeout_ms: int = 5000):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_ms = timeout_ms
        self.extra_config: Dict[str, Any] = {}

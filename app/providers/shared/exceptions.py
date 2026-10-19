class ProviderError(Exception):
    """Base class for all provider exceptions."""
    pass

class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""
    pass

class ProviderAuthenticationError(ProviderError):
    """Raised when a provider rejects credentials."""
    pass

class ProviderRateLimitError(ProviderError):
    """Raised when a provider rate limit is exceeded."""
    pass

class ProviderUnavailableError(ProviderError):
    """Raised when a provider is down or unreachable."""
    pass

class ProviderResponseMappingError(ProviderError):
    """Raised when the mapping layer fails to parse a vendor response."""
    pass

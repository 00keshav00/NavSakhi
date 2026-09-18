import functools
import asyncio
from typing import Callable, Any
from app.providers.shared.exceptions import ProviderError, ProviderTimeoutError

def with_retry(max_retries: int = 3, base_delay_ms: int = 100) -> Callable:
    """
    Decorator implementing exponential backoff and jitter for Provider network calls.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (ProviderTimeoutError, ConnectionError) as e:
                    last_error = e
                    delay = (base_delay_ms * (2 ** attempt)) / 1000.0
                    await asyncio.sleep(delay)
                except ProviderError:
                    # Do not retry on mapping or auth errors
                    raise
            raise last_error
        return wrapper
    return decorator

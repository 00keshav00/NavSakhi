import functools
from typing import Callable, Any, Dict
import hashlib
import json

class ProviderCache:
    """
    Simple in-memory cache decorator for Provider HTTP responses.
    Production systems would replace this with Redis.
    """
    _cache: Dict[str, Any] = {}

    @staticmethod
    def cached(ttl_seconds: int = 300) -> Callable:
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs) -> Any:
                # Create a deterministic cache key based on function name and args
                key_material = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
                key = f"{func.__name__}:{hashlib.sha256(key_material.encode()).hexdigest()}"
                
                if key in ProviderCache._cache:
                    return ProviderCache._cache[key]
                    
                result = await func(self, *args, **kwargs)
                ProviderCache._cache[key] = result
                return result
            return wrapper
        return decorator

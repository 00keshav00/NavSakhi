import time
from typing import Callable, Any
import functools
from app.providers.shared.exceptions import ProviderUnavailableError
from app.providers.shared.metrics import ProviderMetrics

class CircuitBreaker:
    """
    Prevents cascading failures by tripping after a threshold of consecutive failures.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout_sec: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if self.is_open:
                if time.time() - self.last_failure_time > self.recovery_timeout_sec:
                    # Half-open state
                    self.is_open = False
                else:
                    raise ProviderUnavailableError(f"Circuit breaker is OPEN for {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                # Success - reset
                self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    if not self.is_open:
                        ProviderMetrics.log_circuit_trip(func.__name__)
                    self.is_open = True
                raise
        return wrapper

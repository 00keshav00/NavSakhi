class SafeSheException(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "BAD_REQUEST", details: dict = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

class ResourceNotFoundException(SafeSheException):
    def __init__(self, resource: str):
        super().__init__(
            message=f"{resource} not found.",
            status_code=404,
            error_code="NOT_FOUND"
        )

class ProviderNotConfiguredError(SafeSheException):
    def __init__(self, provider_name: str):
        super().__init__(
            message=f"Provider '{provider_name}' is not configured or unavailable.",
            status_code=500,
            error_code="PROVIDER_NOT_CONFIGURED"
        )

class ValidationException(SafeSheException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )

class InvalidStateTransitionError(SafeSheException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=409,
            error_code="INVALID_STATE_TRANSITION"
        )

class UnauthorizedException(SafeSheException):
    def __init__(self, message: str = "Invalid credentials or missing token."):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED"
        )

class ForbiddenException(SafeSheException):
    def __init__(self, message: str = "You do not have permission to access this resource."):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN"
        )

class ConflictException(SafeSheException):
    def __init__(self, message: str = "Resource already exists."):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT"
        )

class DatabaseUnavailableException(SafeSheException):
    def __init__(self, message: str = "Database configuration unavailable. Account creation requires a configured database. Please continue exploring as a guest."):
        super().__init__(
            message=message,
            status_code=503,
            error_code="DATABASE_UNAVAILABLE"
        )


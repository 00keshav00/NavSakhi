from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.exceptions import SafeSheException
from app.schemas.responses import ErrorResponse, ErrorDetails

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(SafeSheException)
    async def safeshe_exception_handler(request: Request, exc: SafeSheException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetails(
                    code=exc.error_code,
                    message=exc.message,
                    details=exc.details
                )
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                success=False,
                error=ErrorDetails(
                    code="UNPROCESSABLE_ENTITY",
                    message="Request validation failed.",
                    details=exc.errors()
                )
            ).model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        from app.config.logging_config import logger
        logger.exception("Unhandled Exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                success=False,
                error=ErrorDetails(
                    code="INTERNAL_SERVER_ERROR",
                    message="An internal server error occurred.",
                    details=str(exc) # Remove in production for security
                )
            ).model_dump(exclude_none=True),
        )

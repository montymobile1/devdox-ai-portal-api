from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse

from app.config import settings


class APIResponse:
    """Utility class for standardized API responses."""

    @staticmethod
    def success(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a success response."""
        response = {"success": True, "message": message, "status_code": 200}
        if data is not None:
            response["data"] = data

        return JSONResponse(content=response, status_code=200)

    @staticmethod
    def error(
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400,
        debug: Any = None,
    ) -> Dict[str, Any]:
        """Generate an error response."""
        response = {
            "success": False,
            "message": message,
            "status_code": status_code,
            "error_code": status_code,
        }
        if details is not None:
            response["details"] = details

        if settings.API_ENV in ["development", "test"]:
            response["debug"] = debug

        return JSONResponse(content=response, status_code=status_code)

    @staticmethod
    def validation_error(
        message: str, details: Optional[list] = None
    ) -> Dict[str, Any]:
        """Generate a validation error response."""
        response = {"success": False, "message": message, "status_code": 422}
        if details is not None:
            response["validation_errors"] = details
        return JSONResponse(content=response, status_code=422)

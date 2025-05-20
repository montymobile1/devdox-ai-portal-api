from typing import Any, Dict, Optional
from pydantic import BaseModel


class APIResponse:
    """Utility class for standardized API responses."""

    @staticmethod
    def success(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a success response."""
        response = {
            "success": True,
            "message": message,
            "status_code": 200
        }
        if data is not None:
            response["data"] = data
        return response

    @staticmethod
    def error(message: str, details: Optional[Dict[str, Any]] = None, status_code: int = 400) -> Dict[str, Any]:
        """Generate an error response."""
        response = {
            "success": False,
            "message": message,
            "status_code": status_code
        }
        if details is not None:
            response["details"] = details
        return response

    @staticmethod
    def validation_error(message: str, errors: Optional[list] = None) -> Dict[str, Any]:
        """Generate a validation error response."""
        response = {
            "success": False,
            "message": message,
            "status_code": 422
        }
        if errors is not None:
            response["validation_errors"] = errors
        return response

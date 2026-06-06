from dataclasses import dataclass
from typing import Any, Optional
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from starlette.responses import JSONResponse
from fastapi import status
from enum import Enum



@dataclass
class AppException(HTTPException):
    """Custom APP Exception object to raise `HTTPException` with app `ErrorCode` handling"""

    error_code: "AppError"
    data: Any = None
    headers: Optional[dict[str, str]] = None

    def json(self):
        return JSONResponse(
            status_code=self.error_code.value[0], content=self.get_error_object()
        )

    def get_error_object(self):
        return {
            "status_code": self.error_code.value[0],
            "error_message": self.error_code.value[1],
            "error_data": jsonable_encoder(self.data),
        }

    def __post_init__(self):
        detail = self.get_error_object()

        super().__init__(
            status_code=self.error_code.value[0], detail=detail, headers=self.headers
        )

class EnumExtended(Enum):
        def __new__(cls, status_code, message):
            obj = object.__new__(cls)
            obj._value_ = message
            obj.status_code = status_code
            obj.message = message
            return obj

class AppError(EnumExtended):

    SCRAPER_REQUEST_FAILED = (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Failed to fetch data from the target website."
    )

    SCRAPER_PAGE_LOAD_FAILED = (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Failed to load page using Selenium."
    )

    SCRAPER_CONTENT_NOT_FOUND = (
        status.HTTP_404_NOT_FOUND,
        "No content found on the page."
    )

    SCRAPER_SAVE_FAILED = (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Failed to save scraped content."
    )

    SCRAPER_INVALID_URL = (
        status.HTTP_400_BAD_REQUEST,
        "Invalid URL provided."
    )

    SCRAPER_DRIVER_ERROR = (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Chrome WebDriver initialization failed."
    )
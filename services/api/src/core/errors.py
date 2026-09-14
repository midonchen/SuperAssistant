from __future__ import annotations

from fastapi import HTTPException


class ApiException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None, retriable: bool = False):
        super().__init__(status_code=status_code, detail={
            "code": code,
            "message": message,
            "details": details or {},
            "retriable": retriable,
        })

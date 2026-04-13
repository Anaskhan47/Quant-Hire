from fastapi import HTTPException


class ValidationAppError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail={"category": "validation", "message": detail})


class ProviderAppError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=502, detail={"category": "provider", "message": detail})


class NetworkAppError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=503, detail={"category": "network", "message": detail})

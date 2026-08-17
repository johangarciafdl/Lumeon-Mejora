from __future__ import annotations

from flask import jsonify


class AppError(Exception):
    status_code = 400
    code = "application_error"

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


def error_response(error: AppError):
    return jsonify({
        "ok": False,
        "error": str(error),
        "code": error.code,
    }), error.status_code

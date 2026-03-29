from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    code: str
    status_code: int
    message: str

    def __str__(self) -> str:
        return self.message

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    role: str = "viewer"
    active: bool = True

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return self.active

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

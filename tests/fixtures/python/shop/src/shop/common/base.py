from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Protocol


class Auditable(Protocol):
    def created_at(self) -> datetime: ...


class BaseEntity(ABC):
    def __init__(self) -> None:
        self._id: Optional[int] = None
        self._created = datetime.now()

    @abstractmethod
    def is_new(self) -> bool:
        raise NotImplementedError

    class Listener(Protocol):
        def changed(self, entity: BaseEntity) -> None: ...

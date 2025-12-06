from __future__ import annotations

from typing import Dict, Optional
from threading import RLock

from .models import Task


class InMemoryTaskStorage:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = RLock()

    def save(self, task: Task) -> None:
        with self._lock:
            self._tasks[task.id] = task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task: Task) -> None:
        # у нас Task мутируемый, но на будущее оставим метод
        with self._lock:
            self._tasks[task.id] = task


storage = InMemoryTaskStorage()

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal
from threading import Lock
from src.config import MAX_TASK_HISTORY, logger

TaskStatus = Literal["pending", "printing", "done", "failed"]


@dataclass
class PrintTask:
    id: str
    status: TaskStatus
    filename: str
    created_at: float
    updated_at: float
    message: Optional[str] = None


class TaskManager:
    def __init__(self):
        self._tasks: List[PrintTask] = []
        self._lock = Lock()

    def create(self, filename: str) -> PrintTask:
        now = time.time()
        task = PrintTask(
            id=str(uuid.uuid4())[:8],
            status="pending",
            filename=filename,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._tasks.append(task)
            self._truncate()
        logger.info(f"Task {task.id} created for {filename}")
        return task

    def update(self, task_id: str, status: TaskStatus, message: Optional[str] = None) -> Optional[PrintTask]:
        with self._lock:
            for task in self._tasks:
                if task.id == task_id:
                    task.status = status
                    task.message = message
                    task.updated_at = time.time()
                    logger.info(f"Task {task_id} updated to {status}: {message}")
                    return task
        return None

    def list_recent(self, limit: int = 20) -> List[PrintTask]:
        with self._lock:
            return sorted(self._tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    def get(self, task_id: str) -> Optional[PrintTask]:
        with self._lock:
            for task in self._tasks:
                if task.id == task_id:
                    return task
        return None

    def _truncate(self):
        if len(self._tasks) > MAX_TASK_HISTORY:
            self._tasks = self._tasks[-MAX_TASK_HISTORY:]

    def to_dict(self, task: PrintTask) -> Dict:
        return {
            "id": task.id,
            "status": task.status,
            "filename": task.filename,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "message": task.message,
        }


task_manager = TaskManager()

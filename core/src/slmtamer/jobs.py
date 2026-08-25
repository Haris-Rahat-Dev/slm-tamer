import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from . import db


@dataclass
class Job:
    id: str
    kind: str
    status: str
    params: dict
    logs: deque = field(default_factory=lambda: deque(maxlen=5000))
    result: dict | None = None
    error: str | None = None
    cancel_requested: bool = False
    process: object | None = None

    def log(self, line: str) -> None:
        self.logs.append(line.rstrip())

    def snapshot(self, since: int = 0) -> dict:
        logs = list(self.logs)
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "logs": logs[since:],
            "cursor": len(logs),
        }


def _run(job: Job, target: Callable[[Job], dict], manager: "JobManager") -> None:
    try:
        job.status = "running"
        db.upsert_job(job.id, job.kind, job.status, job.params)
        result = target(job)
        if job.cancel_requested:
            job.status = "cancelled"
        else:
            job.status = "done"
            job.result = result
        db.upsert_job(job.id, job.kind, job.status, job.params, job.result, job.error)
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
        job.log(f"error: {exc}")
        db.upsert_job(job.id, job.kind, job.status, job.params, None, job.error)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, kind: str, params: dict, target: Callable[[Job], dict]) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, kind=kind, status="queued", params=params)
        with self._lock:
            self._jobs[job_id] = job
        db.upsert_job(job_id, kind, "queued", params)
        t = threading.Thread(target=_run, args=(job, target, self), daemon=True)
        t.start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def request_cancel(self, job: Job) -> bool:
        job.cancel_requested = True
        proc = job.process
        if proc is not None and proc.poll() is None:
            proc.terminate()
            return True
        return False


manager = JobManager()

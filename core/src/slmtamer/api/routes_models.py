from fastapi import APIRouter, HTTPException

from .. import hub
from ..jobs import manager
from .schemas import DownloadRequest

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/search")
def search(q: str = "", limit: int = 24):
    try:
        return hub.search_models(q, limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"hf search failed: {exc}")


@router.get("/local")
def local():
    return hub.local_models()


@router.post("/download")
def download(req: DownloadRequest):
    existing = hub.resolve_model_path(req.repo_id)
    if existing is not None:
        return {"job_id": None, "path": str(existing), "status": "already_downloaded"}

    def target(job):
        return hub.download_model(job, req.repo_id)

    job = manager.start("download", {"repo_id": req.repo_id}, target)
    return {"job_id": job.id, "status": "queued"}

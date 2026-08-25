from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, datasets
from ..jobs import manager

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


class IngestRequest(BaseModel):
    path: str
    name: str


@router.get("")
def index():
    return datasets.list_datasets()


@router.post("/ingest")
def ingest(req: IngestRequest):
    src = Path(req.path).expanduser().resolve()
    if not src.is_dir():
        raise HTTPException(status_code=400, detail=f"not a directory: {src}")
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in req.name).strip("-")
    if not name:
        raise HTTPException(status_code=400, detail="invalid dataset name")
    out_dir = config.DATASETS_DIR / name

    def target(job):
        job.log(f"crawling {src}")
        stats = datasets.build_corpus(src, out_dir)
        job.log(f"wrote {stats['chunks']} chunks from {stats['files']} files")
        return stats

    job = manager.start("ingest", {"source": str(src), "name": name}, target)
    return {"job_id": job.id, "status": "queued"}

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, db, engines
from ..engines import EngineUnavailable, get_training
from ..hub import resolve_model_path
from ..jobs import manager

router = APIRouter(prefix="/api", tags=["train"])


class TrainRequest(BaseModel):
    model: str
    dataset: str
    preset: str = "balanced"
    engine: str = "auto"
    name: str | None = None
    iters: int | None = None
    batch_size: int | None = None
    learning_rate: float | None = None


@router.get("/engines")
def list_engines():
    return engines.detect()


@router.post("/train")
def train(req: TrainRequest):
    model_path = resolve_model_path(req.model)
    if model_path is None:
        raise HTTPException(status_code=404, detail=f"model not found locally: {req.model}")
    dataset_dir = Path(req.dataset).expanduser().resolve()
    if not (dataset_dir / "train.jsonl").exists():
        raise HTTPException(status_code=400, detail=f"{dataset_dir}/train.jsonl not found")
    try:
        engine = get_training(req.engine)
    except EngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    preset = engines.presets().get(req.preset, engines.presets()["balanced"])
    cfg = {
        "iters": req.iters or preset["iters"],
        "batch_size": req.batch_size or preset["batch_size"],
        "learning_rate": req.learning_rate or preset["learning_rate"],
    }
    params = {
        "model": req.model,
        "model_path": str(model_path),
        "dataset": str(dataset_dir),
        "preset": req.preset,
        "engine": engine.name,
        **cfg,
    }

    adapter_name = (req.name or "").strip()
    if not adapter_name:
        base_label = Path(req.model.rstrip("/")).name.replace("--", "-")
        adapter_name = f"{base_label}+{dataset_dir.name}"

    def target(job):
        result = engine.train(job, model_path, dataset_dir, cfg)
        adapter_dir = Path(result["adapter_path"])
        (adapter_dir / "meta.json").write_text(json.dumps({
            "name": adapter_name,
            "base": req.model,
            "dataset": str(dataset_dir),
            "iters": cfg["iters"],
        }))
        return result

    job = manager.start("train", {**params, "name": adapter_name}, target)
    return {"job_id": job.id, "status": "queued", "config": cfg}


class EvalRequest(BaseModel):
    model: str
    dataset: str
    adapter: str | None = None
    engine: str = "auto"


@router.post("/eval")
def evaluate(req: EvalRequest):
    model_path = resolve_model_path(req.model)
    if model_path is None:
        raise HTTPException(status_code=404, detail=f"model not found locally: {req.model}")
    dataset_dir = Path(req.dataset).expanduser().resolve()
    if not (dataset_dir / "train.jsonl").exists():
        raise HTTPException(status_code=400, detail=f"{dataset_dir}/train.jsonl not found")
    if req.adapter and not Path(req.adapter).is_dir():
        raise HTTPException(status_code=400, detail=f"adapter not found: {req.adapter}")
    try:
        engine = get_training(req.engine)
    except EngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    params = {
        "model": req.model,
        "model_path": str(model_path),
        "dataset": str(dataset_dir),
        "adapter": req.adapter,
        "engine": engine.name,
    }

    def target(job):
        return engine.evaluate(job, model_path, dataset_dir, adapter=req.adapter)

    job = manager.start("eval", params, target)
    return {"job_id": job.id, "status": "queued"}


@router.get("/jobs")
def jobs():
    rows = []
    for row in db.list_job_rows():
        row["params"] = json.loads(row["params"] or "{}")
        if row.get("result"):
            row["result"] = json.loads(row["result"])
        rows.append(row)
    return rows


@router.get("/jobs/{job_id}")
def job_detail(job_id: str):
    row = db.get_job_row(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    row["params"] = json.loads(row["params"] or "{}")
    if row.get("result"):
        row["result"] = json.loads(row["result"])
    return row


@router.post("/jobs/{job_id}/cancel")
def cancel(job_id: str):
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not running in this session")
    stopped = manager.request_cancel(job)
    return {"cancelled": True, "terminated_process": stopped}

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config
from ..engines import EngineUnavailable, get_training
from ..hub import resolve_model_path
from ..jobs import manager
from .routes_chat import adapters as list_adapters

router = APIRouter(prefix="/api/models", tags=["export"])


class MergeRequest(BaseModel):
    model: str
    adapter: str
    output_name: str | None = None
    engine: str = "auto"


class ExportGgufRequest(BaseModel):
    model: str
    adapter: str | None = None
    output_name: str
    register_ollama: bool = False


@router.post("/merge")
def merge(req: MergeRequest):
    model_path = resolve_model_path(req.model)
    if model_path is None:
        raise HTTPException(status_code=404, detail=f"model not found locally: {req.model}")
    if not (Path(req.adapter) / "adapters.safetensors").exists():
        known = [a["id"] for a in list_adapters()]
        raise HTTPException(status_code=400, detail=f"adapter not found; known: {known}")
    try:
        engine = get_training(req.engine)
    except EngineUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    name = req.output_name or f"{Path(req.model).name}-tuned"
    save_path = str(config.MODELS_DIR / name.replace("/", "--"))

    def target(job):
        return engine.fuse(job, str(model_path), req.adapter, save_path)

    job = manager.start("merge", {
        "model": req.model,
        "adapter": req.adapter,
        "output": save_path,
        "engine": engine.name,
    }, target)
    return {"job_id": job.id, "status": "queued"}


@router.get("/export-toolchain")
def export_toolchain():
    from .. import export_gguf as exporter
    return exporter.check_toolchain()


@router.post("/export-gguf")
def export_gguf(req: ExportGgufRequest):
    model_path = resolve_model_path(req.model)
    if model_path is None:
        raise HTTPException(status_code=404, detail=f"model not found locally: {req.model}")
    if req.adapter and not Path(req.adapter).is_dir():
        raise HTTPException(status_code=400, detail=f"adapter not found: {req.adapter}")

    from .. import export_gguf as exporter
    out_dir = config.HOME / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(out_dir / f"{req.output_name}.gguf")
    ollama_name = req.output_name if req.register_ollama else None

    def target(job):
        return exporter.export_gguf(job, str(model_path), req.adapter, out_path, ollama_name)

    job = manager.start("export-gguf", {
        "model": req.model,
        "adapter": req.adapter,
        "output": out_path,
        "register_ollama": req.register_ollama,
    }, target)
    return {"job_id": job.id, "status": "queued", "output": out_path}

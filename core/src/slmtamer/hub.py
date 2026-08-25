from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

from . import config


def search_models(query: str, limit: int = 24) -> list[dict]:
    api = HfApi()
    out = []
    for info in api.list_models(
        search=query or None,
        pipeline_tag="text-generation",
        sort="downloads",
        limit=limit,
        expand=["safetensors", "downloads", "likes", "library_name"],
    ):
        params_total = None
        st = getattr(info, "safetensors", None)
        if isinstance(st, dict):
            params_total = st.get("total")
        out.append(
            {
                "repo_id": info.id,
                "downloads": info.downloads,
                "likes": info.likes,
                "params": params_total,
                "library": info.library_name,
                "last_modified": str(info.last_modified) if info.last_modified else None,
            }
        )
    return out


def download_model(job, repo_id: str) -> dict:
    job.log(f"downloading {repo_id}")
    path = snapshot_download(
        repo_id,
        cache_dir=str(config.MODELS_DIR),
        ignore_patterns=["*.gguf", "*.pth", "*.onnx*", "*.msgpack", "*.h5", "*.tflite"],
        max_workers=4,
    )
    job.log(f"done -> {path}")
    return {"path": path}


def local_models() -> list[dict]:
    results = []
    if not config.MODELS_DIR.exists():
        return results
    for entry in sorted(config.MODELS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        candidates = []
        if (entry / "config.json").exists():
            candidates = [entry]
        else:
            snapshots = entry / "snapshots"
            if snapshots.is_dir():
                candidates = [s for s in sorted(snapshots.iterdir()) if (s / "config.json").exists()]
        for snap in candidates:
            size = sum(f.stat().st_size for f in snap.rglob("*") if f.is_file())
            results.append(
                {
                    "repo_id": "/".join(entry.name.split("--")[1:]) if "--" in entry.name else entry.name,
                    "path": str(snap),
                    "size_bytes": size,
                }
            )
            break
    return results


def resolve_model_path(name: str) -> Path | None:
    candidate = Path(name).expanduser()
    if candidate.is_dir() and (candidate / "config.json").exists():
        return candidate
    flat = name.replace("/", "--")
    for candidate in (
        config.MODELS_DIR / name,
        config.MODELS_DIR / flat,
        config.MODELS_DIR / flat / "snapshots",
    ):
        if candidate.is_dir():
            if (candidate / "config.json").exists():
                return candidate
            for snap in sorted(candidate.iterdir()):
                if (snap / "config.json").exists():
                    return snap
    return None

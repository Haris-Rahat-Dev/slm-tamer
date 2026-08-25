from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import config
from ..engines import EngineUnavailable, get_inference

router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    adapter: str | None = None
    engine: str = "auto"
    messages: list[Message]
    max_tokens: int = 256
    temperature: float = 0.7


@router.get("/adapters")
def adapters():
    out = []
    if config.ADAPTERS_DIR.exists():
        for entry in sorted(config.ADAPTERS_DIR.iterdir()):
            if (entry / "adapters.safetensors").exists():
                out.append({"id": entry.name, "path": str(entry)})
    return out


def _resolve_engine(req: ChatRequest):
    if req.adapter:
        try:
            engine = get_inference(req.engine if req.engine != "auto" else None)
        except EngineUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        if not engine.supports_adapter():
            raise HTTPException(
                status_code=400,
                detail=f"engine '{engine.name}' does not support LoRA adapters; merge first or use mlx",
            )
    else:
        try:
            engine = get_inference(req.engine)
        except EngineUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
    return engine


@router.post("/chat")
def chat(req: ChatRequest):
    engine = _resolve_engine(req)
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        reply = engine.generate(messages=messages, adapter=req.adapter, max_tokens=req.max_tokens,
                                temperature=req.temperature, model=req.model)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"generation failed: {exc}")
    return {"reply": reply, "engine": engine.name}


def _sse(payload: dict) -> str:
    import json
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    engine = _resolve_engine(req)
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    def gen() -> Iterator[str]:
        yield _sse({"start": True, "engine": engine.name})
        try:
            for delta in engine.generate_stream(
                model=req.model,
                adapter=req.adapter,
                messages=messages,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
            ):
                yield _sse({"delta": delta})
            yield _sse({"done": True})
        except FileNotFoundError as exc:
            yield _sse({"error": str(exc)})
        except Exception as exc:
            yield _sse({"error": f"generation failed: {exc}"})

    return StreamingResponse(gen(), media_type="text/event-stream")

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import config, db
from ..engines import EngineUnavailable, get_inference
from ..jobs import manager

router = APIRouter(prefix="/api/eval-sets", tags=["qa-eval"])


class QAItem(BaseModel):
    question: str
    answer: str


class EvalSetRequest(BaseModel):
    name: str
    items: list[QAItem]


class RunEvalRequest(BaseModel):
    model: str
    adapter: str | None = None
    engine: str = "auto"
    eval_set: str
    max_tokens: int = 96


def _set_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name).strip("-")
    if not safe:
        raise HTTPException(status_code=400, detail="invalid eval set name")
    return config.EVALS_DIR / f"{safe}.jsonl"


@router.get("")
def index():
    out = []
    if config.EVALS_DIR.exists():
        for entry in sorted(config.EVALS_DIR.glob("*.jsonl")):
            lines = [l for l in entry.read_text().splitlines() if l.strip()]
            out.append({"name": entry.stem, "items": len(lines)})
    return out


@router.post("")
def create(req: EvalSetRequest):
    path = _set_path(req.name)
    with path.open("w") as f:
        for item in req.items:
            f.write(json.dumps({"question": item.question, "answer": item.answer}) + "\n")
    return {"name": path.stem, "items": len(req.items)}


@router.get("/{name}")
def show(name: str):
    path = _set_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="eval set not found")
    items = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return {"name": path.stem, "items": items}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text)


def _run_eval(job, req: RunEvalRequest) -> dict:
    try:
        engine = get_inference(req.engine if not req.adapter else None)
    except EngineUnavailable as exc:
        raise RuntimeError(str(exc))
    if req.adapter and not engine.supports_adapter():
        raise RuntimeError(f"engine '{engine.name}' does not support adapters; merge first")
    path = _set_path(req.eval_set)
    items = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    job.log(f"running {len(items)} questions on {req.model} via {engine.name}")

    correct = 0
    results = []
    for i, item in enumerate(items):
        reply = engine.generate(
            model=req.model,
            adapter=req.adapter,
            messages=[{"role": "user", "content": item["question"]}],
            max_tokens=req.max_tokens,
            temperature=0.0,
        )
        pred_norm = _normalize(reply)
        gold_norm = _normalize(item["answer"])
        ok = gold_norm in pred_norm
        correct += ok
        verdict = "PASS" if ok else "FAIL"
        job.log(f"[{i + 1}/{len(items)}] {verdict} q: {item['question'][:80]} | expected: {item['answer'][:60]} | got: {reply.strip()[:60]}")
        results.append({
            "question": item["question"],
            "expected": item["answer"],
            "got": reply.strip(),
            "correct": ok,
        })

    score = round(correct / len(items), 3) if items else 0.0
    job.log(f"score: {correct}/{len(items)} ({score})")
    return {"score": score, "correct": correct, "total": len(items), "results": results}


@router.post("/run")
def run(req: RunEvalRequest):
    path = _set_path(req.eval_set)
    if not path.exists():
        raise HTTPException(status_code=404, detail="eval set not found")
    job = manager.start("qa-eval", req.model_dump(), lambda j: _run_eval(j, req))
    return {"job_id": job.id, "status": "queued"}

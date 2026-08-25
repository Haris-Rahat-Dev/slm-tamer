from .base import InferenceEngine, TrainingEngine
from .cuda_engine import cuda_training
from .mlx_engine import mlx_inference, mlx_training
from .ollama_engine import ollama

INFERENCE_ENGINES: list[InferenceEngine] = [mlx_inference, ollama]
TRAINING_ENGINES: list[TrainingEngine] = [mlx_training, cuda_training]

_PRESETS: dict[str, dict] = {
    "fast": {"iters": 200, "batch_size": 2, "learning_rate": 1e-4},
    "balanced": {"iters": 600, "batch_size": 4, "learning_rate": 5e-5},
    "deep": {"iters": 2000, "batch_size": 4, "learning_rate": 2e-5},
}


class EngineUnavailable(RuntimeError):
    pass


def presets() -> dict[str, dict]:
    return _PRESETS


def detect() -> dict:
    return {
        "inference": [
            {"name": e.name, "available": e.available(), "adapter_support": e.supports_adapter()}
            for e in INFERENCE_ENGINES
        ],
        "training": [{"name": e.name, "available": e.available()} for e in TRAINING_ENGINES],
        "presets": _PRESETS,
    }


def get_inference(name: str | None = None) -> InferenceEngine:
    if name and name != "auto":
        for engine in INFERENCE_ENGINES:
            if engine.name == name and engine.available():
                return engine
        raise EngineUnavailable(f"inference engine unavailable: {name}")
    for engine in INFERENCE_ENGINES:
        if engine.available():
            return engine
    raise EngineUnavailable("no inference engine available")


def get_training(name: str | None = None) -> TrainingEngine:
    if name and name != "auto":
        for engine in TRAINING_ENGINES:
            if engine.name == name and engine.available():
                return engine
        raise EngineUnavailable(f"training engine unavailable: {name}")
    for engine in TRAINING_ENGINES:
        if engine.available():
            return engine
    raise EngineUnavailable("no training engine available")

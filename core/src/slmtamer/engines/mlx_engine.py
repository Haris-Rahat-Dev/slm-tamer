import json
import subprocess
import sys
import threading
from pathlib import Path

import mlx_lm
from mlx_lm.sample_utils import make_sampler

from .. import config
from ..hub import resolve_model_path


def _prepare_dataset(dataset_dir: Path) -> Path:
    train = dataset_dir / "train.jsonl"
    if not train.exists():
        raise FileNotFoundError(f"{train} not found")
    valid = dataset_dir / "valid.jsonl"
    if not valid.exists():
        lines = [l for l in train.read_text().splitlines() if l.strip()]
        holdout = min(50, max(2, len(lines) // 10))
        valid.write_text("\n".join(lines[:holdout]) + "\n")
    for line_file in (train, valid):
        for i, l in enumerate(line_file.read_text().splitlines()):
            if l.strip():
                json.loads(l)
    return dataset_dir

_lock = threading.Lock()
_cache: dict[tuple[str, str], tuple[object, object]] = {}


def _load(model_ref: str, adapter: str | None):
    key = (model_ref, adapter or "")
    with _lock:
        if key in _cache:
            return _cache[key]
        path = resolve_model_path(model_ref)
        if path is None:
            raise FileNotFoundError(f"model not found locally: {model_ref}")
        model, tokenizer = mlx_lm.load(str(path), adapter_path=adapter)
        if len(_cache) > 3:
            _cache.clear()
        _cache[key] = (model, tokenizer)
        return model, tokenizer


class MLXInference:
    name = "mlx"

    def available(self) -> bool:
        try:
            import mlx.core  # noqa: F401
            return True
        except Exception:
            return False

    def supports_adapter(self) -> bool:
        return True

    def _prompt(self, adapter, model, messages):
        mlx_model, tokenizer = _load(model, adapter)
        try:
            prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        except Exception:
            prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        return mlx_model, tokenizer, prompt

    def generate(self, model, adapter, messages, max_tokens, temperature) -> str:
        mlx_model, tokenizer, prompt = self._prompt(adapter, model, messages)
        return mlx_lm.generate(
            mlx_model,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=make_sampler(temp=temperature),
            verbose=False,
        )

    def generate_stream(self, model, adapter, messages, max_tokens, temperature):
        from mlx_lm.generate import stream_generate

        mlx_model, tokenizer, prompt = self._prompt(adapter, model, messages)
        for resp in stream_generate(
            mlx_model,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            sampler=make_sampler(temp=temperature),
        ):
            yield resp.text


class MLXTraining:
    name = "mlx"

    def available(self) -> bool:
        return MLXInference().available()

    def supports_adapter(self) -> bool:
        return True

    def train(self, job, model_path, dataset_dir, cfg) -> dict:
        adapter_dir = Path(config.ADAPTERS_DIR) / job.id
        adapter_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, "-m", "mlx_lm", "lora",
            "--train",
            "--model", str(model_path),
            "--data", str(_prepare_dataset(dataset_dir)),
            "--fine-tune-type", "lora",
            "--adapter-path", str(adapter_dir),
            "--iters", str(cfg["iters"]),
            "--batch-size", str(cfg["batch_size"]),
            "--learning-rate", str(cfg["learning_rate"]),
        ]
        job.log(f"run: {' '.join(cmd)}")
        proc = self._stream(job, cmd)
        if job.cancel_requested:
            raise RuntimeError("cancelled")
        if proc != 0:
            raise RuntimeError(f"mlx_lm lora exited with code {proc}")
        return {"adapter_path": str(adapter_dir)}

    def evaluate(self, job, model_path, dataset_dir, adapter: str | None = None) -> dict:
        dataset_dir = _prepare_dataset(dataset_dir)
        test = dataset_dir / "test.jsonl"
        if not test.exists():
            valid = dataset_dir / "valid.jsonl"
            test.write_text(valid.read_text())
        cmd = [
            sys.executable, "-m", "mlx_lm", "lora",
            "--test",
            "--model", str(model_path),
            "--data", str(dataset_dir),
        ]
        if adapter:
            cmd += ["--adapter-path", str(adapter)]
        job.log(f"run: {' '.join(cmd)}")
        code = self._stream(job, cmd)
        if code != 0:
            raise RuntimeError(f"mlx_lm lora --test exited with code {code}")
        loss = None
        for line in job.logs:
            if "loss" in line.lower() and any(c.isdigit() for c in line):
                loss = line.strip()
        return {"test_loss": loss}

    def fuse(self, job, model_path, adapter, save_path) -> dict:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, "-m", "mlx_lm", "fuse",
            "--model", str(model_path),
            "--adapter-path", adapter,
            "--save-path", save_path,
        ]
        job.log(f"run: {' '.join(cmd)}")
        code = self._stream(job, cmd)
        if code != 0:
            raise RuntimeError(f"mlx_lm fuse exited with code {code}")
        return {"merged_path": save_path}

    def _stream(self, job, cmd: list[str]) -> int:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        job.process = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            job.log(line.rstrip())
            if job.cancel_requested and proc.poll() is None:
                proc.terminate()
                break
        code = proc.wait()
        job.process = None
        return code


mlx_inference = MLXInference()
mlx_training = MLXTraining()

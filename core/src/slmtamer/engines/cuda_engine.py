import subprocess
import sys
from pathlib import Path

from .. import config

_SCRIPT = Path(__file__).parent / "train_lora.py"
_FUSE_EVAL = Path(__file__).parent / "fuse_eval.py"


class CUDATraining:
    name = "cuda"

    def available(self) -> bool:
        if sys.platform != "linux":
            return False
        try:
            import torch  # noqa: F401
            return torch.cuda.is_available()
        except Exception:
            return False

    def train(self, job, model_path, dataset_dir, cfg) -> dict:
        adapter_dir = config.ADAPTERS_DIR / job.id
        adapter_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, str(_SCRIPT),
            "--model", str(model_path),
            "--data", str(dataset_dir),
            "--output", str(adapter_dir),
            "--iters", str(cfg["iters"]),
            "--batch-size", str(cfg["batch_size"]),
            "--learning-rate", str(cfg["learning_rate"]),
        ]
        job.log(f"run: {' '.join(cmd)}")
        code = self._stream(job, cmd)
        if job.cancel_requested:
            raise RuntimeError("cancelled")
        if code != 0:
            raise RuntimeError(f"cuda trainer exited with code {code}")
        return {"adapter_path": str(adapter_dir)}

    def evaluate(self, job, model_path, dataset_dir, adapter: str | None = None) -> dict:
        cmd = [
            sys.executable, str(_FUSE_EVAL), "eval",
            "--model", str(model_path),
            "--data", str(dataset_dir),
        ]
        if adapter:
            cmd += ["--adapter", str(adapter)]
        job.log(f"run: {' '.join(cmd)}")
        code = self._stream(job, cmd)
        if code != 0:
            raise RuntimeError(f"cuda eval exited with code {code}")
        loss = None
        for line in job.logs:
            if "loss" in line.lower() and any(c.isdigit() for c in line):
                loss = line.strip()
        return {"test_loss": loss}

    def fuse(self, job, model_path: str, adapter: str, save_path: str) -> dict:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable, str(_FUSE_EVAL), "fuse",
            "--model", model_path,
            "--adapter", adapter,
            "--output", save_path,
        ]
        job.log(f"run: {' '.join(cmd)}")
        code = self._stream(job, cmd)
        if code != 0:
            raise RuntimeError(f"cuda fuse exited with code {code}")
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


cuda_training = CUDATraining()

import subprocess
import sys
from pathlib import Path

from . import config


def _stream(job, cmd: list[str]) -> int:
    job.log(f"run: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    job.process = proc
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if "byte/s" in line or not line:
            continue
        job.log(line)
        if job.cancel_requested and proc.poll() is None:
            proc.terminate()
            break
    code = proc.wait()
    job.process = None
    return code


def check_toolchain() -> dict:
    return {
        "converter": (config.LLAMA_CPP_HOME / "convert_hf_to_gguf.py").exists(),
        "convert_python": config.CONVERT_PYTHON.exists(),
        "ollama": _which("ollama") is not None,
    }


def _which(name: str) -> str | None:
    for d in ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"):
        p = Path(d) / name
        if p.exists():
            return str(p)
    out = subprocess.run(["which", name], capture_output=True, text=True)
    return out.stdout.strip() or None


def export_gguf(job, model_path: str, adapter: str | None, out_path: str,
                ollama_name: str | None = None) -> dict:
    converter = config.LLAMA_CPP_HOME / "convert_hf_to_gguf.py"
    if not converter.exists():
        raise RuntimeError(
            f"convert_hf_to_gguf.py not found at {config.LLAMA_CPP_HOME}; "
            "clone llama.cpp or set LLAMA_CPP_HOME"
        )
    if not config.CONVERT_PYTHON.exists():
        raise RuntimeError(
            f"converter python not found at {config.CONVERT_PYTHON}; "
            "create a venv with gguf+torch+transformers or set SLM_TAMER_CONVERT_PYTHON"
        )

    work = Path(out_path).parent / f".export-{job.id}"
    work.mkdir(parents=True, exist_ok=True)

    deq_cmd = [
        sys.executable, "-m", "mlx_lm", "fuse",
        "--model", model_path,
    ]
    if adapter:
        deq_cmd += ["--adapter-path", adapter]
    deq_cmd += [
        "--dequantize",
        "--save-path", str(work / "dequantized"),
    ]
    code = _stream(job, deq_cmd)
    if code != 0:
        raise RuntimeError(f"dequantize-fuse exited with code {code}")

    conv_cmd = [
        str(config.CONVERT_PYTHON), str(converter),
        str(work / "dequantized"),
        "--outfile", out_path,
        "--outtype", "q8_0",
    ]
    code = _stream(job, conv_cmd)
    if code != 0:
        raise RuntimeError(f"gguf conversion exited with code {code}")
    if not Path(out_path).exists():
        raise RuntimeError("conversion finished but output file missing")

    result = {"gguf_path": out_path}

    if ollama_name:
        ollama_bin = _which("ollama")
        if ollama_bin is None:
            raise RuntimeError("ollama CLI not found; gguf exported but not registered")
        modelfile = work / "Modelfile"
        modelfile.write_text(f"FROM {Path(out_path).resolve()}\n")
        code = _stream(job, [ollama_bin, "create", ollama_name, "-f", str(modelfile)])
        if code != 0:
            raise RuntimeError(f"ollama create exited with code {code}")
        result["ollama_model"] = ollama_name

    import shutil
    shutil.rmtree(work, ignore_errors=True)
    return result

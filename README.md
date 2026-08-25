# slm-tamer

Tame small language models for your domain. Pick a base SLM from Hugging Face,
feed it your project's stack, train a LoRA adapter locally, chat with the result.

Full-precision domain-specialized small models instead of quantized generalists.

## Architecture

- `core/` — Python daemon (FastAPI). Model hub browsing/download (huggingface_hub),
  job manager, pluggable training engines (MLX on Apple Silicon, CUDA planned).
- `app/` — Tauri v2 + React desktop shell talking to the daemon over HTTP/WS.

Data lives in `~/.slm-tamer/` (override with `SLM_TAMER_HOME`): models, adapters,
datasets, logs, sqlite db.

## Quickstart

```sh
make core-install    # uv sync into core/.venv
make app-install     # pnpm install

make core-dev        # terminal 1: daemon on http://127.0.0.1:8765
make app-dev         # terminal 2: tauri dev window
```

Headless: `cd core && uv run python scripts/daemon_start.py` (logs to `/tmp/slm-tamer-core.log`).

## Train flow (MVP)

1. Models page → search HF, download a base (e.g. `mlx-community/Qwen3-0.6B-Instruct-2507-4bit`)
2. Data page → point at a git repo, ingest: crawls code + docs, chunks into
   `~/.slm-tamer/datasets/<name>/train.jsonl`
3. Train page → pick base + dataset + preset → start (or hand-write `train.jsonl`
   in [mlx-lm format](https://github.com/ml-explore/mlx-lm))
4. Jobs page → live loss stream; adapter lands in `~/.slm-tamer/adapters/<job-id>/`
5. Chat page → streaming tokens from base or adapter-tuned model (MLX in-process
   or Ollama backend, picked per-request)
6. Merge via API (`POST /api/models/merge`) bakes the adapter into a standalone
   model that shows up in your local list
7. Eval (`POST /api/eval`) reports held-out loss/perplexity; golden Q&A sets
   (`POST /api/eval-sets` + `/run`) score answers against gold truth
8. GGUF export (`POST /api/models/export-gguf`) dequantize-fuses, converts, and
   optionally registers the result in Ollama — train on Mac, serve anywhere

## GGUF export setup

```sh
brew install llama.cpp                      # CLI tools
git clone --depth 1 https://github.com/ggml-org/llama.cpp ~/tools/llama.cpp
uv venv ~/.slm-tamer/tools/convert-venv --python 3.13
uv pip install --python ~/.slm-tamer/tools/convert-venv/bin/python \
  gguf numpy sentencepiece transformers torch
```

Paths are configurable via `LLAMA_CPP_HOME` and `SLM_TAMER_CONVERT_PYTHON`.
Check readiness at `GET /api/models/export-toolchain`.

## Engines

Inference and training are pluggable: `core/src/slmtamer/engines/`. Each engine
implements the protocols in `base.py` and registers in `__init__.py`.
Shipped: MLX (inference + LoRA training + fuse + eval), Ollama (streaming inference),
CUDA (training/fuse/eval for Linux/NVIDIA, inert on Mac).

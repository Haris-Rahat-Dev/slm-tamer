import json
from pathlib import Path

from . import config

CODE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".c", ".h", ".cpp",
    ".hpp", ".java", ".kt", ".swift", ".rb", ".php", ".cs", ".sh", ".sql",
    ".toml", ".yaml", ".yml", ".json", ".css", ".html",
}
DOC_EXTS = {".md", ".txt", ".rst"}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    "target", ".next", ".cache", "coverage", ".idea", ".vscode", "vendor",
}
CHUNK_CHARS = 1600
MAX_FILE_BYTES = 200_000


def _iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        if path.suffix.lower() not in CODE_EXTS | DOC_EXTS:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        yield path


def _chunk(text: str, source: str):
    lines = text.splitlines()
    buf: list[str] = []
    size = 0

    def flush():
        nonlocal buf, size
        if buf:
            body = "\n".join(buf).strip()
            if len(body) > 120:
                yield {"text": f"# source: {source}\n{body}" if not source.endswith(".md") else f"source: {source}\n\n{body}"}
        buf = []
        size = 0

    for line in lines:
        buf.append(line)
        size += len(line) + 1
        if size >= CHUNK_CHARS:
            yield from flush()
    yield from flush()


def build_corpus(src_dir: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / "train.jsonl"
    files = chunks = 0
    with train_path.open("w") as f:
        for path in _iter_files(src_dir):
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            rel = str(path.relative_to(src_dir))
            files += 1
            for chunk in _chunk(text, rel):
                f.write(json.dumps(chunk) + "\n")
                chunks += 1
    return {"files": files, "chunks": chunks, "train": str(train_path)}


def list_datasets() -> list[dict]:
    out = []
    if not config.DATASETS_DIR.exists():
        return out
    for entry in sorted(config.DATASETS_DIR.iterdir()):
        train = entry / "train.jsonl"
        if entry.is_dir() and train.exists():
            lines = sum(1 for l in train.open() if l.strip())
            out.append({"name": entry.name, "path": str(entry), "examples": lines})
    return out

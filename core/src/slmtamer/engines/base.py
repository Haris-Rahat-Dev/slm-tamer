from typing import Iterator, Protocol


class InferenceEngine(Protocol):
    name: str

    def available(self) -> bool: ...

    def supports_adapter(self) -> bool: ...

    def generate(
        self,
        model: str,
        adapter: str | None,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> str: ...

    def generate_stream(
        self,
        model: str,
        adapter: str | None,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> Iterator[str]: ...


class TrainingEngine(Protocol):
    name: str

    def available(self) -> bool: ...

    def train(self, job, model_path, dataset_dir, cfg) -> dict: ...

    def evaluate(self, job, model_path, dataset_dir, adapter: str | None = None) -> dict: ...

    def fuse(self, job, model_path: str, adapter: str, save_path: str) -> dict: ...

import json

import httpx

BASE = "http://127.0.0.1:11434"


class OllamaInference:
    name = "ollama"

    def available(self) -> bool:
        try:
            return httpx.get(f"{BASE}/api/tags", timeout=1.0).status_code == 200
        except Exception:
            return False

    def supports_adapter(self) -> bool:
        return False

    def _payload(self, model, messages, max_tokens, temperature, stream: bool) -> dict:
        return {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }

    def generate(self, model, adapter, messages, max_tokens, temperature) -> str:
        res = httpx.post(
            f"{BASE}/api/chat",
            json=self._payload(model, messages, max_tokens, temperature, stream=False),
            timeout=600,
        )
        res.raise_for_status()
        return res.json()["message"]["content"]

    def generate_stream(self, model, adapter, messages, max_tokens, temperature):
        with httpx.stream(
            "POST",
            f"{BASE}/api/chat",
            json=self._payload(model, messages, max_tokens, temperature, stream=True),
            timeout=600,
        ) as res:
            res.raise_for_status()
            for line in res.iter_lines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                delta = obj.get("message", {}).get("content", "")
                if delta:
                    yield delta
                if obj.get("done"):
                    break


ollama = OllamaInference()

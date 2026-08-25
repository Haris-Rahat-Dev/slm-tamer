import { useEffect, useRef, useState } from "react";
import { API, api, type LocalModel } from "../lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [models, setModels] = useState<LocalModel[]>([]);
  const [adapters, setAdapters] = useState<{ id: string; path: string }[]>([]);
  const [inferenceEngines, setInferenceEngines] = useState<{ name: string; available: boolean; adapter_support: boolean }[]>([]);
  const [engine, setEngine] = useState("auto");
  const [model, setModel] = useState("");
  const [adapter, setAdapter] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<LocalModel[]>("/api/models/local")
      .then((ms) => {
        setModels(ms);
        if (ms.length > 0) setModel(ms[0].path);
      })
      .catch(() => {});
    api<{ id: string; path: string }[]>("/api/adapters").then(setAdapters).catch(() => {});
    api<{ inference: { name: string; available: boolean; adapter_support: boolean }[] }>("/api/engines")
      .then((e) => setInferenceEngines(e.inference))
      .catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || busy || !model) return;
    setBusy(true);
    setError(null);
    const next: Msg[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setMessages([...next, { role: "assistant", content: "" }]);
    try {
      const res = await fetch(`${API}/api/chat/stream`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          model,
          adapter: adapter || null,
          engine,
          messages: next.slice(-10),
          max_tokens: 400,
        }),
      });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `${res.status}`);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let reply = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const evt of events) {
          if (!evt.startsWith("data: ")) continue;
          const payload = JSON.parse(evt.slice(6));
          if (payload.error) throw new Error(payload.error);
          if (payload.delta) {
            reply += payload.delta;
            setMessages([...next, { role: "assistant", content: reply }]);
          }
        }
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="row chat-config">
        <select value={engine} onChange={(e) => setEngine(e.target.value)}>
          <option value="auto">engine: auto</option>
          {inferenceEngines.map((e) => (
            <option key={e.name} value={e.name} disabled={!e.available}>
              engine: {e.name}{!e.available && " (offline)"}
            </option>
          ))}
        </select>
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {models.map((m) => (
            <option key={m.path} value={m.path}>
              {m.repo_id}
            </option>
          ))}
        </select>
        <select value={adapter} onChange={(e) => setAdapter(e.target.value)}>
          <option value="">no adapter (base)</option>
          {adapters.map((a) => (
            <option key={a.id} value={a.path}>
              adapter {a.id}
            </option>
          ))}
        </select>
      </div>

      <div className="thread">
        {messages.length === 0 && (
          <p className="muted">Pick a base and optionally an adapter, then say something.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
        {busy && messages[messages.length - 1]?.content === "" && (
          <div className="bubble assistant muted">thinking…</div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="message…"
          disabled={busy}
        />
        <button type="submit" disabled={busy}>
          Send
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

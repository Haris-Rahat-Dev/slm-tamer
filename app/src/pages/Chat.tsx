import { useEffect, useRef, useState } from "react";
import { API, api, type LocalModel } from "../lib/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [models, setModels] = useState<LocalModel[]>([]);
  const [adapters, setAdapters] = useState<{ id: string; path: string; name: string; base: string | null }[]>([]);
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
    api<{ id: string; path: string; name: string; base: string | null }[]>("/api/adapters").then(setAdapters).catch(() => {});
    api<{ inference: { name: string; available: boolean; adapter_support: boolean }[] }>("/api/engines")
      .then((e) => setInferenceEngines(e.inference))
      .catch(() => {});
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const a = adapters.find((x) => x.path === adapter);
    if (a?.base && a.base !== model) setAdapter("");
  }, [model, adapters, adapter]);

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
          {adapters.map((a) => {
            const mismatched = !!a.base && a.base !== model;
            return (
              <option key={a.id} value={a.path} disabled={mismatched}>
                {a.name}{mismatched ? " (trained on a different base)" : ""}
              </option>
            );
          })}
        </select>
      </div>

      <div className="thread">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-title">Say something.</div>
            <p className="muted">
              Pick a base, optionally attach a trained adapter, and talk to it.
            </p>
            <div className="suggestions">
              {[
                "What is slm-tamer?",
                "Explain LoRA adapters in one paragraph.",
                "Write a haiku about small models.",
              ].map((s) => (
                <button key={s} onClick={() => setInput(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          </div>
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
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message…"
          disabled={busy}
        />
        <button className="primary" type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

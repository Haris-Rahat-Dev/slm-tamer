import { useEffect, useState } from "react";
import { api, type LocalModel } from "../lib/api";

interface EvalSet {
  name: string;
  items: number;
}

export default function Evaluate({ onStarted }: { onStarted: (jobId: string) => void }) {
  const [models, setModels] = useState<LocalModel[]>([]);
  const [model, setModel] = useState("");
  const [adapters, setAdapters] = useState<{ id: string; path: string; name: string }[]>([]);
  const [engines, setEngines] = useState<{ name: string; available: boolean }[]>([]);
  const [engine, setEngine] = useState("auto");

  const [dataset, setDataset] = useState("");
  const [lossAdapter, setLossAdapter] = useState("");

  const [sets, setSets] = useState<EvalSet[]>([]);
  const [setName, setSetName] = useState("");
  const [setJson, setSetJson] = useState(
    '[\n  {"question": "...", "answer": "..."}\n]'
  );
  const [runSet, setRunSet] = useState("");
  const [qaAdapter, setQaAdapter] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    api<LocalModel[]>("/api/models/local")
      .then((ms) => {
        setModels(ms);
        if (!model && ms.length > 0) setModel(ms[0].path);
      })
      .catch(() => {});
    api<{ id: string; path: string; name: string }[]>("/api/adapters").then(setAdapters).catch(() => {});
    api<{ inference: { name: string; available: boolean }[] }>("/api/engines")
      .then((e) => setEngines(e.inference))
      .catch(() => {});
    api<EvalSet[]>("/api/eval-sets").then(setSets).catch(() => {});
  }

  useEffect(() => {
    refresh();
  }, []);

  async function runLossEval() {
    setError(null);
    try {
      const res = await api<{ job_id: string }>("/api/eval", {
        method: "POST",
        body: JSON.stringify({
          model,
          dataset,
          adapter: lossAdapter || null,
          engine: "auto",
        }),
      });
      onStarted(res.job_id);
    } catch (e) {
      setError(String(e));
    }
  }

  async function createSet() {
    setError(null);
    try {
      const items = JSON.parse(setJson);
      await api("/api/eval-sets", {
        method: "POST",
        body: JSON.stringify({ name: setName, items }),
      });
      setSetName("");
      refresh();
    } catch (e) {
      setError(`invalid set: ${e}`);
    }
  }

  async function runQa() {
    setError(null);
    try {
      const res = await api<{ job_id: string }>("/api/eval-sets/run", {
        method: "POST",
        body: JSON.stringify({
          model,
          adapter: qaAdapter || null,
          engine,
          eval_set: runSet,
          max_tokens: 96,
        }),
      });
      onStarted(res.job_id);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h2>Model under test</h2>
      <div className="row">
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {models.map((m) => (
            <option key={m.path} value={m.path}>
              {m.repo_id}
            </option>
          ))}
        </select>
        <select value={engine} onChange={(e) => setEngine(e.target.value)}>
          <option value="auto">engine: auto</option>
          {engines.map((e) => (
            <option key={e.name} value={e.name} disabled={!e.available}>
              {e.name}{!e.available && " (offline)"}
            </option>
          ))}
        </select>
      </div>

      <h2>Held-out loss</h2>
      <p className="muted">Perplexity-style check via the training engine (MLX/CUDA).</p>
      <div className="row">
        <select value={lossAdapter} onChange={(e) => setLossAdapter(e.target.value)}>
          <option value="">no adapter (base)</option>
          {adapters.map((a) => (
            <option key={a.id} value={a.path}>
              {a.name}
            </option>
          ))}
        </select>
        <input
          className="mono"
          value={dataset}
          onChange={(e) => setDataset(e.target.value)}
          placeholder="/path/to/dataset (train.jsonl)"
        />
        <button className="primary" onClick={runLossEval} disabled={!model || !dataset}>
          Run loss eval
        </button>
      </div>

      <h2>Golden Q&amp;A sets</h2>
      <table>
        <thead>
          <tr>
            <th>Set</th>
            <th>Items</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sets.map((s) => (
            <tr key={s.name}>
              <td>{s.name}</td>
              <td>{s.items}</td>
              <td>
                <button
                  onClick={() => {
                    setRunSet(s.name);
                    runQaWith(s.name);
                  }}
                  disabled={!model}
                >
                  Run
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>New set</h3>
      <div className="row">
        <input
          value={setName}
          onChange={(e) => setSetName(e.target.value)}
          placeholder="set name"
        />
        <button onClick={createSet} disabled={!setName || !setJson.trim()}>
          Save
        </button>
      </div>
      <textarea
        className="mono json-area"
        value={setJson}
        onChange={(e) => setSetJson(e.target.value)}
        rows={6}
      />

      <h2>Run Q&amp;A</h2>
      <div className="row">
        <select value={runSet} onChange={(e) => setRunSet(e.target.value)}>
          <option value="">— pick a set —</option>
          {sets.map((s) => (
            <option key={s.name} value={s.name}>
              {s.name}
            </option>
          ))}
        </select>
        <select value={qaAdapter} onChange={(e) => setQaAdapter(e.target.value)}>
          <option value="">no adapter</option>
          {adapters.map((a) => (
            <option key={a.id} value={a.path}>
              {a.name} ({engine === "auto" ? "mlx" : engine} only)
            </option>
          ))}
        </select>
        <button className="primary" onClick={runQa} disabled={!model || !runSet}>
          Run
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );

  function runQaWith(name: string) {
    api<{ job_id: string }>("/api/eval-sets/run", {
      method: "POST",
      body: JSON.stringify({
        model,
        adapter: qaAdapter || null,
        engine,
        eval_set: name,
        max_tokens: 96,
      }),
    })
      .then((r) => onStarted(r.job_id))
      .catch((e) => setError(String(e)));
  }
}

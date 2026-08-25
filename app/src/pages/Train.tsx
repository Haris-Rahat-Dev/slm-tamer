import { useEffect, useState } from "react";
import { api, type LocalModel } from "../lib/api";

export default function Train({ onStarted }: { onStarted: (jobId: string) => void }) {
  const [models, setModels] = useState<LocalModel[]>([]);
  const [trainingEngines, setTrainingEngines] = useState<{ name: string; available: boolean }[]>([]);
  const [presets, setPresets] = useState<Record<string, Record<string, number>>>({});
  const [adapters, setAdapters] = useState<{ id: string; path: string }[]>([]);
  const [model, setModel] = useState("");
  const [dataset, setDataset] = useState("");
  const [preset, setPreset] = useState("balanced");
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const [exportAdapter, setExportAdapter] = useState("");
  const [exportName, setExportName] = useState("");
  const [registerOllama, setRegisterOllama] = useState(true);
  const [toolchain, setToolchain] = useState<{
    converter: boolean;
    convert_python: boolean;
    ollama: boolean;
  } | null>(null);

  useEffect(() => {
    api<LocalModel[]>("/api/models/local")
      .then((ms) => {
        setModels(ms);
        if (ms.length > 0) setModel(ms[0].path);
      })
      .catch(() => {});
    api<{ training: { name: string; available: boolean }[]; presets: Record<string, Record<string, number>> }>("/api/engines")
      .then((e) => {
        setTrainingEngines(e.training);
        setPresets(e.presets);
      })
      .catch(() => {});
    api<{ id: string; path: string }[]>("/api/adapters").then(setAdapters).catch(() => {});
    api<{ converter: boolean; convert_python: boolean; ollama: boolean }>("/api/models/export-toolchain")
      .then(setToolchain)
      .catch(() => {});
  }, []);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const res = await api<{ job_id: string }>("/api/train", {
        method: "POST",
        body: JSON.stringify({ model, dataset, preset }),
      });
      onStarted(res.job_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setStarting(false);
    }
  }

  async function exportGguf() {
    setError(null);
    try {
      const res = await api<{ job_id: string }>("/api/models/export-gguf", {
        method: "POST",
        body: JSON.stringify({
          model,
          adapter: exportAdapter || null,
          output_name: exportName,
          register_ollama: registerOllama,
        }),
      });
      onStarted(res.job_id);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h2>Train LoRA adapter</h2>
      <label>
        Base model
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {models.length === 0 && <option value="">— download a model first —</option>}
          {models.map((m) => (
            <option key={m.path} value={m.path}>
              {m.repo_id}
            </option>
          ))}
        </select>
      </label>

      <label>
        Dataset directory (must contain train.jsonl)
        <input
          className="mono"
          value={dataset}
          onChange={(e) => setDataset(e.target.value)}
          placeholder="/path/to/dataset"
        />
      </label>

      <fieldset className="presets">
        <legend>Preset</legend>
        {Object.entries(presets).map(([name, cfg]) => (
          <label key={name} className="radio">
            <input
              type="radio"
              name="preset"
              checked={preset === name}
              onChange={() => setPreset(name)}
            />
            <span>
              <b>{name}</b> · iters {cfg.iters} · bs {cfg.batch_size} · lr {cfg.learning_rate}
            </span>
          </label>
        ))}
      </fieldset>

      <div className="row">
        <button onClick={start} disabled={starting || !model || !dataset}>
          {starting ? "Starting…" : "Start training"}
        </button>
        {trainingEngines.map((e) => (
          <span key={e.name} className={e.available ? "ok" : "muted"}>
            engine: {e.name} ({e.available ? "available" : "unavailable"})
          </span>
        ))}
      </div>

      <h2>Export GGUF</h2>
      <p className="muted">
        Dequantize-fuse → convert (q8_0) → optionally register in Ollama.
        {toolchain && (
          <>
            {" "}Toolchain:{" "}
            {(["converter", "convert_python", "ollama"] as const).map((k) => (
              <span key={k} className={toolchain[k] ? "ok" : "error"}>
                {k} {toolchain[k] ? "✓" : "✗"}{" "}
              </span>
            ))}
          </>
        )}
      </p>
      <div className="row">
        <select value={exportAdapter} onChange={(e) => setExportAdapter(e.target.value)}>
          <option value="">no adapter (base only)</option>
          {adapters.map((a) => (
            <option key={a.id} value={a.path}>
              adapter {a.id}
            </option>
          ))}
        </select>
        <input
          value={exportName}
          onChange={(e) => setExportName(e.target.value)}
          placeholder="output name (e.g. my-model-tuned)"
        />
        <label className="checkbox">
          <input
            type="checkbox"
            checked={registerOllama}
            onChange={(e) => setRegisterOllama(e.target.checked)}
          />
          register in Ollama
        </label>
        <button onClick={exportGguf} disabled={!model || !exportName}>
          Export
        </button>
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  );
}

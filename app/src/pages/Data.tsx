import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface Dataset {
  name: string;
  path: string;
  examples: number;
}

export default function Data({ onStarted }: { onStarted: (jobId: string) => void }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setDatasets(await api<Dataset[]>("/api/datasets"));
  }

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  async function ingest() {
    setError(null);
    try {
      const res = await api<{ job_id: string }>("/api/datasets/ingest", {
        method: "POST",
        body: JSON.stringify({ path, name }),
      });
      onStarted(res.job_id);
      poll(res.job_id);
    } catch (e) {
      setError(String(e));
    }
  }

  async function poll(jobId: string) {
    for (let i = 0; i < 600; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      try {
        const row = await api<{ status: string }>(`/api/jobs/${jobId}`);
        if (row.status === "done") {
          refresh();
          return;
        }
        if (row.status === "error" || row.status === "cancelled") return;
      } catch {
        return;
      }
    }
  }

  return (
    <div>
      <h2>Build a dataset from a repo</h2>
      <p className="muted">
        Crawls code + docs (skips node_modules/.git/…), chunks files, writes
        train.jsonl in mlx-lm completion format.
      </p>
      <label>
        Repository path
        <input
          className="mono"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="/path/to/project"
        />
      </label>
      <label>
        Dataset name
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="my-project" />
      </label>
      <button className="primary" onClick={ingest} disabled={!path || !name}>
        Ingest
      </button>
      {error && <p className="error">{error}</p>}

      <h2>Datasets</h2>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Examples</th>
            <th>Path</th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((d) => (
            <tr key={d.name}>
              <td>{d.name}</td>
              <td>{d.examples}</td>
              <td className="mono">{d.path}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

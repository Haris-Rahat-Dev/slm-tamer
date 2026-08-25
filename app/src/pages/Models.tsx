import { useEffect, useState } from "react";
import {
  api,
  formatBytes,
  formatParams,
  type LocalModel,
  type SearchHit,
} from "../lib/api";

export default function Models() {
  const [query, setQuery] = useState("qwen3");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [local, setLocal] = useState<LocalModel[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function refreshLocal() {
    setLocal(await api<LocalModel[]>("/api/models/local"));
  }

  useEffect(() => {
    refreshLocal().catch(() => {});
    search();
  }, []);

  async function search() {
    setError(null);
    try {
      setHits(await api<SearchHit[]>(`/api/models/search?q=${encodeURIComponent(query)}&limit=24`));
    } catch (e) {
      setError(String(e));
    }
  }

  async function download(repoId: string) {
    setBusy(repoId);
    setError(null);
    try {
      const res = await api<{ job_id: string | null; status: string }>("/api/models/download", {
        method: "POST",
        body: JSON.stringify({ repo_id: repoId }),
      });
      if (!res.job_id) {
        setStatus(`${repoId}: already downloaded`);
      } else {
        setStatus(`${repoId}: download started (${res.job_id})`);
        pollJob(res.job_id, repoId);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function pollJob(jobId: string, repoId: string) {
    for (let i = 0; i < 2000; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      try {
        const row = await api<{ status: string }>(`/api/jobs/${jobId}`);
        if (row.status === "done") {
          setStatus(`${repoId}: downloaded`);
          refreshLocal();
          return;
        }
        if (row.status === "error" || row.status === "cancelled") {
          setStatus(`${repoId}: ${row.status}`);
          return;
        }
        setStatus(`${repoId}: downloading…`);
      } catch {
        return;
      }
    }
  }

  return (
    <div>
      <h2>Local models</h2>
      {local.length === 0 && <p className="muted">Nothing downloaded yet.</p>}
      <ul className="list">
        {local.map((m) => (
          <li key={m.path}>
            <span className="mono">{m.repo_id}</span>
            <span className="muted"> · {formatBytes(m.size_bytes)}</span>
          </li>
        ))}
      </ul>

      <h2>Hugging Face search</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
        className="row"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="search models…"
        />
        <button className="primary" type="submit">Search</button>
      </form>

      {error && <p className="error">{error}</p>}
      {status && <p className="ok">{status}</p>}

      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Params</th>
            <th>Downloads</th>
            <th>Likes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {hits.map((h) => (
            <tr key={h.repo_id}>
              <td className="mono">{h.repo_id}</td>
              <td>{formatParams(h.params)}</td>
              <td>{h.downloads.toLocaleString()}</td>
              <td>{h.likes}</td>
              <td>
                <button disabled={busy === h.repo_id} onClick={() => download(h.repo_id)}>
                  Download
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

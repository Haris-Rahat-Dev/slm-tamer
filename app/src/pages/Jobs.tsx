import { useEffect, useRef, useState } from "react";
import { api, jobWs, type JobRow } from "../lib/api";

export default function Jobs({ selected }: { selected: string | null }) {
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [activeId, setActiveId] = useState<string | null>(selected);
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState<string>("");
  const logRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    setActiveId(selected);
  }, [selected]);

  useEffect(() => {
    const load = () => api<JobRow[]>("/api/jobs").then(setJobs).catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!activeId) return;
    setLogs([]);
    setStatus("");
    let ws = jobWs(activeId);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.error === "job not found") {
        setStatus("not running (restart core to view old jobs)");
        return;
      }
      if (msg.logs?.length) setLogs((prev) => [...prev, ...msg.logs]);
      if (msg.status) setStatus(msg.status);
    };
    ws.onclose = () => {};
    return () => ws.close();
  }, [activeId]);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [logs]);

  return (
    <div className="jobs-layout">
      <div className="jobs-list">
        <h2>Jobs</h2>
        {jobs.length === 0 && <p className="muted">No jobs yet.</p>}
        <ul className="list">
          {jobs.map((j) => (
            <li
              key={j.id}
              className={j.id === activeId ? "active" : ""}
              onClick={() => setActiveId(j.id)}
            >
              <span className={`badge ${j.status}`}>{j.status}</span>
              <span> {j.kind}</span>
              <span className="muted mono"> {j.id}</span>
              <div className="muted small">
                {typeof j.params.model === "string" ? j.params.model : ""}
                {typeof j.params.repo_id === "string" ? ` ${j.params.repo_id}` : ""}
              </div>
            </li>
          ))}
        </ul>
      </div>
      <div className="job-log">
        {activeId ? (
          <>
            <div className="row">
              <h2>{activeId}</h2>
              <span className={`badge ${status}`}>{status}</span>
            </div>
            <pre ref={logRef} className="mono">
              {logs.join("\n")}
            </pre>
          </>
        ) : (
          <p className="muted">Select a job to stream its output.</p>
        )}
      </div>
    </div>
  );
}

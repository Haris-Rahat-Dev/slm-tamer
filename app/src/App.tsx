import { useState } from "react";
import Models from "./pages/Models";
import Data from "./pages/Data";
import Train from "./pages/Train";
import Evaluate from "./pages/Evaluate";
import Chat from "./pages/Chat";
import Jobs from "./pages/Jobs";

type Tab = "models" | "data" | "train" | "evaluate" | "chat" | "jobs";

export default function App() {
  const [tab, setTab] = useState<Tab>("models");
  const [jobId, setJobId] = useState<string | null>(null);

  function openJob(id: string) {
    setJobId(id);
    setTab("jobs");
  }

  return (
    <div className="shell">
      <nav>
        <h1 className="brand">slm-tamer</h1>
        <button className={tab === "models" ? "on" : ""} onClick={() => setTab("models")}>
          <span className="icon">⬇</span> Models
        </button>
        <button className={tab === "data" ? "on" : ""} onClick={() => setTab("data")}>
          <span className="icon">▤</span> Data
        </button>
        <button className={tab === "train" ? "on" : ""} onClick={() => setTab("train")}>
          <span className="icon">⚡</span> Train
        </button>
        <button className={tab === "evaluate" ? "on" : ""} onClick={() => setTab("evaluate")}>
          <span className="icon">◎</span> Evaluate
        </button>
        <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>
          <span className="icon">✦</span> Chat
        </button>
        <button className={tab === "jobs" ? "on" : ""} onClick={() => setTab("jobs")}>
          <span className="icon">☰</span> Jobs
        </button>
        <div className="spacer" />
        <div className="hint">tame small models<br />for your domain</div>
      </nav>
      <main>
        {tab === "models" && <Models />}
        {tab === "data" && <Data onStarted={openJob} />}
        {tab === "train" && <Train onStarted={openJob} />}
        {tab === "evaluate" && <Evaluate onStarted={openJob} />}
        {tab === "chat" && <Chat />}
        {tab === "jobs" && <Jobs selected={jobId} />}
      </main>
    </div>
  );
}

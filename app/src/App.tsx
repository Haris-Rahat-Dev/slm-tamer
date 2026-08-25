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
          Models
        </button>
        <button className={tab === "data" ? "on" : ""} onClick={() => setTab("data")}>
          Data
        </button>
        <button className={tab === "train" ? "on" : ""} onClick={() => setTab("train")}>
          Train
        </button>
        <button className={tab === "evaluate" ? "on" : ""} onClick={() => setTab("evaluate")}>
          Evaluate
        </button>
        <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>
          Chat
        </button>
        <button className={tab === "jobs" ? "on" : ""} onClick={() => setTab("jobs")}>
          Jobs
        </button>
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

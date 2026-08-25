import anyio
from fastapi import WebSocket

from ..jobs import manager


async def job_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    cursor = 0
    last_status = None
    try:
        while True:
            job = manager.get(job_id)
            if job is None:
                await websocket.send_json({"error": "job not found"})
                break
            snap = job.snapshot(since=cursor)
            cursor = snap["cursor"]
            payload = {"status": snap["status"], "logs": snap["logs"]}
            if snap["result"] is not None:
                payload["result"] = snap["result"]
            if snap["error"]:
                payload["error"] = snap["error"]
            if payload["logs"] or snap["status"] != last_status:
                await websocket.send_json(payload)
                last_status = snap["status"]
            if snap["status"] in ("done", "error", "cancelled"):
                break
            await anyio.sleep(0.4)
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

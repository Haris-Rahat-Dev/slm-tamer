from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__, db
from ..api.routes_chat import router as chat_router
from ..api.routes_datasets import router as datasets_router
from ..api.routes_export import router as export_router
from ..api.routes_models import router as models_router
from ..api.routes_qa import router as qa_router
from ..api.routes_train import router as train_router
from ..api.ws import job_stream

app = FastAPI(title="slm-tamer", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_router)
app.include_router(train_router)
app.include_router(datasets_router)
app.include_router(chat_router)
app.include_router(export_router)
app.include_router(qa_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str):
    await job_stream(websocket, job_id)


@app.on_event("startup")
def startup() -> None:
    db.init_db()

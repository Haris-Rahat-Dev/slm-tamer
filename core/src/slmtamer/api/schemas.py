from pydantic import BaseModel


class DownloadRequest(BaseModel):
    repo_id: str

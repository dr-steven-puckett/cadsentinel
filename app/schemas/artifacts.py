from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    url: str
    kind: str  # "thumbnail" | "png" | "pdf" | "json"

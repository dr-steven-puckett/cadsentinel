from fastapi import FastAPI
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="CadSentinel DWG Pipeline")

# Routers will be included later as we implement them.
# from app.api.routers import ingest, drawings, search, chat, standards
# app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
# ...

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "CadSentinel backend skeleton is running."}


# app/api/routers/chat.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.schemas import ChatDrawingRequest, ChatDrawingResponse
from app.services.chat_drawing import chat_with_drawing

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/drawing", response_model=ChatDrawingResponse)
async def chat_drawing(
    payload: ChatDrawingRequest,
    db: Session = Depends(get_db),
) -> ChatDrawingResponse:
    """
    Chat with a specific drawing version.

    You can pass either:
      - drawing_version_id, or
      - document_id (DWG hash) and the backend will resolve to the latest version.
    """
    try:
        return await chat_with_drawing(db, payload)
    except ValueError as e:
        # invalid drawing_version_id or unknown document_id
        raise HTTPException(status_code=404, detail=str(e))

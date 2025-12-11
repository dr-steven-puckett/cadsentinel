from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.security_mode import (
    get_security_mode,
    set_security_mode,
    SecurityMode,
)

router = APIRouter(prefix="/config", tags=["config"])


class SecurityModeStatus(BaseModel):
    mode: SecurityMode


class SecurityModeUpdate(BaseModel):
    mode: SecurityMode


@router.get("/security-mode", response_model=SecurityModeStatus)
async def get_security_mode_endpoint() -> SecurityModeStatus:
    """
    Return the current security mode.

    - "secure"     → use Ollama (local)
    - "not_secure" → use OpenAI API
    """
    return SecurityModeStatus(mode=get_security_mode())


@router.post("/security-mode", response_model=SecurityModeStatus)
async def set_security_mode_endpoint(payload: SecurityModeUpdate) -> SecurityModeStatus:
    """
    Set the global security mode at runtime.
    """
    new_mode = set_security_mode(payload.mode)
    return SecurityModeStatus(mode=new_mode)

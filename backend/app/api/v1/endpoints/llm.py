"""LLM-Komfort-Endpunkte (Phase 7) — Ollama-gestützte Assistenz im Angebotseditor."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_current_user, get_tenant_id
from app.services.ollama import suggest_position, split_to_positions, available_models

router = APIRouter()


class SuggestPositionRequest(BaseModel):
    keywords: str
    context: str = "bau"  # "bau" oder "huf"


class SuggestPositionResponse(BaseModel):
    description: str
    unit: str
    unit_price: str | None = None
    vat_rate: str = "19.00"


class SplitPositionsRequest(BaseModel):
    text: str
    context: str = "bau"


class PositionItem(BaseModel):
    description: str
    qty: str = "1"
    unit: str = "Stk"
    unit_price: str = "0.00"
    vat_rate: str = "19.00"


@router.post("/suggest-position", response_model=SuggestPositionResponse)
async def suggest_position_endpoint(
    body: SuggestPositionRequest,
    _tenant_id: int = Depends(get_tenant_id),
    _user=Depends(get_current_user),
) -> SuggestPositionResponse:
    result = await suggest_position(body.keywords, body.context)
    if not result:
        raise HTTPException(503, "LLM nicht verfügbar oder keine Antwort")
    return SuggestPositionResponse(**result)


@router.post("/split-positions", response_model=list[PositionItem])
async def split_positions_endpoint(
    body: SplitPositionsRequest,
    _tenant_id: int = Depends(get_tenant_id),
    _user=Depends(get_current_user),
) -> list[PositionItem]:
    result = await split_to_positions(body.text, body.context)
    if not result:
        raise HTTPException(503, "LLM nicht verfügbar oder keine Antwort")
    return [PositionItem(**item) for item in result]


@router.get("/models")
async def list_models(
    _tenant_id: int = Depends(get_tenant_id),
    _user=Depends(get_current_user),
) -> list[str]:
    return await available_models()

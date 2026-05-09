"""Ollama-Client: OCR-Strukturierung + LLM-Komfort (Phase 7)."""
from __future__ import annotations

import json
import re

import httpx

from app.core.config import settings

_STRUCTURE_PROMPT = """\
Analysiere den folgenden Text einer Eingangsrechnung und extrahiere die Informationen.
Antworte NUR mit einem JSON-Objekt, ohne Erklärungen.

Felder:
- supplier_name: Name des Lieferanten (String oder null)
- invoice_number: Rechnungsnummer des Lieferanten (String oder null)
- invoice_date: Rechnungsdatum im Format YYYY-MM-DD (String oder null)
- due_date: Fälligkeitsdatum im Format YYYY-MM-DD (String oder null)
- subtotal: Nettobetrag als Zahl ohne Währungszeichen (String oder null)
- vat_total: Mehrwertsteuerbetrag als Zahl (String oder null)
- total: Bruttobetrag als Zahl (String oder null)
- description: Kurzbeschreibung der Leistung in 1-2 Sätzen (String oder null)

Rechnungstext:
{content}

JSON:"""


async def structure_invoice(ocr_text: str, model: str = "llama3.2") -> dict:
    """Sendet OCR-Text an Ollama und gibt strukturierte Felder zurück."""
    prompt = _STRUCTURE_PROMPT.format(content=ocr_text[:4000])

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
        if resp.status_code != 200:
            return {}

        raw = resp.json().get("response", "")
        # JSON aus der Antwort extrahieren
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {}
        return json.loads(match.group())
    except Exception:
        return {}


async def available_models() -> list[str]:
    """Gibt eine Liste verfügbarer Ollama-Modelle zurück."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


_SUGGEST_POSITION_PROMPT = """\
Du bist ein Assistent für ein deutsches Bauunternehmen / Hufbeschlagsunternehmen.
Erstelle aus den folgenden Stichwörtern eine vollständige, professionelle Angebotsposition.
Kontext: {context}
Antworte NUR mit einem JSON-Objekt, ohne Erklärungen.

Felder:
- description: Vollständige Positionsbeschreibung auf Deutsch (String, max. 200 Zeichen)
- unit: Einheit (Stk / m / m² / m³ / h / kg / psch) — wähle passend zur Leistung
- unit_price: Typischer Einzelpreis als String (z.B. "85.00") oder null wenn unbekannt
- vat_rate: Mehrwertsteuersatz ("19.00" für Standard, "7.00" für Sonderfälle, "0.00" für steuerfreie Leistungen)

Stichwörter: {keywords}

JSON:"""

_SPLIT_POSITIONS_PROMPT = """\
Du bist ein Assistent für ein deutsches Bauunternehmen / Hufbeschlagsunternehmen.
Zerlege den folgenden Freitext in einzelne Angebotsposition.
Kontext: {context}
Antworte NUR mit einem JSON-Array, ohne Erklärungen.

Jede Position hat folgende Felder:
- description: Positionsbeschreibung (String)
- qty: Menge als String (z.B. "1", "2.5")
- unit: Einheit (Stk / m / m² / m³ / h / kg / psch)
- unit_price: Einzelpreis als String oder "0.00" wenn unbekannt
- vat_rate: "19.00", "7.00" oder "0.00"

Freitext: {text}

JSON-Array:"""


async def _ollama_generate(prompt: str, model: str = "llama3.2") -> str:
    """Sendet einen Prompt an Ollama und gibt den Rohtext zurück."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
        if resp.status_code != 200:
            return ""
        return resp.json().get("response", "")
    except Exception:
        return ""


async def suggest_position(keywords: str, context: str = "bau") -> dict:
    """Stichwörter → ausformulierte Angebotsposition."""
    ctx = "Bauunternehmen" if context == "bau" else "Hufbeschlagsunternehmen"
    prompt = _SUGGEST_POSITION_PROMPT.format(keywords=keywords[:500], context=ctx)
    raw = await _ollama_generate(prompt)
    if not raw:
        return {}
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except Exception:
        return {}


async def split_to_positions(text: str, context: str = "bau") -> list[dict]:
    """Freitext → Liste von Angebotspositionen."""
    ctx = "Bauunternehmen" if context == "bau" else "Hufbeschlagsunternehmen"
    prompt = _SPLIT_POSITIONS_PROMPT.format(text=text[:2000], context=ctx)
    raw = await _ollama_generate(prompt)
    if not raw:
        return []
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        result = json.loads(match.group())
        return result if isinstance(result, list) else []
    except Exception:
        return []

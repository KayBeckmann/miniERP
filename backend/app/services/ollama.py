"""Ollama-Client für Strukturierung von OCR-Texten."""
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

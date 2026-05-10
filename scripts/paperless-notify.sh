#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Paperless-ngx Post-Consume-Script → miniERP Webhook
#
# Wird von Paperless nach jeder Dokumentenverarbeitung aufgerufen.
# Paperless setzt automatisch folgende Umgebungsvariablen:
#   DOCUMENT_ID            - ID des verarbeiteten Dokuments
#   DOCUMENT_FILE_NAME     - Originaldateiname
#   DOCUMENT_CREATED       - Erstellungsdatum
#   DOCUMENT_CORRESPONDENT - Zugeordneter Korrespondent
#
# Konfiguration via docker-compose.yml (Umgebungsvariablen):
#   MINIERP_URL            - miniERP Backend URL (default: http://backend:8000)
#   MINIERP_INTERNAL_TOKEN - Muss mit INTERNAL_PAPERLESS_TOKEN in .env übereinstimmen
#   MINIERP_TENANT_ID      - Mandant-ID in miniERP (1 = bau, 2 = huf, default: 1)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MINIERP_URL="${MINIERP_URL:-http://backend:8000}"
MINIERP_INTERNAL_TOKEN="${MINIERP_INTERNAL_TOKEN:-}"
MINIERP_TENANT_ID="${MINIERP_TENANT_ID:-1}"

if [ -z "$DOCUMENT_ID" ]; then
    echo "[miniERP] Kein DOCUMENT_ID gesetzt, überspringe." >&2
    exit 0
fi

if [ -z "$MINIERP_INTERNAL_TOKEN" ]; then
    echo "[miniERP] MINIERP_INTERNAL_TOKEN nicht gesetzt, überspringe." >&2
    exit 0
fi

ENDPOINT="${MINIERP_URL}/api/v1/supplier-invoices/paperless-hook/${DOCUMENT_ID}"

HTTP_STATUS=$(curl -sf \
    -o /tmp/minierp-hook-response.json \
    -w "%{http_code}" \
    -X POST "${ENDPOINT}" \
    -H "X-Internal-Token: ${MINIERP_INTERNAL_TOKEN}" \
    -H "X-Tenant-ID: ${MINIERP_TENANT_ID}" \
    -H "Content-Type: application/json" \
    --max-time 30 \
    2>/dev/null) || HTTP_STATUS="000"

if [ "$HTTP_STATUS" = "201" ] || [ "$HTTP_STATUS" = "200" ]; then
    echo "[miniERP] Dokument ${DOCUMENT_ID} erfolgreich übermittelt (HTTP ${HTTP_STATUS})"
else
    echo "[miniERP] Webhook fehlgeschlagen (HTTP ${HTTP_STATUS}) — miniERP läuft?" >&2
    # Kein Exit 1 — Paperless soll weiterlaufen auch wenn miniERP nicht erreichbar ist
fi

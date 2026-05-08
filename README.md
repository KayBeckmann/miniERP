# miniERP

Kleines, selbst gebautes ERP für ein Einzelunternehmen mit zwei Sparten:
**Bauunternehmen** (`bau`) und **Hufbearbeitung** (`huf`). Ziel: Angebote,
Aufträge, Ausgangs- und Eingangsrechnungen, Stundenerfassung und einfache
Auswertungen – ohne den Pflegeaufwand eines klassischen Materialstamms.

> **Status: Phase 0 abgeschlossen** — Stack läuft (`postgres`, `backend`,
> `frontend`). Nächster Schritt: Phase 1 (Stammdaten).
> Details siehe [`Roadmap.md`](./Roadmap.md).

## Idee

Die Inhaberin schreibt ihre Angebote bisher per Hand in LibreOffice Writer.
Wiederholungen im Material gibt es kaum, eine klassische Stammpflege wäre
teurer als der Nutzen. miniERP setzt deshalb auf:

- **Freitext-first Positionen**: Beschreibung + Menge + Preis genügt; ein
  Materialstamm wächst optional aus tatsächlich wiederkehrenden Einträgen.
- **Zwei Sparten** (`bau`, `huf`) eines Einzelunternehmens – eigene
  Nummernkreise, Templates und Auswertungen, steuerlich aber ein Topf.
- **LLM-Unterstützung lokal** über Ollama: Stichworte zu Positionen
  ausformulieren, Lieferantenrechnungen strukturieren, Texte für
  Anschreiben/Mahnungen entwerfen.
- **GoBD- und E-Rechnungs-fähig**: XRechnung/ZUGFeRD bei B2B,
  PDF-Hashkette, append-only Audit-Log.

## Stack

| Bereich        | Wahl                                                          |
| -------------- | ------------------------------------------------------------- |
| Backend        | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2                |
| Datenbank      | PostgreSQL 16                                                 |
| Frontend       | Vue 3 · Vite · TypeScript · Pinia · Vuetify 3 (PWA)           |
| Auth           | JWT (Access + Refresh) · argon2                               |
| PDF            | Gotenberg-Sidecar (HTML/Jinja → PDF/A)                        |
| OCR            | Paperless-ngx (eingebaut), Tesseract als Fallback             |
| LLM            | Ollama (lokal), z. B. `llama3.1` / `qwen2.5` / `mistral`     |
| Dokumentablage | Paperless-ngx (Default), Nextcloud als zweiter Adapter        |
| Automation     | n8n via Webhooks (keine Geschäftslogik in n8n)                |
| Container      | Docker Compose                                                |
| Tests          | pytest (Backend) · Vitest/Playwright (Frontend, ab Phase 2)  |
| Lint/Format    | ruff + black (Backend) · eslint + prettier (Frontend)         |

## Module (geplant)

- **Stammdaten**: Kunden, Lieferanten, optionaler Materialstamm
- **Angebote → Aufträge → Auftragsbestätigung → Rechnung** (Teil/Abschlag/Schluss) → Gutschrift
- **Stundenerfassung** (mobil-tauglich, PWA)
- **Lieferantenrechnungen** mit OCR-Vorbefüllung und Auftragszuordnung
- **Auswertungen und Steuerberater-Export** (Zip mit CSVs + Belegen, pro Sparte aufgeschlüsselt)
- Spätere Ausbaustufen: FinTS-Zahlungsabgleich, DATEV-Export, Peppol-Versand

Genauer Phasenplan und Datenmodell stehen in der [`Roadmap.md`](./Roadmap.md).

## Repo-Struktur

```
miniERP/
├── backend/                   FastAPI · SQLAlchemy 2 · Alembic
│   ├── app/
│   │   ├── api/v1/            Router pro Modul
│   │   ├── core/              config, security, db
│   │   ├── models/            SQLAlchemy ORM (Tenant, User, …)
│   │   ├── schemas/           Pydantic
│   │   ├── services/          Geschäftslogik (PDF, LLM, …)
│   │   └── main.py
│   ├── alembic/               Migrationen
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  Vue 3 + Vuetify 3 (PWA)
│   ├── src/
│   │   ├── api/               API-Client + Typen
│   │   ├── components/        Layout, wiederverwendbare Komponenten
│   │   ├── layouts/           DefaultLayout mit Header + Drawer
│   │   ├── pages/             Login, Dashboard, alle Module
│   │   ├── router/            Vue Router mit Auth-Guard
│   │   └── stores/            Pinia (auth + aktiver Mandant)
│   └── Dockerfile
├── n8n/workflows/             exportierte Workflows (ab Phase 5)
├── templates/pdf/             HTML/CSS-Templates pro Mandant (ab Phase 2)
├── docs/                      Datenmodell, ADRs
├── .github/workflows/         CI: lint + tests
├── docker-compose.yml
├── .env.example
├── Roadmap.md
└── README.md
```

## Schnellstart

```bash
# 1. Umgebungsvariablen anlegen
cp .env.example .env
# .env anpassen: POSTGRES_PASSWORD, SECRET_KEY, FIRST_SUPERUSER_PASSWORD

# 2. Stack starten (postgres + backend + frontend)
docker compose up -d

# 3. Frontend aufrufen
open http://localhost:3000
# Login: FIRST_SUPERUSER_EMAIL / FIRST_SUPERUSER_PASSWORD aus .env

# 4. API-Docs (Swagger)
open http://localhost:3000/api/v1/docs
```

### Optionale Profile

```bash
# Entwicklungsmodus (Vite Dev-Server mit Hot-Reload auf Port 5173)
docker compose --profile dev up -d frontend-dev

# PDF-Service (Gotenberg)
docker compose --profile pdf up -d gotenberg

# Workflow-Automation (n8n)
docker compose --profile automation up -d n8n

# Lokales LLM (Ollama)
docker compose --profile llm up -d ollama
```

## Entwicklung

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# Tests
pytest
# Lint
ruff check . && black --check .
# Migration erstellen
alembic revision --autogenerate -m "beschreibung"
alembic upgrade head
```

### Frontend

```bash
cd frontend
npm install
npm run dev        # Vite Dev-Server auf http://localhost:5173
npm run lint       # ESLint
npm run build      # Produktions-Build
```

## Lizenz

Siehe [`LICENSE`](./LICENSE).

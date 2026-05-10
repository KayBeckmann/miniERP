# miniERP

Kleines, selbst gebautes ERP für ein Einzelunternehmen mit zwei Sparten:
**Bauunternehmen** (`bau`) und **Hufbearbeitung** (`huf`). Ziel: Angebote,
Aufträge, Ausgangs- und Eingangsrechnungen, Stundenerfassung und einfache
Auswertungen – ohne den Pflegeaufwand eines klassischen Materialstamms.

> **Status: Phasen 0–8 implementiert** — vollständig lauffähig.
> Details und Fortschritt in der [`Roadmap.md`](./Roadmap.md).

## Idee

Freitext-first: Position = Beschreibung + Menge + Preis, kein Stammpflege-Zwang.
Zwei Sparten eines Einzelunternehmens mit eigenen Nummernkreisen und Templates.

## Stack

| Bereich        | Wahl                                                          |
| -------------- | ------------------------------------------------------------- |
| Backend        | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2                |
| Datenbank      | PostgreSQL 16                                                 |
| Frontend       | Vue 3 · Vite · TypeScript · Pinia · Vuetify 3 (PWA)           |
| Auth           | JWT (Access + Refresh) · argon2                               |
| PDF            | Gotenberg-Sidecar (HTML/Jinja → PDF/A)                        |
| Dokumente      | Paperless-ngx (eingebaut, OCR, Custom Fields, Webhooks)       |
| LLM            | Ollama lokal — `llama3.2:3b` empfohlen (2 GB RAM, CPU-only)   |
| Automation     | n8n via Webhooks                                              |
| Container      | Docker Compose                                                |

## Services im Stack

| Service            | Port   | Beschreibung                              |
| ------------------ | ------ | ----------------------------------------- |
| `frontend`         | 3000   | Vue 3 Web-UI (Nginx)                      |
| `backend`          | intern | FastAPI + Alembic-Migrationen             |
| `postgres`         | intern | miniERP-Datenbank                         |
| `gotenberg`        | intern | HTML → PDF/A (Gotenberg 8)                |
| `paperless`        | 8001   | Paperless-ngx Dokumentenmanagement        |
| `paperless-db`     | intern | Eigene PostgreSQL-DB für Paperless        |
| `paperless-redis`  | intern | Redis Task-Queue für Paperless            |
| `ollama`           | intern | Lokales LLM (llama3.2:3b empfohlen)       |
| `n8n`              | 5678   | Workflow-Automation (Profile: automation) |

## Schnellstart

```bash
# 1. Umgebungsvariablen anlegen
cp .env.example .env
# .env anpassen — mindestens:
#   POSTGRES_PASSWORD, SECRET_KEY, FIRST_SUPERUSER_PASSWORD
#   PAPERLESS_DBPASS, PAPERLESS_SECRET_KEY, PAPERLESS_ADMIN_PASSWORD

# 2. Stack starten
docker compose up -d

# 3. miniERP Web-UI
open http://localhost:3000
# Login: FIRST_SUPERUSER_EMAIL / FIRST_SUPERUSER_PASSWORD

# 4. Ollama-Modell laden (einmalig, ~2 GB Download)
docker exec -it minierp-ollama-1 ollama pull llama3.2:3b

# 5. API-Docs (Swagger)
open http://localhost:3000/api/v1/docs
```

## Paperless-ngx Einrichtung (Erststart)

```bash
# 1. Stack starten (Paperless-ngx wird unter Port 8001 erreichbar)
docker compose up -d

# 2. Paperless aufrufen und als Admin anmelden
open http://localhost:8001
# Login: PAPERLESS_ADMIN_USER / PAPERLESS_ADMIN_PASSWORD aus .env

# 3. API-Token erzeugen
#    Profil (oben rechts) → Mein Profil → API-Token → Token erzeugen → kopieren

# 4. Token in .env eintragen
#    PAPERLESS_TOKEN=<kopierter-token>

# 5. Backend neu starten (damit Token aktiv wird)
docker compose restart backend

# 6. Optional: Custom Fields für Rechnungsverknüpfung anlegen
#    Admin → Custom Fields → "rechnung_no" (Text) + "auftrag_no" (Text) + "sparte" (Text)
```

## VPS-Deployment

```bash
# Voraussetzungen: Docker + Docker Compose auf dem VPS

# 1. Repo klonen
git clone https://github.com/KayBeckmann/miniERP.git
cd miniERP

# 2. .env anlegen und anpassen
cp .env.example .env
nano .env   # alle change_me-Werte ersetzen

# 3. Images bauen und Stack starten
docker compose up -d --build

# 4. Ollama-Modell laden (einmalig)
docker exec -it minierp-ollama-1 ollama pull llama3.2:3b

# 5. Paperless einrichten (siehe oben)

# Tipp: Reverse-Proxy (nginx/Traefik) vor die Dienste schalten
# und HTTPS per Let's Encrypt aktivieren.
# Ports: frontend:3000  paperless:8001  n8n:5678 (nur mit --profile automation)
```

### Ollama Modellwahl

| Modell         | RAM   | Qualität (DE) | Empfehlung             |
| -------------- | ----- | ------------- | ---------------------- |
| `llama3.2:3b`  | ~2 GB | ★★★★☆         | **Standard-Empfehlung** |
| `gemma3:4b`    | ~3 GB | ★★★★☆         | Gute Alternative        |
| `mistral:7b`   | ~5 GB | ★★★★★         | Bei ≥ 8 GB RAM          |
| `phi3:mini`    | ~2 GB | ★★★☆☆         | Sehr schnell, weniger DE|

```bash
# Modell wechseln (Beispiel: mistral)
docker exec -it minierp-ollama-1 ollama pull mistral:7b
# In backend/.env: (Backend nutzt den Namen aus dem API-Aufruf, kein Neustart nötig)
```

### GPU-Support (NVIDIA)

```yaml
# In docker-compose.yml unter ollama: uncomment deploy-Block
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

## Optionale Profile

```bash
# n8n Workflow-Automation
docker compose --profile automation up -d n8n

# Frontend Dev-Server (Vite, Hot-Reload)
docker compose --profile dev up -d frontend-dev
```

## Entwicklung

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                              # Tests
ruff check . && black --check .     # Lint
alembic upgrade head                # Migrationen

# Frontend
cd frontend
npm install
npm run dev     # http://localhost:5173
npm run build   # Produktions-Build
```

## Repo-Struktur

```
miniERP/
├── backend/                   FastAPI · SQLAlchemy 2 · Alembic
│   ├── app/
│   │   ├── api/v1/            Router pro Modul
│   │   ├── core/              config, security, db
│   │   ├── models/            SQLAlchemy ORM
│   │   ├── schemas/           Pydantic
│   │   └── services/          PDF, LLM, Paperless, Kalkulation
│   ├── alembic/               Migrationen 0001–0009
│   └── templates/pdf/         Jinja2-HTML-Templates
├── frontend/
│   └── src/
│       ├── api/               API-Client + TypeScript-Typen
│       ├── pages/             Alle Seiten (Dashboard, Angebote, …)
│       └── stores/            Pinia (Auth, Snackbar)
├── docker-compose.yml
├── .env.example
└── Roadmap.md
```

## Lizenz

Siehe [`LICENSE`](./LICENSE).

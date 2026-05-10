# miniERP – Roadmap

Kleines, selbst gebautes ERP für ein Bauunternehmen + Hufbearbeitung. Ziel: Angebote,
Aufträge, Ausgangs- und Eingangsrechnungen, Stundenerfassung, Materialstamm, Auswertungen.

## 1. Architekturentscheidungen

| Bereich        | Entscheidung                                                                 |
| -------------- | ---------------------------------------------------------------------------- |
| Backend        | FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2                               |
| Datenbank      | PostgreSQL 16                                                                |
| Frontend       | Vue 3 + Vite + TypeScript + Pinia + Vue Router + **Vuetify 3**               |
| Auth           | JWT (Access + Refresh), 1 User initial, Hashing mit `argon2`                 |
| Mandanten      | 2 Sparten (`Bau`, `Hufbearbeitung`) **eines** Einzelunternehmens; je eigene Nummernkreise und Templates, **steuerlich gemeinsamer Topf** |
| PDF            | **Gotenberg** als Sidecar-Container (HTTP, HTML/Jinja → PDF/A); Backend rendert Jinja, schickt HTML an Gotenberg, bekommt PDF zurück |
| Dokumentablage | **Paperless-ngx als primärer Belegspeicher** (REST, OCR, Custom Fields, Webhooks); Nextcloud optional als Consume-Ordner / Briefpapier-Share. MinIO bleibt nur als späterer Adapter im Backlog. |
| Automation     | n8n via Webhooks ins Backend (keine Geschäftslogik in n8n; n8n macht **nicht** die REST-API) |
| LLM            | Ollama (lokal), empfohlen: `llama3.2:3b` (2 GB RAM, CPU-only), alternativ `gemma3:4b` / `mistral:7b` |
| OCR            | Tesseract (für Fotos/Scans ohne Textlayer) → Text → Ollama-Strukturierung (JSON) |
| Container      | docker-compose (postgres, backend, frontend, n8n, ollama, paperless optional) |
| Tests          | pytest (Backend) + Vitest/Playwright (Frontend, später)                      |
| Lint/Format    | ruff + black (Backend), eslint + prettier (Frontend)                         |

### Repo-Struktur (Zielbild)

```
miniERP/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # Router pro Modul
│   │   ├── core/             # config, security, db
│   │   ├── models/           # SQLAlchemy ORM
│   │   ├── schemas/          # Pydantic
│   │   ├── services/         # Geschäftslogik (PDF, LLM, Numbering, …)
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/              # generierter / handgeschriebener API-Client
│   │   ├── components/
│   │   ├── pages/
│   │   ├── stores/           # Pinia
│   │   └── main.ts
│   └── package.json
├── n8n/workflows/            # exportierte Workflows
├── templates/pdf/            # HTML/CSS pro Mandant
├── docs/
│   ├── datamodel.md
│   └── adr/                  # Architecture Decision Records
├── docker-compose.yml
├── Roadmap.md
└── README.md
```

## 2. Datenmodell (Entwurf)

### Stammdaten
- **Tenant** (= Sparte des einen Einzelunternehmens): `id`, `code` (`bau` / `huf`), `name`,
  `address`, `iban`, `logo_path`, `invoice_number_prefix`, `quote_number_prefix`,
  `pdf_template`.
  - **Hinweis:** USt-ID und §19-Status liegen **nicht** am Tenant, sondern am übergeordneten
    `Company`-Datensatz, weil steuerlich beide Sparten ein Unternehmen sind.
- **Company** (Singleton): `id`, `legal_name`, `owner_name`, `address`, `tax_id`,
  `vat_id?`, `is_small_business` (§19 UStG, gilt fürs **Gesamtunternehmen**), `bank_iban`,
  `bank_bic`. Wird von beiden Sparten geteilt.
- **User**: `id`, `email`, `password_hash`, `role`, `default_tenant_id`.
- **Customer**: `id`, `tenant_id`, `customer_no`, `kind` (Privat/Geschäft), `name`, `contact`,
  `address`, `email`, `phone`, `tax_id`, `notes`, `created_at`.
- **Supplier**: `id`, `tenant_id`, `name`, `address`, `iban`, `default_payment_terms`.
- **Material/Article**: `id`, `tenant_id`, `sku`, `name`, `description`, `unit` (Stk/m/m²/h/…),
  `purchase_price`, `sale_price`, `vat_rate`, `category`, `default_supplier_id?`, `active`,
  `usage_count` (zur Sortierung „häufig genutzt“).
  - **Wichtig:** Der Materialstamm ist **nicht** das primäre Eingabemodell. Die Inhaberin
    hat in der Praxis wenige Wiederholungen, klassische Stammpflege wäre teurer als der Nutzen.
    Stattdessen siehe Abschnitt **„Freitext-first Positionen“** weiter unten.
- **NumberSequence**: `tenant_id`, `kind` (quote/order_confirmation/invoice/credit_note/supplier_invoice),
  `year`, `next_value`. Lückenlos, transaktional, keine Löschung — nur Stornos.

### Angebote / Aufträge / Rechnungen
- **Quote**: `id`, `tenant_id`, `customer_id`, `quote_no`, `date`, `valid_until`, `status`
  (draft/sent/accepted/declined/expired), `subtotal`, `vat_total`, `total`,
  `notes`, `internal_notes`, `pdf_path`, `version`.
- **QuoteItem**: `id`, `quote_id`, `position`, `material_id?`, `description`, `qty`,
  `unit`, `unit_price`, `discount_pct`, `vat_rate`, `line_total`.
- **Order**: `id`, `tenant_id`, `customer_id`, `quote_id?`, `order_no`, `title`,
  `status` (open/in_progress/done/cancelled), `start_date`, `end_date`,
  `budget_hours`, `budget_material`.
- **OrderConfirmation** (Auftragsbestätigung): `id`, `tenant_id`, `order_id`, `oc_no`,
  `date`, `pdf_path`, `sent_at`. Eigener Belegtyp, eigener Nummernkreis.
- **Invoice**: `id`, `tenant_id`, `customer_id`, `order_id?`, `quote_id?`, `invoice_no`, `date`,
  `due_date`, `kind` (final/partial/advance), `status` (draft/sent/paid/overdue/cancelled),
  `subtotal`, `vat_total`, `total`, `paid_amount`, `paid_at`, `pdf_path`,
  `e_invoice_path?` (XRechnung XML / ZUGFeRD-PDF), `pdf_sha256` (für GoBD-Hashkette).
- **CreditNote** (Gutschrift): `id`, `tenant_id`, `invoice_id`, `credit_no`, `date`, `total`,
  `reason`, `pdf_path`, `pdf_sha256`. Nie Rechnung löschen — immer Gutschrift erzeugen.
- **InvoiceItem** / **CreditNoteItem**: analog `QuoteItem`.
- **Payment**: `id`, `tenant_id`, `invoice_id`, `date`, `amount`, `method`
  (transfer/cash/card), `bank_ref?`, `note`. Mehrere Zahlungen pro Rechnung
  möglich (Teilzahlungen). Vorbereitet für späteren FinTS/HBCI-Import.
- **TimeEntry**: `id`, `order_id`, `user_id`, `date`, `hours`, `description`,
  `hourly_rate?`, `billable` (bool), `invoiced` (bool).
- **SupplierInvoice**: `id`, `tenant_id`, `supplier_id`, `order_id?`, `external_no`,
  `date`, `due_date`, `subtotal`, `vat_total`, `total`, `paid_at`, `document_id`
  (Paperless-/Nextcloud-Referenz), `ocr_payload` (jsonb).
- **Document**: `id`, `tenant_id`, `kind`, `ref_table`, `ref_id`, `storage` (paperless/nextcloud/minio/local),
  `external_id`, `path`, `sha256`, `created_at`.
- **AuditLog** (append-only): `id`, `at`, `user_id`, `tenant_id`, `entity`, `entity_id`,
  `action` (create/update/cancel/credit), `before` (jsonb), `after` (jsonb), `prev_hash`,
  `hash`. Schreibrechte ausschließlich aus dem Backend, keine Updates/Deletes (DB-Trigger).
  Grundlage für GoBD-Nachvollziehbarkeit.

### Beziehungen (vereinfacht)
```
Tenant 1─* Customer 1─* Quote 1─* QuoteItem
                       └── Order 1─* TimeEntry
                                └── 1─* Invoice 1─* InvoiceItem
                                └── *─1 SupplierInvoice (über order_id)
```

Detaillierte ER-Diagramme folgen unter `docs/datamodel.md`.

## 2a. Freitext-first Positionen (statt Stammpflege-Zwang)

Annahme: In beiden Sparten gibt es **wenige echte Wiederholungen** im Material. Klassische
Stammdatenpflege wäre teurer als der spätere Nutzen. Daher:

- **Primärer Eingabepfad ist Freitext**: Position = Beschreibung + Menge + Einheit + Einzelpreis.
  Kein Material-Datensatz nötig, kein Pflicht-Lookup.
- **Quick-Reuse statt Stamm**:
  - Letzte 30 verwendete Positionen pro Mandant als Vorschlagsliste (Volltextsuche, ohne CRUD-Maske).
  - „Aus Angebot X übernehmen“ kopiert komplette Positionsblöcke.
  - Ähnliche Positionen werden via Embedding (Ollama) erkannt und gruppiert vorgeschlagen.
- **Lazy Materialstamm**: Jede Freitext-Position wird normalisiert in eine Tabelle
  `position_history` geschrieben. Erst wenn ein Eintrag mehrfach (Schwelle, z. B. ≥ 3) auftritt,
  bietet das System „Als Stammartikel anlegen?“ an. Stamm wächst organisch, nur dort wo
  sich Pflege lohnt.
- **Material-Modul ist optional**: CRUD existiert (für die wenigen Pauschalen wie Anfahrt,
  Standard-Hufkorrektur), ist aber nicht Voraussetzung, um Angebote/Rechnungen zu schreiben.
- **LLM-Hilfe**: „Stichworte → ausformulierte Position“ als Service (siehe Phase 7),
  ersetzt im Alltag den Stammartikel.

Konsequenz fürs Datenmodell: `QuoteItem.material_id` und `InvoiceItem.material_id` sind
nullable. `position_history` ist eine eigene Tabelle (nicht Material).

## 2b. E-Rechnung & GoBD

E-Rechnungs-Pflicht im B2B-Bereich gilt seit 2025 (Empfang) und ab 2027/2028 schrittweise
auch beim Versand. Daher als **Kernanforderung** statt Backlog:

- Rechnungen werden bei B2B-Kunden zusätzlich als **XRechnung (UBL XML)** und/oder
  **ZUGFeRD 2.x (PDF/A-3 mit eingebettetem XML)** erzeugt.
- Kennzeichen am Customer: `is_business`, `leitweg_id?` (öffentliche Auftraggeber),
  `e_invoice_format` (none/xrechnung/zugferd).
- Bei Privatkunden bleibt es bei klassischem PDF.
- Versand-Pfade: E-Mail, Peppol (später, Backlog), manueller Download.

GoBD-Eckpunkte, die wir umsetzen:

- Unveränderlichkeit: Belege (Quote, Invoice, CreditNote, SupplierInvoice) nach
  Status `sent`/`booked` nur via Gutschrift/Storno korrigierbar, kein UPDATE auf Beträgen.
- Hashkette: PDF-`sha256` wird bei Erzeugung berechnet und im Datensatz festgehalten;
  `AuditLog` hashes verkettet (`prev_hash`).
- Append-only-Tabellen via Postgres-Trigger (verbieten UPDATE/DELETE auf `audit_log` und
  finalen Belegdokumenten).
- Aufbewahrung 10 Jahre, Backup-Strategie dokumentiert.

## 3. Phasen-Roadmap

Jede Phase endet mit einem **lauffähigen Stand** (build grün, manueller Smoketest).

### Phase 0 – Projektgerüst ✅ abgeschlossen (2026-05-08)
- [x] `docker-compose.yml` mit `postgres`, `backend`, `frontend` (n8n/ollama optional aus)
- [x] FastAPI-Skeleton mit `/health`, JWT-Login (1 Seed-User), Settings via `pydantic-settings`
- [x] Alembic initialisiert, `Tenant` + `User` als erste Migration, Seed `bau` + `huf`
- [x] Vue 3 + Vuetify 3 + Vite-Skeleton mit Login-Seite und Mandantenwahl im Header
- [x] `ruff`, `black`, `eslint`, `prettier`, GitHub-Actions-Workflow (lint + tests)

### Phase 1 – Stammdaten ✅ abgeschlossen (2026-05-08)
- [x] CRUD: Customer (mit `is_business`, `e_invoice_format`, `leitweg_id?`), Supplier
- [x] Material/Article CRUD **als optionales Modul** (Pauschalen, Anfahrt, etc.)
- [x] Such-/Filterfelder, Pagination, Sortierung (Material: usage_count DESC)
- [x] CSV-Import für Material übersprungen (keine Altdaten vorhanden)
- [x] Mandanten-Scope strikt im Backend erzwungen (`get_tenant_id`-Dependency, X-Tenant-ID-Header)

### Phase 2 – Angebote ✅ abgeschlossen (2026-05-09)
- [x] Quote + QuoteItem CRUD, Positions-Editor mit **Freitext als Default**
- [x] Quick-Reuse: „Letzte 30 Positionen”, „Aus Angebot X übernehmen”
- [x] `position_history` befüllen (für späteres Lazy-Stamm + Embeddings)
- [x] Optionaler Material-Lookup (nur falls Stammartikel vorhanden)
- [x] Berechnung Netto/USt/Brutto pro Position + Summen serverseitig (single source of truth)
- [x] Nummernkreise pro Mandant + Jahr + Belegart (`NumberSequence`, transaktional)
- [x] PDF-Template `Bau` und `Huf`, **Gotenberg** (HTML/Jinja → PDF/A), Vorschau im Browser
- [x] Status-Workflow (draft → sent → accepted/declined → in Auftrag gewandelt)
- [x] **Angebotsgruppen** (Bad, Küche, …) mit Zwischensummen je Gruppe (Alembic 0007)
- [x] `POST /quotes/{id}/to-order` — akzeptiertes Angebot in Auftrag wandeln
- [x] Bugfix: Datum-Anzeige UTC-Offset (“Invalid Date”), Materialstamm-Auswahl im Editor

### Phase 3 – Aufträge + Stundenerfassung ✅ abgeschlossen (2026-05-09)
- [x] Order entsteht aus akzeptiertem Angebot (Kopie der Positionen als Soll)
- [x] Auftragsbestätigungs-PDF (eigener Belegtyp, eigener Nummernkreis)
- [x] TimeEntry-Erfassung: Wochenansicht + Schnellbuchung mobil (Vuetify, PWA-tauglich)
- [x] Soll/Ist-Auswertung pro Auftrag (Stunden + Material)
- [x] `POST /orders/{id}/to-invoice` — Auftrag in Rechnung wandeln (final/Teil/Abschlag)
- [x] **Budget-Übernahme aus Angebot** (2026-05-10): `to-order` berechnet automatisch
      `budget_hours` (Summe aller Positionen mit Einheit `h`) und
      `budget_material` (Netto-Summe aller übrigen Positionen)

### Phase 4 – Ausgangsrechnungen ✅ abgeschlossen (2026-05-09)
- [x] Rechnung aus Auftrag (anteilig nach Stunden/Material) oder aus Angebot (1:1)
- [x] Teil-/Abschlags-/Schlussrechnung
- [x] **Gutschrift als eigener Belegtyp** (Storno- statt Lösch-Pfad)
- [x] PDF analog zu Angeboten, eigene Templates, `pdf_sha256` festschreiben
- [x] **E-Rechnung Kern, nicht Backlog**: XRechnung (UBL) und ZUGFeRD 2.x abhängig vom
      Customer-Flag erzeugen; mehrere Zahlungen je Rechnung (`Payment` 1:n)
- [x] Zahlungseingang **manuell** erfassen (FinTS folgt später, Schema bleibt vorbereitet),
      OP-Liste, Mahnstufen-Felder vorbereiten

### Phase 5 – Lieferantenrechnungen ✅ abgeschlossen (2026-05-09)
- [x] Upload-Form (auch Foto vom Smartphone) → Backend reicht direkt an
      **Paperless-ngx** durch (`POST /api/documents/post_document/`)
- [x] OCR macht **Paperless** (eingebaut) — Volltext per `/api/documents/{id}/content`
- [x] **Strukturierung via Ollama**: Volltext → JSON (Lieferant, Datum, Netto/USt/Brutto)
- [x] Paperless-Webhook → n8n → `/supplier-invoices/from-paperless/{id}` erzeugt Entwurf
- [x] Custom Fields in Paperless setzen: `rechnung_no`, `auftrag_no` (best-effort)
- [x] Re-Struktur-Button + direkt in Paperless öffnen im Edit-Dialog
- [x] Paperless-Instanz: http://10.10.0.26:8000 (Token: jenny-User)
- [ ] Admin-Hinweis: Custom Fields (auftrag_no, rechnung_no, sparte) manuell anlegen

### Phase 6 – Auswertungen & Steuerberater-Export ✅ abgeschlossen (2026-05-09)
- [x] Offene Angebote, offene Rechnungen, fällige Lieferantenrechnungen
- [x] Marge pro Auftrag (invoiced total vs. Zeitkosten), Stunden pro Auftrag
- [x] **USt-Vorschau**: Soll-USt − Vorsteuer = Zahllast für Periodenauswahl
- [x] **Steuerberater-Export** (zentral, weil das die laufende Schnittstelle ist):
      - Periodenwahl (Monat / Quartal / Jahr)
      - **Pro Sparte aufgeschlüsselt**, aber als ein Export-Bundle
        (Bau und Huf gehören demselben Unternehmen, der Steuerberater erkennt die
        Trennung über die Spalte `tenant_code`)
      - Zip-Bundle mit:
        - `ausgangsrechnungen.csv` (Datum, Rechnungs-Nr., Sparte, Kunde, Netto,
          USt-Satz, USt, Brutto, Zahlung am, Status)
        - `eingangsrechnungen.csv` (Datum, Lieferant, externe Nr., Sparte/Auftrag,
          Netto, USt, Brutto, Zahlung am, Paperless-Doc-ID)
        - `gutschriften.csv`
        - `zahlungen.csv`
        - `belege/` Ordner mit allen PDFs aus dem Zeitraum
        - `manifest.json` mit Hashes (für GoBD-Nachvollziehbarkeit)
      - Optional: DATEV-CSV-Format (im Backlog, sobald der StB sagt was er bevorzugt)
- [x] USt-Vorschau (Soll-USt fällig, Vorsteuer aus Eingangsrechnungen)

### Phase 7 – LLM-Komfort ✅ Basis abgeschlossen (2026-05-09)
- [x] `services/ollama.py` erweitert um `suggest_position()` + `split_to_positions()`
- [x] Use-Case 1: **„Stichworte → ausformulierte Position”** — `POST /llm/suggest-position`
- [x] Use-Case 2: „Freitext → mehrere Positionen” — `POST /llm/split-positions`
- [x] KI-Assistent-Widget im QuoteEditorPage (Stichwörter + Aufteilen, graceful wenn offline)
- [x] `GET /llm/models` — verfügbare Ollama-Modelle
- [ ] Use-Case 3: Mahn-/Anschreiben-Entwurf
- [ ] Use-Case 4: Hufbefund strukturieren (für Mandant `huf`)
- [ ] Use-Case 5: Embeddings auf `position_history` für Ähnlichkeitsvorschläge

### Phase 8 – Härtung & Finanzschnittstellen ✅ Basis abgeschlossen (2026-05-09)
- [x] **EÜR-Vorschau** (Zufluss-/Abflussprinzip): Einnahmen, Ausgaben, Gewinn/Verlust
- [x] Eingangsrechnungen im Steuerberater-Export-ZIP (`eingangsrechnungen.csv`)
- [x] GET /reports/eur — EÜR-Vorschau API-Endpoint
- [ ] Backups (pg_dump nightly, Dokumente in Paperless bleiben dort gesichert)
- [ ] Rollen-/Berechtigungslogik, falls Mehrbenutzer kommen
- [ ] **FinTS/HBCI-Anbindung** für Zahlungsabgleich (Kontoumsätze → Match auf
      `Payment.bank_ref`). **Bewusst hier**, nicht früher — Phase 4 erfasst
      Zahlungen so lange manuell.
- [ ] DATEV-CSV-Variante des Steuerberater-Exports (sobald StB-Format bekannt)
- [ ] Peppol-Versand für E-Rechnungen (optional)

### n8n entfernt – direkter Paperless-Webhook ✅ abgeschlossen (2026-05-10)
- [x] n8n komplett aus docker-compose entfernt (war nie aktiv, nicht nötig)
- [x] `scripts/paperless-notify.sh`: Post-Consume-Script für Paperless-ngx
- [x] Neuer Endpoint `POST /supplier-invoices/paperless-hook/{id}`:
      - Kein JWT nötig — nur `X-Internal-Token` + `X-Tenant-ID` Header
      - `INTERNAL_PAPERLESS_TOKEN` in config.py + .env
- [x] `PAPERLESS_DEFAULT_TENANT_ID` steuert Mandantenzuordnung
- [x] Paperless ruft miniERP vollautomatisch nach Dokumentenverarbeitung auf

### Profil & Passwort-Änderung ✅ abgeschlossen (2026-05-10)
- [x] `POST /auth/change-password`: aktuelles PW prüfen, neues setzen (min. 8 Zeichen)
- [x] Profil-Menü im App-Header (Account-Icon): E-Mail, Passwort ändern, Abmelden
- [x] auth-Store: user-Objekt (email) nach Login persistent gespeichert

### Phase 10 – Rechnungsworkflow: Teil- & Schlussrechnung ✅ abgeschlossen (2026-05-10)
- [x] **Stunden im Angebot**: „Stunden"-Schnell-Button im Angebots-Editor (pre-filled unit=h, 19% MwSt.)
- [x] **Positionsselektion**: Dialog Auftrag→Rechnung zeigt Angebots-Positionen als Checkliste
      bei Teil-/Abschlagsrechnungen — bereits abgerechnete Positionen sind deaktiviert
- [x] **Doppelte Abrechnung verhindern**: `InvoiceItem.quote_item_id` FK trackt Herkunft;
      neue Teil-/Abschlagsrechnungen schließen bereits verrechnete Positionen automatisch aus
- [x] **Vorleistungen in Schlussrechnung**: `Invoice.prior_invoiced_total` summiert alle
      nicht-stornierten Teil-/Abschlagsrechnungen des Auftrags; PDF weist den Abzug aus
- [x] PDF: Rechnungsart-Label (Teilrechnung / Abschlagsrechnung / Rechnung) im Dokumenttitel
- [x] Migration `0010`: `invoice_items.quote_item_id` FK + `invoices.prior_invoiced_total`

### Gruppen in Rechnung + Stunden auf Gruppen buchen ✅ abgeschlossen (2026-05-10)
- [x] **Gruppen aus dem Angebot in die Rechnung übernehmen**: `InvoiceItem` bekommt das
      Feld `group_label` (VARCHAR 200, nullable). Beim `POST /orders/{id}/to-invoice` wird
      das Label aus der `QuoteGroup.title` des zugehörigen `QuoteItem.group_id` übernommen.
      Positionen ohne Gruppe erhalten `NULL`. PDF-Templates können damit Gruppen-Überschriften
      und Zwischensummen pro Gruppe rendern.
- [x] **Stunden auf Gruppen buchen**: `TimeEntry` bekommt `quote_group_id` (FK →
      `quote_groups.id`, ON DELETE SET NULL). In der Stundenerfassung erscheint ein
      Gruppen-Picker sobald der ausgewählte Auftrag ein Angebot mit Gruppen hat.
      `GET /orders/{id}/groups` liefert die Gruppen des Auftrags.
- [x] **Anzeige in der Wochenansicht**: `TimeEntryRead` enthält `quote_group_title` (aus
      der eager-geladenen Beziehung); der globale `/time-entries`-Endpoint lädt die
      Gruppe per `selectinload`, sodass alle Wocheneinträge ihre Gruppe direkt tragen.
- [x] Migration `0011`: `invoice_items.group_label`, `time_entries.quote_group_id`

### Bugfix: Stundenerfassung – Werte immer 0 ✅ abgeschlossen (2026-05-10)
- [x] **Root cause**: FastAPI-Route `GET /orders/time-entries` war hinter `GET /orders/{order_id}`
      registriert → Starlette matched `"time-entries"` als `order_id`-Pfadparameter (int),
      gibt 422 zurück, der `/time-entries`-Handler wurde nie erreicht
- [x] Fix: `/time-entries`-Route vor alle `/{order_id}`-Routen verschoben
      (`backend/app/api/v1/endpoints/orders.py`)
- [x] Frontend-Catch `{ entries.value = [] }` hat den Fehler still geschluckt → alle
      Statistiken blieben bei 0.0 h

### Mandanten-Konfiguration via .env (TODO)
Ziel: miniERP ohne Code-Änderungen für beliebige Betriebe verwendbar.

- [ ] Mandantendaten (Name, Code, Adresse, IBAN, Nummernpräfixe) vollständig aus `.env` lesen
      statt hardcoded im Seed-Script (`app/main.py`):
      ```
      TENANT1_CODE=bau
      TENANT1_NAME=Muster Bauunternehmen
      TENANT1_ADDRESS=...
      TENANT1_IBAN=DE89...
      TENANT1_INVOICE_PREFIX=R
      TENANT1_QUOTE_PREFIX=A
      TENANT2_CODE=huf        ← leer = kein zweiter Mandant
      TENANT2_NAME=...
      ```
- [ ] `app/core/config.py`: neue Settings-Felder `TENANT1_*` / `TENANT2_*`
- [ ] `app/main.py` Seed-Funktion: liest Werte aus Settings statt Literale
- [ ] Unterstützung für Einzelbetrieb (TENANT2_CODE leer → nur ein Mandant)
- [ ] `.env.example` + README dokumentieren die neuen Variablen
- [ ] Bestehende Daten bleiben erhalten (Migration-safe: nur beim ersten Start / leerem DB)

### Phase 9 – E-Mail-Integration (TODO)
- [ ] **SMTP-Versand**: Angebote und Rechnungen direkt als PDF per E-Mail versenden
      - `POST /quotes/{id}/send-email` — Angebot an Kunde senden
      - `POST /invoices/{id}/send-email` — Rechnung an Kunde senden
      - SMTP-Konfiguration in `.env` (Host, Port, TLS, User, Password)
      - E-Mail-Template (Jinja2) pro Sparte und Belegart
      - Versandstatus und Zeitstempel auf Quote/Invoice speichern
- [ ] **POP3/IMAP-Abruf**: Eingehende E-Mails auf Lieferantenrechnungen prüfen
      - Anhänge (PDF) automatisch aus E-Mails extrahieren
      - PDF → Paperless-ngx hochladen → OCR → Ollama-Strukturierung
      - Entwurf `SupplierInvoice` automatisch anlegen
      - Konfiguration: POP3/IMAP-Host, Port, SSL, Credentials in `.env`
- [ ] E-Mail-Archivierung: Versendete E-Mails in Paperless ablegen (optional)

## 4. Out of Scope (vorerst)
- Kassensystem, Lagerverwaltung mit Beständen, Filialen
- Mehrwährungsfähigkeit
- Personalabrechnung
- **Mieteinnahmen / Vermietung & Verpachtung** — gehört steuerlich nicht ins
  Gewerbe und wird nicht im miniERP geführt. Der Steuerberater erhält die
  Mieten weiterhin außerhalb von miniERP.
- **Buchhaltung im engeren Sinn** (Konten, Belegbuchung, EÜR-Erstellung) —
  miniERP liefert nur den sauber getrennten Export, der Steuerberater bucht.
- **Mobile Native App** — bewusst nicht: Vue3 + Vuetify wird als **PWA** ausgeliefert
  (Handy für Stundenerfassung & Belegfoto, Tablet beim Kunden, Desktop für Buchhaltung).
  Native App lohnt erst bei echtem Hardware-Bedarf (z. B. NFC).

## 5. Risiken / offene Punkte
- **Rechtliches / GoBD**: Aufbewahrung 10 Jahre, Unveränderlichkeit, Nachvollziehbarkeit.
  Adressiert über Hash-PDFs, append-only `audit_log`, Storno/Gutschrift statt Update.
  Mit Steuerberater abnicken lassen.
- **Nummernkreise**: lückenlos je Mandant + Belegart + Jahr; transaktional, nur Stornos.
- **PDF-Layout**: Briefpapier-Vorlage von der Inhaberin nötig (Logo, Fußzeile, IBAN, USt-ID,
  Kleinunternehmer-Hinweis falls einschlägig).
- **OCR-Qualität**: Schlechte Scans → schlechte Strukturierung. Immer mit manueller
  Bestätigung; Tesseract + Bildvorverarbeitung (Deskew, Contrast) vorschalten.
- **E-Rechnung-Validierung**: Erzeugte XRechnung/ZUGFeRD gegen offizielle Validatoren testen
  (z. B. KoSIT-Validator) bevor scharf geschaltet.

## 6. Getroffene Entscheidungen

1. **Rechtsform & USt**: Einzelunternehmerin, beide Sparten gehören steuerlich zu **einem**
   Unternehmen. §19-UStG-Status gilt fürs Gesamtunternehmen (am `Company`-Datensatz),
   **nicht** pro Sparte. Bei B2B im Baubereich realistischerweise regelbesteuert.
   → Im PDF wird der Hinweistext zentral aus `Company.is_small_business` abgeleitet.
2. **Mieteinnahmen**: separate Einkunftsart (V+V), liegen außerhalb von miniERP.
   Wird **nicht** mit erfasst.
3. **Steuerberater-Export**: Nicht-Ziel ist DATEV/EÜR-Buchung im miniERP. Ziel ist ein
   sauber getrennter, exportierbarer Auszug pro Periode (siehe neue Phase 6).
4. **FinTS/HBCI**: Schema wird vorbereitet (`Payment.bank_ref`, Felder in `Company`),
   Implementierung erfolgt **später**. Phase 4 erfasst Zahlungen vorerst manuell.
5. **Belegablage**: **Paperless-ngx** ist Default-Speicher. Begründung: REST-API mit
   strukturierten Metadaten (Korrespondent, Dokumenttyp, Tags, Custom Fields), eingebaute
   OCR, Volltextsuche, Webhooks bei neuen Dokumenten. Nextcloud bleibt verfügbar als
   Consume-Ordner / Briefpapier-Share, ist aber nicht primärer Belegspeicher.
6. **PDF-Engine**: **Gotenberg** als Sidecar. Backend rendert Jinja-HTML, Gotenberg liefert
   PDF/A zurück. WeasyPrint entfällt damit.

## 7. Nächste Schritte
1. Mit dem Steuerberater abstimmen, welches Export-Format ideal ist
   (CSV-Spalten, ggf. DATEV) — beeinflusst die Felder in Phase 6.
2. Briefpapier-Daten und je ein Beispielangebot/-rechnung pro Sparte sammeln
   (für die Gotenberg-Templates).
3. Paperless-ngx auf API-Token vorbereiten und Custom Fields anlegen
   (`auftrag_no`, `rechnung_no`, `sparte`).
4. Phase 0 umsetzen.

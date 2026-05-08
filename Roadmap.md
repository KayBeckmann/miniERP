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
| Mandanten      | 2 Mandanten (`Bau`, `Hufbearbeitung`), je eigene Nummernkreise und Templates |
| PDF            | WeasyPrint + Jinja2-HTML/CSS-Templates pro Mandant                           |
| Dokumentablage | Paperless-ngx (REST) ODER Nextcloud (WebDAV), konfigurierbar                 |
| Automation     | n8n via Webhooks ins Backend (keine Geschäftslogik in n8n)                   |
| LLM            | Ollama (lokal), Backend-Service als alleiniger Konsument                     |
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
- **Tenant**: `id`, `code` (`bau` / `huf`), `name`, `address`, `tax_id`, `iban`, `logo_path`,
  `invoice_number_prefix`, `quote_number_prefix`, `pdf_template`.
- **User**: `id`, `email`, `password_hash`, `role`, `default_tenant_id`.
- **Customer**: `id`, `tenant_id`, `customer_no`, `kind` (Privat/Geschäft), `name`, `contact`,
  `address`, `email`, `phone`, `tax_id`, `notes`, `created_at`.
- **Supplier**: `id`, `tenant_id`, `name`, `address`, `iban`, `default_payment_terms`.
- **Material**: `id`, `tenant_id`, `sku`, `name`, `description`, `unit` (Stk/m/m²/h/…),
  `purchase_price`, `sale_price`, `vat_rate`, `category`, `active`.
- **NumberSequence**: `tenant_id`, `kind` (quote/invoice/order), `year`, `next_value`.

### Angebote / Aufträge / Rechnungen
- **Quote**: `id`, `tenant_id`, `customer_id`, `quote_no`, `date`, `valid_until`, `status`
  (draft/sent/accepted/declined/expired), `subtotal`, `vat_total`, `total`,
  `notes`, `internal_notes`, `pdf_path`, `version`.
- **QuoteItem**: `id`, `quote_id`, `position`, `material_id?`, `description`, `qty`,
  `unit`, `unit_price`, `discount_pct`, `vat_rate`, `line_total`.
- **Order**: `id`, `tenant_id`, `customer_id`, `quote_id?`, `order_no`, `title`,
  `status` (open/in_progress/done/cancelled), `start_date`, `end_date`,
  `budget_hours`, `budget_material`.
- **Invoice**: `id`, `tenant_id`, `customer_id`, `order_id?`, `invoice_no`, `date`,
  `due_date`, `kind` (final/partial/advance/credit), `status` (draft/sent/paid/overdue/cancelled),
  `subtotal`, `vat_total`, `total`, `paid_amount`, `paid_at`, `pdf_path`.
- **InvoiceItem**: analog `QuoteItem`.
- **TimeEntry**: `id`, `order_id`, `user_id`, `date`, `hours`, `description`,
  `hourly_rate?`, `billable` (bool), `invoiced` (bool).
- **SupplierInvoice**: `id`, `tenant_id`, `supplier_id`, `order_id?`, `external_no`,
  `date`, `due_date`, `subtotal`, `vat_total`, `total`, `paid_at`, `document_id`
  (Paperless-/Nextcloud-Referenz), `ocr_payload` (jsonb).
- **Document**: `id`, `tenant_id`, `kind`, `ref_table`, `ref_id`, `storage` (paperless/nextcloud/local),
  `external_id`, `path`, `created_at`.

### Beziehungen (vereinfacht)
```
Tenant 1─* Customer 1─* Quote 1─* QuoteItem
                       └── Order 1─* TimeEntry
                                └── 1─* Invoice 1─* InvoiceItem
                                └── *─1 SupplierInvoice (über order_id)
```

Detaillierte ER-Diagramme folgen unter `docs/datamodel.md`.

## 3. Phasen-Roadmap

Jede Phase endet mit einem **lauffähigen Stand** (build grün, manueller Smoketest).

### Phase 0 – Projektgerüst (≈ 0,5 Tage)
- [ ] `docker-compose.yml` mit `postgres`, `backend`, `frontend` (n8n/ollama optional aus)
- [ ] FastAPI-Skeleton mit `/health`, JWT-Login (1 Seed-User), Settings via `pydantic-settings`
- [ ] Alembic initialisiert, `Tenant` + `User` als erste Migration, Seed `bau` + `huf`
- [ ] Vue 3 + Vuetify 3 + Vite-Skeleton mit Login-Seite und Mandantenwahl im Header
- [ ] `ruff`, `black`, `eslint`, `prettier`, GitHub-Actions-Workflow (lint + tests)

### Phase 1 – Stammdaten (≈ 1–2 Tage)
- [ ] CRUD: Customer, Supplier, Material (Backend + Frontend)
- [ ] Such-/Filterfelder, Pagination, Sortierung
- [ ] Import CSV für Material (einmalige Befüllung aus Altdaten)
- [ ] Mandanten-Scope strikt im Backend erzwingen (DB-Filter + Tests)

### Phase 2 – Angebote (≈ 2–3 Tage)
- [ ] Quote + QuoteItem CRUD, Positions-Editor (Drag/Drop, Material-Lookup, Freitext)
- [ ] Berechnung Netto/USt/Brutto pro Position + Summen serverseitig (single source of truth)
- [ ] Nummernkreise pro Mandant + Jahr (`NumberSequence`, transaktional)
- [ ] PDF-Template `Bau` und `Huf`, WeasyPrint, Vorschau im Browser
- [ ] Status-Workflow (draft → sent → accepted/declined)
- [ ] Versand per Mail (SMTP) als optionaler Schritt

### Phase 3 – Aufträge + Stunden (≈ 1–2 Tage)
- [ ] Order entsteht aus akzeptiertem Angebot (Kopie der Positionen als Soll)
- [ ] TimeEntry-Erfassung: Wochenansicht + Schnellbuchung mobil (Vuetify)
- [ ] Soll/Ist-Auswertung pro Auftrag

### Phase 4 – Ausgangsrechnungen (≈ 2 Tage)
- [ ] Rechnung aus Auftrag (anteilig nach Stunden/Material) oder aus Angebot (1:1)
- [ ] Teil-/Schluss-/Abschlagsrechnung, Gutschrift
- [ ] PDF analog zu Angeboten, eigene Templates, ZUGFeRD/X-Rechnung später (Backlog)
- [ ] Zahlungseingang erfassen, OP-Liste

### Phase 5 – Lieferantenrechnungen (≈ 1–2 Tage)
- [ ] Upload-Form, Speicherung in Paperless-ngx **oder** Nextcloud (Adapter-Pattern)
- [ ] Zuordnung zu Auftrag und/oder Materialposition
- [ ] OCR-Vorbefüllung via n8n-Webhook (Paperless liefert Text → Backend ruft Ollama →
      strukturiertes JSON → User bestätigt)

### Phase 6 – Auswertungen & Dashboard (≈ 1 Tag)
- [ ] Offene Angebote, offene Rechnungen, fällige Lieferantenrechnungen
- [ ] Marge pro Auftrag, Stunden pro Kunde/Monat
- [ ] USt-Vorschau für den Steuerberater (CSV-/PDF-Export)

### Phase 7 – LLM-Komfort (≈ 1–2 Tage)
- [ ] Service `services/llm.py` als einziger Ollama-Client
- [ ] Use-Case 1: „Freitext → Angebotspositionen“ (Vorschlag, Mensch bestätigt)
- [ ] Use-Case 2: Mahn-/Anschreiben-Entwurf
- [ ] Use-Case 3: Hufbefund strukturieren (für Mandant `huf`)
- [ ] Prompt-Templates versioniert in `backend/app/services/prompts/`

### Phase 8 – Härtung
- [ ] Backups (pg_dump nightly, Dokumente in Paperless/Nextcloud sind dort gesichert)
- [ ] Rollen-/Berechtigungslogik, falls Mehrbenutzer kommen
- [ ] E-Rechnung (XRechnung/ZUGFeRD) für Geschäftskunden
- [ ] DATEV-Export der Rechnungen

## 4. Out of Scope (vorerst)
- Kassensystem, Lagerverwaltung mit Beständen, Filialen
- Mehrwährungsfähigkeit
- Personalabrechnung
- Mobile Native App (nur responsive Web)

## 5. Risiken / offene Punkte
- **Rechtliches**: GoBD-konforme Aufbewahrung. Paperless-ngx erfüllt Auffindbarkeit/Unveränderlichkeit
  in der Praxis; rechtssichere Archivierung mit Steuerberater abstimmen.
- **Nummernkreise**: müssen lückenlos sein — transaktional erzeugen, Stornos statt Löschungen.
- **PDF-Layout**: Briefpapier-Vorlage von der Inhaberin nötig (Logo, Fußzeile, IBAN, USt-ID).
- **OCR-Qualität**: Bei schlechten Scans liefert Ollama-Strukturierung Müll; immer mit
  manueller Bestätigung absichern.

## 6. Nächste Schritte
1. Roadmap reviewen, Phasen priorisieren / verschieben.
2. Briefpapier-Daten und Beispielangebot/-rechnung sammeln (für PDF-Templates).
3. Phase 0 umsetzen.

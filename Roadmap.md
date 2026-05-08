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
| PDF            | WeasyPrint **oder** Gotenberg-Sidecar (HTTP, HTML/Jinja → PDF). Default: WeasyPrint im Backend; Gotenberg, falls komplexere Layouts nötig. |
| Dokumentablage | Paperless-ngx (REST) ODER Nextcloud (WebDAV), konfigurierbar; optional MinIO-Bucket als zusätzliche Backend-Option für PDF-Originale |
| Automation     | n8n via Webhooks ins Backend (keine Geschäftslogik in n8n; n8n macht **nicht** die REST-API) |
| LLM            | Ollama (lokal), Backend-Service als alleiniger Konsument; OpenAI-Fallback nur per Config-Schalter, default aus |
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
- **Tenant**: `id`, `code` (`bau` / `huf`), `name`, `address`, `tax_id`, `iban`, `logo_path`,
  `invoice_number_prefix`, `quote_number_prefix`, `pdf_template`.
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

### Phase 0 – Projektgerüst (≈ 0,5 Tage)
- [ ] `docker-compose.yml` mit `postgres`, `backend`, `frontend` (n8n/ollama optional aus)
- [ ] FastAPI-Skeleton mit `/health`, JWT-Login (1 Seed-User), Settings via `pydantic-settings`
- [ ] Alembic initialisiert, `Tenant` + `User` als erste Migration, Seed `bau` + `huf`
- [ ] Vue 3 + Vuetify 3 + Vite-Skeleton mit Login-Seite und Mandantenwahl im Header
- [ ] `ruff`, `black`, `eslint`, `prettier`, GitHub-Actions-Workflow (lint + tests)

### Phase 1 – Stammdaten (≈ 1–2 Tage)
- [ ] CRUD: Customer (mit `is_business`, `e_invoice_format`, `leitweg_id?`), Supplier
- [ ] Material/Article CRUD **als optionales Modul** (für Pauschalen wie Anfahrt,
      Standard-Hufkorrektur). Kein Pflichtfeld in Belegen.
- [ ] Such-/Filterfelder, Pagination, Sortierung
- [ ] CSV-Import für Material (nur falls überhaupt Altdaten existieren — sonst überspringen)
- [ ] Mandanten-Scope strikt im Backend erzwingen (DB-Filter + Tests)

### Phase 2 – Angebote (≈ 2–3 Tage)
- [ ] Quote + QuoteItem CRUD, Positions-Editor mit **Freitext als Default**
- [ ] Quick-Reuse: „Letzte 30 Positionen“, „Aus Angebot X übernehmen“
- [ ] `position_history` befüllen (für späteres Lazy-Stamm + Embeddings)
- [ ] Optionaler Material-Lookup (nur falls Stammartikel vorhanden)
- [ ] Berechnung Netto/USt/Brutto pro Position + Summen serverseitig (single source of truth)
- [ ] Nummernkreise pro Mandant + Jahr + Belegart (`NumberSequence`, transaktional)
- [ ] PDF-Template `Bau` und `Huf`, WeasyPrint, Vorschau im Browser
- [ ] Status-Workflow (draft → sent → accepted/declined → in Auftrag gewandelt)
- [ ] Versand per Mail (SMTP) als optionaler Schritt

### Phase 3 – Aufträge + Stunden (≈ 1–2 Tage)
- [ ] Order entsteht aus akzeptiertem Angebot (Kopie der Positionen als Soll)
- [ ] Auftragsbestätigungs-PDF (eigener Belegtyp, eigener Nummernkreis)
- [ ] TimeEntry-Erfassung: Wochenansicht + Schnellbuchung mobil (Vuetify, PWA-tauglich)
- [ ] Soll/Ist-Auswertung pro Auftrag (Stunden + Material)

### Phase 4 – Ausgangsrechnungen (≈ 2–3 Tage)
- [ ] Rechnung aus Auftrag (anteilig nach Stunden/Material) oder aus Angebot (1:1)
- [ ] Teil-/Abschlags-/Schlussrechnung
- [ ] **Gutschrift als eigener Belegtyp** (Storno- statt Lösch-Pfad)
- [ ] PDF analog zu Angeboten, eigene Templates, `pdf_sha256` festschreiben
- [ ] **E-Rechnung Kern, nicht Backlog**: XRechnung (UBL) und ZUGFeRD 2.x abhängig vom
      Customer-Flag erzeugen; mehrere Zahlungen je Rechnung (`Payment` 1:n)
- [ ] Zahlungseingang manuell erfassen, OP-Liste, Mahnstufen-Felder vorbereiten

### Phase 5 – Lieferantenrechnungen (≈ 1–2 Tage)
- [ ] Upload-Form (auch Foto vom Smartphone), Speicherung in Paperless-ngx **oder**
      Nextcloud **oder** MinIO (Adapter-Pattern, Default Paperless)
- [ ] Zuordnung zu Auftrag und/oder Position
- [ ] **OCR-Pipeline**:
      - PDFs mit Textlayer: Text direkt entnehmen
      - Fotos / textlose PDFs: **Tesseract** vorgeschaltet
      - Text → Ollama-Service → strukturiertes JSON (Lieferant, Datum, Rechnungsnummer,
        Netto/USt/Brutto, Fälligkeit) → Vorschlag im Formular, User bestätigt
- [ ] Trigger-Variante: Paperless erkennt neuen Beleg → n8n-Workflow → Backend-Endpoint

### Phase 6 – Auswertungen & Dashboard (≈ 1 Tag)
- [ ] Offene Angebote, offene Rechnungen, fällige Lieferantenrechnungen
- [ ] Marge pro Auftrag, Stunden pro Kunde/Monat
- [ ] USt-Vorschau für den Steuerberater (CSV-/PDF-Export)

### Phase 7 – LLM-Komfort (≈ 1–2 Tage)
- [ ] Service `services/llm.py` als einziger Ollama-Client
- [ ] Use-Case 1: **„Stichworte → ausformulierte Position“** (ersetzt Stammartikel im Alltag)
- [ ] Use-Case 2: „Freitext-Beschreibung → mehrere Positionen“ (Vorschlag, Mensch bestätigt)
- [ ] Use-Case 3: Mahn-/Anschreiben-Entwurf
- [ ] Use-Case 4: Hufbefund strukturieren (für Mandant `huf`)
- [ ] Use-Case 5: Embeddings auf `position_history` für Ähnlichkeitsvorschläge
- [ ] Prompt-Templates versioniert in `backend/app/services/prompts/`

### Phase 8 – Härtung & Finanzschnittstellen
- [ ] Backups (pg_dump nightly, Dokumente in Paperless/Nextcloud/MinIO bleiben dort)
- [ ] Rollen-/Berechtigungslogik, falls Mehrbenutzer kommen
- [ ] **FinTS/HBCI-Anbindung** für Zahlungsabgleich (Kontoumsätze → Match auf
      `Payment.bank_ref`); abhängig von Entscheidung „jetzt oder später“
- [ ] DATEV-Export der Rechnungen + EÜR-Vorschau
- [ ] Peppol-Versand für E-Rechnungen (optional)

## 4. Out of Scope (vorerst)
- Kassensystem, Lagerverwaltung mit Beständen, Filialen
- Mehrwährungsfähigkeit
- Personalabrechnung
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

## 6. Offene Entscheidungen (vor / während Phase 0)
1. **§19 UStG (Kleinunternehmerregelung)** — pro Sparte einzeln zu klären:
   - Bauunternehmen: vermutlich regelbesteuert (B2B).
   - Hufbearbeitung: häufig Kleinunternehmer.
   Bestimmt USt-Anzeige, Pflichttext im PDF, Verhalten der `vat_rate`-Felder.
2. **FinTS/HBCI-Anbindung** jetzt mitdenken (Phase 4/8) oder später nachrüsten?
   Beeinflusst nur Felder in `Payment` (`bank_ref`), das Schema bleibt vorbereitet.
3. **Ablage-Default**: Paperless-ngx vs. Nextcloud vs. MinIO — was läuft schon, was soll laufen?
4. **PDF-Engine**: WeasyPrint im Backend (einfach) vs. Gotenberg-Sidecar (mächtiger).
   Default WeasyPrint, Wechsel später möglich.

## 7. Nächste Schritte
1. Roadmap reviewen, offene Entscheidungen aus Abschnitt 6 beantworten.
2. Briefpapier-Daten und je ein Beispielangebot/-rechnung pro Sparte sammeln (für PDF-Templates).
3. Phase 0 umsetzen.

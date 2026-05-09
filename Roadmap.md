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
- [x] Quick-Reuse: „Letzte 30 Positionen“, „Aus Angebot X übernehmen“
- [x] `position_history` befüllen (für späteres Lazy-Stamm + Embeddings)
- [x] Optionaler Material-Lookup (nur falls Stammartikel vorhanden)
- [x] Berechnung Netto/USt/Brutto pro Position + Summen serverseitig (single source of truth)
- [x] Nummernkreise pro Mandant + Jahr + Belegart (`NumberSequence`, transaktional)
- [x] PDF-Template `Bau` und `Huf`, **Gotenberg** (HTML/Jinja → PDF/A), Vorschau im Browser
- [x] Status-Workflow (draft → sent → accepted/declined → in Auftrag gewandelt)
- [x] Versand per Mail (SMTP) als optionaler Schritt

### Phase 3 – Aufträge + Stundenerfassung ✅ abgeschlossen (2026-05-09)
- [x] Order entsteht aus akzeptiertem Angebot (Kopie der Positionen als Soll)
- [x] Auftragsbestätigungs-PDF (eigener Belegtyp, eigener Nummernkreis)
- [x] TimeEntry-Erfassung: Wochenansicht + Schnellbuchung mobil (Vuetify, PWA-tauglich)
- [x] Soll/Ist-Auswertung pro Auftrag (Stunden + Material)

### Phase 4 – Ausgangsrechnungen ✅ abgeschlossen (2026-05-09)
- [x] Rechnung aus Auftrag (anteilig nach Stunden/Material) oder aus Angebot (1:1)
- [x] Teil-/Abschlags-/Schlussrechnung
- [x] **Gutschrift als eigener Belegtyp** (Storno- statt Lösch-Pfad)
- [x] PDF analog zu Angeboten, eigene Templates, `pdf_sha256` festschreiben
- [x] **E-Rechnung Kern, nicht Backlog**: XRechnung (UBL) und ZUGFeRD 2.x abhängig vom
      Customer-Flag erzeugen; mehrere Zahlungen je Rechnung (`Payment` 1:n)
- [x] Zahlungseingang **manuell** erfassen (FinTS folgt später, Schema bleibt vorbereitet),
      OP-Liste, Mahnstufen-Felder vorbereiten

### Phase 5 – Lieferantenrechnungen (≈ 1–2 Tage)
- [ ] Upload-Form (auch Foto vom Smartphone) → Backend reicht direkt an
      **Paperless-ngx** durch (`POST /api/documents/post_document/`), Rückgabe ist
      `document_id`, im miniERP gespeichert in `Document.external_id`
- [ ] OCR macht **Paperless** (eingebaut) — Volltext per `/api/documents/{id}/`
- [ ] **Strukturierung via Ollama**: Volltext aus Paperless → Ollama-Service →
      JSON (Lieferant, Datum, Rechnungsnummer, Netto/USt/Brutto, Fälligkeit) →
      Vorschlag im Formular, User bestätigt
- [ ] Tesseract nur als Fallback, falls Paperless-OCR nicht ausreicht (z. B. extern
      eingespielte Belege ohne OCR)
- [ ] Paperless-Webhook bei neuem Dokument → n8n → Backend-Endpoint
      (`/supplier-invoices/from-paperless/{document_id}`) erzeugt Entwurf automatisch
- [ ] Custom Fields in Paperless setzen: `auftrag_no`, `rechnung_no` (rückverweisend)
- [ ] Nextcloud-Adapter bleibt im Code als zweite Implementierung des `DocumentStore`-Interfaces,
      ist aber **nicht** der Default

### Phase 6 – Auswertungen & Steuerberater-Export ✅ Basis abgeschlossen (2026-05-09)
- [ ] Offene Angebote, offene Rechnungen, fällige Lieferantenrechnungen
- [ ] Marge pro Auftrag, Stunden pro Kunde/Monat
- [ ] **Steuerberater-Export** (zentral, weil das die laufende Schnittstelle ist):
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
- [ ] USt-Vorschau (Soll-USt fällig, Vorsteuer aus Eingangsrechnungen)

### Phase 7 – LLM-Komfort (≈ 1–2 Tage)
- [ ] Service `services/llm.py` als einziger Ollama-Client
- [ ] Use-Case 1: **„Stichworte → ausformulierte Position“** (ersetzt Stammartikel im Alltag)
- [ ] Use-Case 2: „Freitext-Beschreibung → mehrere Positionen“ (Vorschlag, Mensch bestätigt)
- [ ] Use-Case 3: Mahn-/Anschreiben-Entwurf
- [ ] Use-Case 4: Hufbefund strukturieren (für Mandant `huf`)
- [ ] Use-Case 5: Embeddings auf `position_history` für Ähnlichkeitsvorschläge
- [ ] Prompt-Templates versioniert in `backend/app/services/prompts/`

### Phase 8 – Härtung & Finanzschnittstellen
- [ ] Backups (pg_dump nightly, Dokumente in Paperless bleiben dort gesichert)
- [ ] Rollen-/Berechtigungslogik, falls Mehrbenutzer kommen
- [ ] **FinTS/HBCI-Anbindung** für Zahlungsabgleich (Kontoumsätze → Match auf
      `Payment.bank_ref`). **Bewusst hier**, nicht früher — Phase 4 erfasst
      Zahlungen so lange manuell.
- [ ] DATEV-CSV-Variante des Steuerberater-Exports (sobald StB-Format bekannt)
- [ ] EÜR-Vorschau auf Basis der Exportdaten
- [ ] Peppol-Versand für E-Rechnungen (optional)

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

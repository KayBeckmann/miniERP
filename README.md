# miniERP

Kleines, selbst gebautes ERP für ein Bauunternehmen mit zweitem Standbein
Hufbearbeitung. Ziel: Angebote, Aufträge, Ausgangs- und Eingangsrechnungen,
Stundenerfassung und einfache Auswertungen – ohne den Pflegeaufwand eines
klassischen Materialstamms.

> Status: in Planung. Architektur und Phasenplan stehen, Implementierung
> startet mit Phase 0 (Projektgerüst). Details siehe [`Roadmap.md`](./Roadmap.md).

## Idee

Die Inhaberin schreibt ihre Angebote bisher per Hand in LibreOffice Writer.
Wiederholungen im Material gibt es kaum, eine klassische Stammpflege wäre
teurer als der Nutzen. miniERP setzt deshalb auf:

- **Freitext-first Positionen**: Beschreibung + Menge + Preis genügt; ein
  Materialstamm wächst optional aus tatsächlich wiederkehrenden Einträgen.
- **Zwei Mandanten** (`bau`, `huf`) auf einer Codebasis – eigene
  Nummernkreise, Templates und Auswertungen.
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
| PDF            | WeasyPrint (Default) oder Gotenberg-Sidecar                   |
| OCR            | Tesseract → Ollama-Strukturierung                             |
| LLM            | Ollama (lokal), z. B. `llama3.1` / `qwen2.5` / `mistral`      |
| Dokumentablage | Paperless-ngx · Nextcloud · MinIO (Adapter, konfigurierbar)   |
| Automation     | n8n via Webhooks (keine Geschäftslogik in n8n)                |
| Container      | docker-compose                                                |

## Geplante Module

- Stammdaten: Kunden, Lieferanten, optionaler Materialstamm
- Angebote → Aufträge → Auftragsbestätigung → Rechnung (Teil/Abschlag/Schluss) → Gutschrift
- Stundenerfassung (mobil-tauglich)
- Lieferantenrechnungen mit OCR-Vorbefüllung und Auftragszuordnung
- Auswertungen: Offene Posten, Margen pro Auftrag, Stunden, USt-Vorschau
- Spätere Ausbaustufen: FinTS-Zahlungsabgleich, DATEV-Export, Peppol-Versand

Genauer Phasenplan und Datenmodell stehen in der [`Roadmap.md`](./Roadmap.md).

## Repo-Struktur (Zielbild)

```
miniERP/
├── backend/          FastAPI, Alembic, Tests
├── frontend/         Vue 3 + Vuetify 3 (PWA)
├── n8n/workflows/    exportierte Workflows
├── templates/pdf/    HTML/CSS-Templates pro Mandant
├── docs/             Datenmodell, ADRs
├── docker-compose.yml
├── Roadmap.md
└── README.md
```

Aktuell ist nur die Roadmap im Repo – Code folgt mit Phase 0.

## Entwicklung

Sobald Phase 0 umgesetzt ist, läuft die lokale Umgebung über
`docker-compose up`. Bis dahin gibt es noch nichts zu starten.

## Lizenz

Siehe [`LICENSE`](./LICENSE).

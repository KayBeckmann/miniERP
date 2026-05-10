<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">PDF-Vorlage &amp; Einstellungen</h1>
      <v-btn color="primary" :loading="saving" @click="save">Speichern</v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4">{{ error }}</v-alert>
    <v-alert v-if="saved" type="success" variant="tonal" density="compact" class="mb-4">Einstellungen gespeichert.</v-alert>

    <v-row>
      <!-- Settings form -->
      <v-col cols="12" md="5">
        <v-card class="pa-4 mb-4">
          <div class="text-subtitle-1 mb-3">Unternehmensangaben</div>
          <v-text-field v-model="form.name" label="Unternehmensname" variant="outlined" density="compact" class="mb-3" />
          <v-textarea v-model="form.address" label="Adresse" rows="3" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="form.iban" label="IBAN" variant="outlined" density="compact" class="mb-0" />
        </v-card>

        <v-card class="pa-4 mb-4">
          <div class="text-subtitle-1 mb-3">Farben</div>
          <div class="d-flex align-center gap-3 mb-4">
            <div>
              <div class="text-caption text-medium-emphasis mb-1">Primärfarbe (Überschriften, Tabellenkopf)</div>
              <div class="d-flex align-center gap-2">
                <input type="color" v-model="form.pdf_color" style="width:48px;height:36px;border:none;border-radius:4px;cursor:pointer;padding:2px" />
                <v-text-field v-model="form.pdf_color" variant="outlined" density="compact" style="max-width:120px" hide-details />
              </div>
            </div>
          </div>
          <div class="d-flex align-center gap-3">
            <div>
              <div class="text-caption text-medium-emphasis mb-1">Akzentfarbe (Gruppenköpfe, Hintergründe)</div>
              <div class="d-flex align-center gap-2">
                <input type="color" v-model="form.pdf_accent_secondary" style="width:48px;height:36px;border:none;border-radius:4px;cursor:pointer;padding:2px" />
                <v-text-field v-model="form.pdf_accent_secondary" variant="outlined" density="compact" style="max-width:120px" hide-details />
              </div>
            </div>
          </div>
        </v-card>

        <v-card class="pa-4 mb-4">
          <div class="text-subtitle-1 mb-3">Footer &amp; Bankverbindung</div>
          <v-textarea v-model="form.pdf_footer_text" label="Footer-Text (optional)" rows="3" variant="outlined" density="compact" class="mb-3"
            hint="Wird am Ende jeder PDF-Seite angezeigt" />
          <v-checkbox v-model="form.pdf_show_bank_details" label="Bankverbindung (IBAN) in PDFs anzeigen" density="compact" hide-details />
        </v-card>
      </v-col>

      <!-- Live preview -->
      <v-col cols="12" md="7">
        <v-card class="pa-4">
          <div class="text-subtitle-1 mb-3 d-flex align-center gap-2">
            <v-icon color="primary">mdi-eye-outline</v-icon>
            Live-Vorschau
          </div>
          <div style="border:1px solid #e0e0e0; border-radius:4px; overflow:hidden; background:#fff;">
            <div v-html="previewHtml" style="transform-origin:top left; font-size:0.7em; padding:12mm 16mm; font-family:Arial,sans-serif;" />
          </div>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { settingsApi, type TenantSettings } from '@/api/settings'

const saving = ref(false)
const saved = ref(false)
const error = ref('')

const form = ref<TenantSettings>({
  id: 0,
  code: '',
  name: '',
  address: null,
  iban: null,
  pdf_color: '#1976D2',
  pdf_footer_text: null,
  pdf_show_bank_details: true,
  pdf_accent_secondary: '#E3F2FD',
})

onMounted(async () => {
  try {
    const data = await settingsApi.getTenant()
    form.value = { ...data }
  } catch (e) {
    error.value = 'Einstellungen konnten nicht geladen werden.'
  }
})

async function save() {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    const updated = await settingsApi.updateTenant({
      name: form.value.name || undefined,
      address: form.value.address,
      iban: form.value.iban,
      pdf_color: form.value.pdf_color,
      pdf_footer_text: form.value.pdf_footer_text,
      pdf_show_bank_details: form.value.pdf_show_bank_details,
      pdf_accent_secondary: form.value.pdf_accent_secondary,
    })
    form.value = { ...updated }
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch (e) {
    error.value = 'Speichern fehlgeschlagen.'
  } finally {
    saving.value = false
  }
}

const previewHtml = computed(() => {
  const color = escapeHtml(form.value.pdf_color || '#1976D2')
  const secondary = escapeHtml(form.value.pdf_accent_secondary || '#E3F2FD')
  const name = escapeHtml(form.value.name || 'Meine Firma GmbH')
  const address = escapeHtml(form.value.address || 'Musterstraße 1\n12345 Musterstadt').replace(/\n/g, '<br>')
  const iban = form.value.iban ? escapeHtml(form.value.iban) : null
  const footerText = form.value.pdf_footer_text ? escapeHtml(form.value.pdf_footer_text).replace(/\n/g, '<br>') : ''
  const showBank = form.value.pdf_show_bank_details

  return `
    <div style="color:#222;font-size:11pt;">
      <div style="display:flex;justify-content:space-between;margin-bottom:6mm;">
        <div>
          <div style="font-size:18pt;font-weight:bold;color:${color};">${name}</div>
          <div style="font-size:9pt;color:#555;margin-top:2mm;line-height:1.5;">${address}</div>
        </div>
        <div style="text-align:right;font-size:9pt;color:#555;">
          <div><strong>Angebotsnr.:</strong> A-2026-001</div>
          <div><strong>Datum:</strong> 10.05.2026</div>
          <div><strong>Gültig bis:</strong> 10.06.2026</div>
          <div style="display:inline-block;padding:1mm 3mm;border-radius:3px;font-size:9pt;background:${secondary};color:#1565c0;margin-top:2mm;">ENTWURF</div>
        </div>
      </div>

      <div style="font-size:16pt;font-weight:bold;margin:4mm 0 2mm;">Angebot A-2026-001</div>

      <div style="border-left:3px solid ${color};padding-left:4mm;margin-bottom:6mm;font-size:10pt;line-height:1.6;">
        <strong>Max Mustermann</strong><br>
        <span style="color:#555;">Geschäftsführer</span><br>
        Beispielweg 42, 10115 Berlin<br>
        max@beispiel.de
      </div>

      <table style="width:100%;border-collapse:collapse;margin-bottom:4mm;font-size:10pt;">
        <thead>
          <tr>
            <th style="background:${color};color:white;padding:2mm 3mm;text-align:left;font-size:9pt;width:5%">Pos.</th>
            <th style="background:${color};color:white;padding:2mm 3mm;text-align:left;font-size:9pt;width:40%">Beschreibung</th>
            <th style="background:${color};color:white;padding:2mm 3mm;text-align:right;font-size:9pt;width:8%">Menge</th>
            <th style="background:${color};color:white;padding:2mm 3mm;text-align:left;font-size:9pt;width:8%">Einh.</th>
            <th style="background:${color};color:white;padding:2mm 3mm;text-align:right;font-size:9pt;width:10%">EP (€)</th>
            <th style="background:${color};color:white;padding:2mm 3mm;text-align:right;font-size:9pt;width:13%">Gesamt (€)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;">1</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;">Fliesenarbeiten Bad</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;text-align:right;">12,000</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;">m²</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;text-align:right;">45,00</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;text-align:right;"><strong>540,00</strong></td>
          </tr>
          <tr style="background:#f9f9f9;">
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;">2</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;">Materialkosten Fliesen</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;text-align:right;">1,000</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;">Pauschal</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;text-align:right;">320,00</td>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;text-align:right;"><strong>320,00</strong></td>
          </tr>
          <tr>
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;" colspan="4" />
            <td style="padding:1.5mm 3mm;border-bottom:1px solid #e0e0e0;background:${secondary};font-size:9pt;font-style:italic;" colspan="2">
              Gruppe „Bad" — Netto: 860,00 € · <strong>Gesamt: 1.023,40 €</strong>
            </td>
          </tr>
        </tbody>
      </table>

      <table style="margin-left:auto;width:80mm;border-top:2px solid ${color};font-size:10pt;">
        <tr><td style="padding:1mm 3mm;">Nettobetrag</td><td style="padding:1mm 3mm;text-align:right;">860,00 €</td></tr>
        <tr><td style="padding:1mm 3mm;">Mehrwertsteuer</td><td style="padding:1mm 3mm;text-align:right;">163,40 €</td></tr>
        <tr style="font-weight:bold;font-size:12pt;border-top:1px solid #ccc;">
          <td style="padding:1mm 3mm;"><strong>Gesamtbetrag</strong></td>
          <td style="padding:1mm 3mm;text-align:right;"><strong>1.023,40 €</strong></td>
        </tr>
      </table>

      ${showBank && iban ? `
      <div style="background:${secondary};padding:3mm;border-radius:3px;margin-top:6mm;font-size:10pt;">
        <strong>Bitte überweisen Sie den Betrag auf:</strong><br>
        IBAN: ${iban} · Empfänger: ${name} · Verwendungszweck: A-2026-001
      </div>` : ''}

      <div style="margin-top:8mm;font-size:8pt;color:#888;border-top:1px solid #eee;padding-top:3mm;">
        ${name}${showBank && iban ? ` · IBAN: ${iban}` : ''} · Angebotsnr.: A-2026-001 · Version 1
        ${footerText ? `<br>${footerText}` : ''}
      </div>
    </div>
  `
})

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
</script>

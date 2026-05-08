<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Kunden</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">Neuer Kunde</v-btn>
    </div>

    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      label="Suchen (Name, Kundennr., E-Mail, Telefon)"
      clearable
      variant="outlined"
      density="compact"
      class="mb-4"
      @update:model-value="onSearch"
    />

    <v-card>
      <v-table>
        <thead>
          <tr>
            <th>Kundennr.</th>
            <th>Name</th>
            <th>Art</th>
            <th>E-Mail</th>
            <th>Telefon</th>
            <th>E-Rechnung</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="text-center pa-4">
              <v-progress-circular indeterminate size="24" />
            </td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="7" class="text-center pa-4 text-medium-emphasis">
              Keine Kunden gefunden
            </td>
          </tr>
          <tr v-for="c in items" :key="c.id">
            <td>{{ c.customer_no }}</td>
            <td>{{ c.name }}<span v-if="c.contact" class="text-medium-emphasis text-caption ml-1">({{ c.contact }})</span></td>
            <td><v-chip :color="c.is_business ? 'primary' : 'default'" size="small" label>{{ c.is_business ? 'Geschäft' : 'Privat' }}</v-chip></td>
            <td>{{ c.email ?? '—' }}</td>
            <td>{{ c.phone ?? '—' }}</td>
            <td><v-chip v-if="c.e_invoice_format !== 'none'" color="info" size="small" label>{{ c.e_invoice_format }}</v-chip><span v-else class="text-medium-emphasis">—</span></td>
            <td class="text-right">
              <v-btn icon size="small" variant="text" @click="openEdit(c)"><v-icon>mdi-pencil</v-icon></v-btn>
              <v-btn icon size="small" variant="text" color="error" @click="askDelete(c)"><v-icon>mdi-delete</v-icon></v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>

      <div class="d-flex align-center justify-space-between pa-3">
        <span class="text-caption text-medium-emphasis">{{ total }} Einträge</span>
        <div class="d-flex align-center gap-2">
          <v-btn size="small" variant="text" :disabled="page === 1" @click="page--">
            <v-icon>mdi-chevron-left</v-icon>
          </v-btn>
          <span class="text-caption">Seite {{ page }} / {{ totalPages }}</span>
          <v-btn size="small" variant="text" :disabled="page >= totalPages" @click="page++">
            <v-icon>mdi-chevron-right</v-icon>
          </v-btn>
        </div>
      </div>
    </v-card>

    <!-- Create / Edit Dialog -->
    <v-dialog v-model="dialog" max-width="640" persistent>
      <v-card>
        <v-card-title>{{ editItem ? 'Kunde bearbeiten' : 'Neuer Kunde' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-row dense>
              <v-col cols="12" sm="8">
                <v-text-field v-model="form.name" label="Name *" :rules="[required]" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-select v-model="form.kind" :items="kindOptions" label="Typ" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.contact" label="Ansprechpartner" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.phone" label="Telefon" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.email" label="E-Mail" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.tax_id" label="Steuernummer / USt-ID" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12">
                <v-textarea v-model="form.address" label="Adresse" rows="2" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-checkbox v-model="form.is_business" label="Geschäftskunde (B2B)" density="compact" hide-details />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="form.e_invoice_format" :items="eInvoiceOptions" label="E-Rechnung" variant="outlined" density="compact" />
              </v-col>
              <v-col v-if="form.e_invoice_format !== 'none'" cols="12" sm="6">
                <v-text-field v-model="form.leitweg_id" label="Leitweg-ID (öff. Auftraggeber)" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12">
                <v-textarea v-model="form.notes" label="Notizen" rows="2" variant="outlined" density="compact" />
              </v-col>
            </v-row>
          </v-form>
          <v-alert v-if="formError" type="error" variant="tonal" density="compact" class="mt-2">{{ formError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="save">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog
      ref="confirmRef"
      title="Kunde löschen?"
      :message="`${deleteTarget?.name} (${deleteTarget?.customer_no}) wirklich löschen?`"
      @confirm="doDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { customersApi, type Customer, type CustomerCreate } from '@/api/stammdaten'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const LIMIT = 25
const items = ref<Customer[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))

const dialog = ref(false)
const saving = ref(false)
const formError = ref('')
const formRef = ref()
const editItem = ref<Customer | null>(null)

const deleteTarget = ref<Customer | null>(null)
const confirmRef = ref()

const emptyForm = (): CustomerCreate => ({
  kind: 'privat', name: '', contact: null, address: null, email: null,
  phone: null, tax_id: null, notes: null, is_business: false,
  e_invoice_format: 'none', leitweg_id: null, active: true,
})
const form = ref<CustomerCreate>(emptyForm())

const required = (v: string) => !!v?.trim() || 'Pflichtfeld'
const kindOptions = [{ title: 'Privat', value: 'privat' }, { title: 'Geschäft', value: 'geschaeft' }]
const eInvoiceOptions = [
  { title: 'Keine', value: 'none' },
  { title: 'XRechnung', value: 'xrechnung' },
  { title: 'ZUGFeRD', value: 'zugferd' },
]

async function load() {
  loading.value = true
  try {
    const res = await customersApi.list({ skip: (page.value - 1) * LIMIT, limit: LIMIT, search: search.value || undefined })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 300)
}

watch(page, load)
onMounted(load)

function openCreate() {
  editItem.value = null
  form.value = emptyForm()
  formError.value = ''
  dialog.value = true
}
function openEdit(c: Customer) {
  editItem.value = c
  form.value = { kind: c.kind, name: c.name, contact: c.contact, address: c.address,
    email: c.email, phone: c.phone, tax_id: c.tax_id, notes: c.notes,
    is_business: c.is_business, e_invoice_format: c.e_invoice_format,
    leitweg_id: c.leitweg_id, active: c.active }
  formError.value = ''
  dialog.value = true
}

async function save() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  formError.value = ''
  try {
    if (editItem.value) {
      await customersApi.update(editItem.value.id, form.value)
    } else {
      await customersApi.create(form.value)
    }
    dialog.value = false
    load()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

function askDelete(c: Customer) {
  deleteTarget.value = c
  confirmRef.value.open()
}
async function doDelete() {
  if (!deleteTarget.value) return
  confirmRef.value.loading.value = true
  try {
    await customersApi.delete(deleteTarget.value.id)
    confirmRef.value.close()
    load()
  } catch (e) {
    confirmRef.value.close()
  }
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Lieferanten</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">Neuer Lieferant</v-btn>
    </div>

    <v-text-field
      v-model="search"
      prepend-inner-icon="mdi-magnify"
      label="Suchen (Name, E-Mail)"
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
            <th>Name</th>
            <th>E-Mail</th>
            <th>Telefon</th>
            <th>IBAN</th>
            <th>Zahlungsziel</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="6" class="text-center pa-4 text-medium-emphasis">Keine Lieferanten gefunden</td>
          </tr>
          <tr v-for="s in items" :key="s.id">
            <td>{{ s.name }}</td>
            <td>{{ s.email ?? '—' }}</td>
            <td>{{ s.phone ?? '—' }}</td>
            <td><code v-if="s.iban" class="text-caption">{{ s.iban }}</code><span v-else class="text-medium-emphasis">—</span></td>
            <td>{{ s.default_payment_terms ?? '—' }}</td>
            <td class="text-right">
              <v-btn icon size="small" variant="text" @click="openEdit(s)"><v-icon>mdi-pencil</v-icon></v-btn>
              <v-btn icon size="small" variant="text" color="error" @click="askDelete(s)"><v-icon>mdi-delete</v-icon></v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <div class="d-flex align-center justify-space-between pa-3">
        <span class="text-caption text-medium-emphasis">{{ total }} Einträge</span>
        <div class="d-flex align-center">
          <v-btn size="small" variant="text" :disabled="page === 1" @click="page--"><v-icon>mdi-chevron-left</v-icon></v-btn>
          <span class="text-caption">Seite {{ page }} / {{ totalPages }}</span>
          <v-btn size="small" variant="text" :disabled="page >= totalPages" @click="page++"><v-icon>mdi-chevron-right</v-icon></v-btn>
        </div>
      </div>
    </v-card>

    <v-dialog v-model="dialog" max-width="560" persistent>
      <v-card>
        <v-card-title>{{ editItem ? 'Lieferant bearbeiten' : 'Neuer Lieferant' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-row dense>
              <v-col cols="12">
                <v-text-field v-model="form.name" label="Name *" :rules="[required]" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.email" label="E-Mail" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.phone" label="Telefon" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12">
                <v-textarea v-model="form.address" label="Adresse" rows="2" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.iban" label="IBAN" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.default_payment_terms" label="Zahlungsziel" variant="outlined" density="compact" placeholder="z. B. 14 Tage netto" />
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

    <ConfirmDialog ref="confirmRef" title="Lieferant löschen?"
      :message="`${deleteTarget?.name} wirklich löschen?`" @confirm="doDelete" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { suppliersApi, type Supplier, type SupplierCreate } from '@/api/stammdaten'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const LIMIT = 25
const items = ref<Supplier[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))
const dialog = ref(false)
const saving = ref(false)
const formError = ref('')
const formRef = ref()
const editItem = ref<Supplier | null>(null)
const deleteTarget = ref<Supplier | null>(null)
const confirmRef = ref()

const emptyForm = (): SupplierCreate => ({
  name: '', address: null, email: null, phone: null,
  iban: null, default_payment_terms: null, notes: null,
})
const form = ref<SupplierCreate>(emptyForm())
const required = (v: string) => !!v?.trim() || 'Pflichtfeld'

async function load() {
  loading.value = true
  try {
    const res = await suppliersApi.list({ skip: (page.value - 1) * LIMIT, limit: LIMIT, search: search.value || undefined })
    items.value = res.items
    total.value = res.total
  } finally { loading.value = false }
}

let t: ReturnType<typeof setTimeout>
function onSearch() { clearTimeout(t); t = setTimeout(() => { page.value = 1; load() }, 300) }
watch(page, load)
onMounted(load)

function openCreate() { editItem.value = null; form.value = emptyForm(); formError.value = ''; dialog.value = true }
function openEdit(s: Supplier) {
  editItem.value = s
  form.value = { name: s.name, address: s.address, email: s.email, phone: s.phone,
    iban: s.iban, default_payment_terms: s.default_payment_terms, notes: s.notes }
  formError.value = ''; dialog.value = true
}
async function save() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true; formError.value = ''
  try {
    editItem.value ? await suppliersApi.update(editItem.value.id, form.value) : await suppliersApi.create(form.value)
    dialog.value = false; load()
  } catch (e) { formError.value = e instanceof Error ? e.message : 'Fehler' }
  finally { saving.value = false }
}
function askDelete(s: Supplier) { deleteTarget.value = s; confirmRef.value.open() }
async function doDelete() {
  if (!deleteTarget.value) return
  try { await suppliersApi.delete(deleteTarget.value.id); confirmRef.value.close(); load() }
  catch { confirmRef.value.close() }
}
</script>

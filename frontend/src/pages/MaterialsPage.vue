<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Materialstamm</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">Neuer Artikel</v-btn>
    </div>

    <div class="d-flex gap-2 mb-4">
      <v-text-field
        v-model="search" prepend-inner-icon="mdi-magnify"
        label="Suchen (Name, SKU, Kategorie)" clearable variant="outlined"
        density="compact" style="max-width:400px" @update:model-value="onSearch"
      />
      <v-checkbox v-model="activeOnly" label="Nur aktive" density="compact" hide-details class="mt-1" @update:model-value="() => { page = 1; load() }" />
    </div>

    <v-card>
      <v-table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>Bezeichnung</th>
            <th>Kategorie</th>
            <th>Einheit</th>
            <th class="text-right">VK-Preis</th>
            <th class="text-right">MwSt.</th>
            <th>Status</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="8" class="text-center pa-4 text-medium-emphasis">Keine Artikel gefunden</td>
          </tr>
          <tr v-for="m in items" :key="m.id">
            <td><code class="text-caption">{{ m.sku ?? '—' }}</code></td>
            <td>{{ m.name }}<div v-if="m.description" class="text-caption text-medium-emphasis">{{ m.description }}</div></td>
            <td>{{ m.category ?? '—' }}</td>
            <td>{{ m.unit }}</td>
            <td class="text-right">{{ m.sale_price ? `${Number(m.sale_price).toFixed(2)} €` : '—' }}</td>
            <td class="text-right">{{ m.vat_rate }} %</td>
            <td><v-chip :color="m.active ? 'success' : 'default'" size="small" label>{{ m.active ? 'Aktiv' : 'Inaktiv' }}</v-chip></td>
            <td class="text-right">
              <v-btn icon size="small" variant="text" @click="openEdit(m)"><v-icon>mdi-pencil</v-icon></v-btn>
              <v-btn icon size="small" variant="text" color="error" @click="askDelete(m)"><v-icon>mdi-delete</v-icon></v-btn>
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

    <v-dialog v-model="dialog" max-width="600" persistent>
      <v-card>
        <v-card-title>{{ editItem ? 'Artikel bearbeiten' : 'Neuer Artikel' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-row dense>
              <v-col cols="12" sm="8">
                <v-text-field v-model="form.name" label="Bezeichnung *" :rules="[required]" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-text-field v-model="form.sku" label="SKU / Artikelnr." variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12">
                <v-textarea v-model="form.description" label="Beschreibung" rows="2" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-text-field v-model="form.unit" label="Einheit" variant="outlined" density="compact" placeholder="Stk, m², h, …" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-text-field v-model="form.sale_price" label="VK-Preis (€)" type="number" step="0.01" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-text-field v-model="form.purchase_price" label="EK-Preis (€)" type="number" step="0.01" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-select v-model="form.vat_rate" :items="vatOptions" label="MwSt." variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-text-field v-model="form.category" label="Kategorie" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="4">
                <v-checkbox v-model="form.active" label="Aktiv" density="compact" hide-details />
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

    <ConfirmDialog ref="confirmRef" title="Artikel löschen?"
      :message="`${deleteTarget?.name} wirklich löschen?`" @confirm="doDelete" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { materialsApi, type Material, type MaterialCreate } from '@/api/stammdaten'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const LIMIT = 25
const items = ref<Material[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const activeOnly = ref(false)
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))
const dialog = ref(false)
const saving = ref(false)
const formError = ref('')
const formRef = ref()
const editItem = ref<Material | null>(null)
const deleteTarget = ref<Material | null>(null)
const confirmRef = ref()

const vatOptions = ['0.00', '7.00', '19.00']
const required = (v: string) => !!v?.trim() || 'Pflichtfeld'

const emptyForm = (): MaterialCreate => ({
  sku: null, name: '', description: null, unit: 'Stk',
  purchase_price: null, sale_price: null, vat_rate: '19.00',
  category: null, default_supplier_id: null, active: true,
})
const form = ref<MaterialCreate>(emptyForm())

async function load() {
  loading.value = true
  try {
    const res = await materialsApi.list({ skip: (page.value - 1) * LIMIT, limit: LIMIT, search: search.value || undefined, active_only: activeOnly.value })
    items.value = res.items
    total.value = res.total
  } finally { loading.value = false }
}

let t: ReturnType<typeof setTimeout>
function onSearch() { clearTimeout(t); t = setTimeout(() => { page.value = 1; load() }, 300) }
watch(page, load)
onMounted(load)

function openCreate() { editItem.value = null; form.value = emptyForm(); formError.value = ''; dialog.value = true }
function openEdit(m: Material) {
  editItem.value = m
  form.value = { sku: m.sku, name: m.name, description: m.description, unit: m.unit,
    purchase_price: m.purchase_price, sale_price: m.sale_price, vat_rate: m.vat_rate,
    category: m.category, default_supplier_id: m.default_supplier_id, active: m.active }
  formError.value = ''; dialog.value = true
}
async function save() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true; formError.value = ''
  try {
    editItem.value ? await materialsApi.update(editItem.value.id, form.value) : await materialsApi.create(form.value)
    dialog.value = false; load()
  } catch (e) { formError.value = e instanceof Error ? e.message : 'Fehler' }
  finally { saving.value = false }
}
function askDelete(m: Material) { deleteTarget.value = m; confirmRef.value.open() }
async function doDelete() {
  if (!deleteTarget.value) return
  try { await materialsApi.delete(deleteTarget.value.id); confirmRef.value.close(); load() }
  catch { confirmRef.value.close() }
}
</script>

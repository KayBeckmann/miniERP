<template>
  <v-dialog v-model="visible" max-width="420" persistent>
    <v-card>
      <v-card-title class="text-h6">{{ title }}</v-card-title>
      <v-card-text>{{ message }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="cancel">Abbrechen</v-btn>
        <v-btn color="error" variant="flat" :loading="loading" @click="confirm">Löschen</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  title?: string
  message?: string
}>()

const emit = defineEmits<{ confirm: []; cancel: [] }>()

const visible = ref(false)
const loading = ref(false)

function open() {
  visible.value = true
}
function cancel() {
  visible.value = false
  emit('cancel')
}
function confirm() {
  emit('confirm')
}
function close() {
  visible.value = false
  loading.value = false
}

defineExpose({ open, close, loading })
</script>

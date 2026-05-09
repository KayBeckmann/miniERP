import { defineStore } from 'pinia'
import { ref } from 'vue'

type SnackbarType = 'success' | 'error' | 'info' | 'warning'

export const useSnackbarStore = defineStore('snackbar', () => {
  const show = ref(false)
  const message = ref('')
  const type = ref<SnackbarType>('success')
  const timeout = ref(3000)

  function notify(msg: string, t: SnackbarType = 'success', ms = 3000) {
    message.value = msg
    type.value = t
    timeout.value = ms
    show.value = true
  }

  return { show, message, type, timeout, notify }
})

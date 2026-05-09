export function useAppSettings() {
  // Paperless-URL wird zur Laufzeit aus dem nginx-Proxy abgeleitet
  // (kein Vite-Build-time env nötig, da wir im gleichen Netzwerk sind)
  const paperlessUrl = import.meta.env.VITE_PAPERLESS_URL ?? 'http://10.10.0.26:8000'

  return { paperlessUrl }
}

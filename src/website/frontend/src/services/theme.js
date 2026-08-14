import { computed, ref } from 'vue'

export const LIGHT_THEME = 'light'
export const DARK_THEME = 'dark'

const THEME_COLOURS = {
  [LIGHT_THEME]: '#faf8f3',
  [DARK_THEME]: '#0e1116',
}

export const currentTheme = ref(LIGHT_THEME)
export const isDarkTheme = computed(() => currentTheme.value === DARK_THEME)

export function preferredTheme(savedTheme, prefersDark) {
  if (savedTheme === LIGHT_THEME || savedTheme === DARK_THEME) return savedTheme
  return prefersDark ? DARK_THEME : LIGHT_THEME
}

function updateDocument(theme) {
  document.documentElement.dataset.theme = theme
  const themeColour = document.querySelector('meta[name="theme-color"]')
  themeColour?.setAttribute('content', THEME_COLOURS[theme])
}

function storageKey() {
  return document.documentElement.dataset.themeStorage
}

function savedTheme() {
  try {
    return window.localStorage.getItem(storageKey())
  } catch {
    return null
  }
}

export function setTheme(theme, { persist = true } = {}) {
  const normalized = theme === DARK_THEME ? DARK_THEME : LIGHT_THEME
  currentTheme.value = normalized
  updateDocument(normalized)
  if (persist) {
    try {
      window.localStorage.setItem(storageKey(), normalized)
    } catch {
      // The active theme still works when storage is unavailable.
    }
  }
}

export function initializeTheme() {
  // index.html resolves this before CSS paints; retain a fallback for tests or
  // alternate entry points that do not run the pre-paint bootstrap.
  const bootTheme = document.documentElement.dataset.theme
  const theme = bootTheme === LIGHT_THEME || bootTheme === DARK_THEME
    ? bootTheme
    : preferredTheme(savedTheme(), window.matchMedia('(prefers-color-scheme: dark)').matches)
  setTheme(theme, { persist: false })
}

export function toggleTheme() {
  setTheme(isDarkTheme.value ? LIGHT_THEME : DARK_THEME)
}

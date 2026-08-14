import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-600.css'
import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initializeTheme } from './services/theme'

const app = createApp(App)

initializeTheme()
app.use(router)
app.mount('#app')

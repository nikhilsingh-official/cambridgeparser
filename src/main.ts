import { createApp } from "vue";
import App from "@/App.vue";
import router from '@/router/router';
import { createPinia } from "pinia";
import { useAuthStore } from "@/stores/useAuth";
// the theme layer. themes.scss is imported here rather than forwarded
// through main.scss because vite injects main.scss into every component's
// <style> block - see the header comment in themes.scss.
import "@/styles/themes.scss";
import "@/styles/public-seo.scss";
// the Cambridge IDE's component styles and the mono face it ships. Both
// came from that app's own entrypoint when it was a separate site; themes.scss
// stays first so its tokens are defined before ide.css reads them.
import "@fontsource/ibm-plex-mono/latin-400.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import "@/styles/ide.css";
// @vueform/multiselect's stylesheet was imported inside Header.vue - a
// component on a LAZY route. So the stats page's filters were styled only if
// you happened to visit the Paper Browser first, and rendered as bare bulleted
// lists otherwise. Third-party CSS that several routes depend on has to load
// with the app, not with whichever chunk happens to arrive first.
import "@vueform/multiselect/themes/default.css";
import { initializeTheme } from "@/lib/theme";

// before createApp so the first painted frame is already themed.
initializeTheme();

const app = createApp(App);

// pinia is installed BEFORE the router, because the auth store is read
// below and the router's install() kicks off the initial navigation - and that
// navigation hits the beforeEach guard.
const pinia = createPinia();
app.use(pinia);

// auth initialisation moved here from App.vue's setup.
//
// The guard awaits `authReady`, which only resolves inside init(). When init()
// lived in App.vue it ran during mount() - i.e. AFTER app.use(router) had
// already started the initial navigation and parked the guard on that promise.
// It happened to work, but only because mount() does not block on a pending
// navigation. That is far too subtle a thing to leave load-bearing: starting it
// here means the promise is always in flight before anything can await it.
//
// Deliberately not awaited - the app shell mounts immediately and the guard
// handles the wait, so there is no blank frame while the session is restored.
useAuthStore().init();

app.use(router);

app.mount("#app");

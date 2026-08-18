import { createApp } from "vue";
import App from "@/App.vue";
import router from '@/router/router';
import { createPinia } from "pinia";
import { useAuthStore } from "@/stores/useAuth";

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

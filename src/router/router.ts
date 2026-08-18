import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import DashboardPage from '@/components_dashboard/DashboardPage.vue'
import BrowserPage from '@/components_browser/BrowserPage.vue'
import StatsPage from '@/components_stats/StatsPage.vue'
import MCQNav from '@/components_navigator/MCQNav.vue'
import Login from '@/components_auth/Login.vue'
import { authReady, supabase } from '@/stores/useAuth'

// route meta is now typed, so `requiresAuth` cannot be misspelled into
// silence - a typo'd meta key on a protected route would otherwise leave that
// route publicly reachable with no error anywhere.
declare module 'vue-router' {
  interface RouteMeta {
    /** Signed-in users only. Anonymous visitors are sent to /login. */
    requiresAuth?: boolean
    /** Signed-OUT users only. Signed-in visitors are sent to the dashboard. */
    guestOnly?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  // every application route is now explicitly protected. Previously all of
  // them were open - the dashboard, browser and stats pages rendered fine with
  // no session, and only MCQNav had an ad-hoc onMounted redirect.
  { path: '/', name: 'Dashboard', component: DashboardPage, meta: { requiresAuth: true } },
  { path: '/browser', name: 'Browser', component: BrowserPage, meta: { requiresAuth: true } },
  { path: '/stats', name: 'Stats', component: StatsPage, meta: { requiresAuth: true } },
  {
    path: '/solver/:schema',
    name: 'Solver',
    component: MCQNav,
    props: true,
    meta: { requiresAuth: true },
  },
  { path: '/login', name: 'Login', component: Login, meta: { guestOnly: true } },

  // there was no catch-all, so an unmatched URL rendered a blank page with
  // no error. This is also what made the broken OAuth redirect to /dashboard
  // fail silently instead of visibly.
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  // wait for the initial session restore before deciding anything. Without
  // this the guard reads a null session on every hard refresh and bounces a
  // signed-in user to /login. See the authReady comment in useAuth.ts.
  await authReady

  // read the client directly rather than the Pinia store. The guard can run
  // before any component has mounted, and calling useAuthStore() outside an
  // active pinia instance throws. getSession() is cached in memory after
  // authReady has resolved, so this is not an extra network call.
  const { data } = await supabase.auth.getSession()
  const isAuthed = data.session !== null

  if (to.meta.requiresAuth && !isAuthed) {
    // remember where they were going so login can return them there
    // instead of dumping everyone on the dashboard.
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && isAuthed) {
    return { path: '/' }
  }

  return true
})

export default router

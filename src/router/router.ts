import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
// PERFORMANCE. These were static imports, so every route's code - the
// dashboard, the stats page, the browser, pdfjs-dist, lottie - was bundled into
// one 1.4 MB chunk that had to be downloaded and PARSED before any page could
// render. Opening the Paper Solver paid for the entire application.
//
// Lazy imports give each route its own chunk. The solver pays for pdf.js; the
// dashboard pays for its images; neither pays for the other.
const DashboardPage = () => import('@/components_dashboard/DashboardPage.vue')
const BrowserPage = () => import('@/components_browser/BrowserPage.vue')
const StatsPage = () => import('@/components_stats/StatsPage.vue')
const MCQNav = () => import('@/components_navigator/MCQNav.vue')
// the Cambridge IDE's pages, merged in from what used to be a separate
// application. Same lazy treatment - the IDE pulls CodeMirror and a wasm
// parser, and the solver should not pay for either.
const IdeView = () => import('@/views/IdeView.vue')
const ProblemsView = () => import('@/views/ProblemsView.vue')
const LearnView = () => import('@/views/LearnView.vue')
// the public landing page. Kept eager alongside Login for the same reason -
// it is the first paint for an anonymous visitor.
import LandingView from '@/views/LandingView.vue'
// Login stays EAGER on purpose. It is the first thing an unauthenticated
// visitor sees, and the guard redirects there before anything else has loaded -
// making it a separate round trip would delay the one screen that must be fast.
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
    /** Reachable without a session AND without the app shell (no sidebar). */
    publicChrome?: boolean
    /** Signed-in, but the page owns the whole viewport (the exam runner). */
    fullscreen?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  // the public shopfront. No session, no sidebar - it is the page a visitor
  // lands on before they have an account, and it came from the Cambridge IDE
  // side of the merge.
  { path: '/', name: 'Landing', component: LandingView, meta: { publicChrome: true } },
  { path: '/login', name: 'Login', component: Login, meta: { guestOnly: true, publicChrome: true } },

  // ------------------------------------------------------------ paper solver
  // every application route is explicitly protected. Previously all of
  // them were open - the dashboard, browser and stats pages rendered fine with
  // no session, and only MCQNav had an ad-hoc onMounted redirect.
  { path: '/dashboard', name: 'Dashboard', component: DashboardPage, meta: { requiresAuth: true } },
  { path: '/browser', name: 'Browser', component: BrowserPage, meta: { requiresAuth: true } },
  { path: '/stats', name: 'Stats', component: StatsPage, meta: { requiresAuth: true } },
  {
    path: '/solver/:schema',
    name: 'Solver',
    component: MCQNav,
    props: true,
    // no sidebar during an exam. The runner owns the viewport, and a nav
    // rail is both a distraction and an invitation to leave mid-paper.
    meta: { requiresAuth: true, fullscreen: true },
  },

  // ----------------------------------------------------------- cambridge IDE
  // the second half of the merge. These were their own application with
  // their own router, auth and hash-based URLs; they are now a page group in
  // this one, on the same path routing and the same session.
  { path: '/problems', name: 'Problems', component: ProblemsView, meta: { requiresAuth: true } },
  { path: '/ide', name: 'Ide', component: IdeView, meta: { requiresAuth: true } },
  { path: '/ide/:id', name: 'IdeRecord', component: IdeView, props: true, meta: { requiresAuth: true } },
  { path: '/learn', name: 'Learn', component: LearnView, meta: { requiresAuth: true } },

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
    return { path: '/dashboard' }
  }

  // a signed-in visitor hitting the landing page wants the app, not the
  // shopfront. Anonymous visitors still get the landing page.
  if (to.name === 'Landing' && isAuthed) {
    return { path: '/dashboard' }
  }

  return true
})

export default router

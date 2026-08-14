import { createRouter, createWebHashHistory } from 'vue-router'
import { authReady, currentUser } from '@/services/auth'

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      name: 'landing',
      component: () => import('@/views/LandingView.vue'),
      meta: { public: true, chrome: false },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true, chrome: false },
    },
    {
      path: '/ide',
      name: 'ide',
      component: () => import('@/views/IdeView.vue'),
    },
    {
      path: '/record/:id',
      name: 'record',
      component: () => import('@/views/IdeView.vue'),
      props: true,
    },
    {
      path: '/problems',
      name: 'problems',
      component: () => import('@/views/ProblemsView.vue'),
    },
    {
      path: '/learn',
      name: 'learn',
      component: () => import('@/views/LearnView.vue'),
    },
  ],
})

// Route protection. Every route requires auth except those flagged public.
// Awaiting `authReady` makes a hard reload wait for Firebase's initial auth
// check before deciding, so a signed-in user is never bounced to /login.
router.beforeEach(async (to) => {
  // Public pages do not depend on Firebase and should paint even when auth is
  // slow or unavailable. A signed-in user can still choose to visit Log in;
  // submitting there simply refreshes their session and opens the IDE.
  if (to.meta.public) return true
  await authReady
  if (!currentUser.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router

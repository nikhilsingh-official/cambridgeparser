import { createRouter, createWebHistory } from 'vue-router'
import DashboardPage from '@/components_dashboard/DashboardPage.vue'
import BrowserPage from '@/components_browser/BrowserPage.vue'
import StatsPage from '@/components_stats/StatsPage.vue'
import MCQNav from '@/components_navigator/MCQNav.vue'
import Login from '@/components_auth/Login.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: DashboardPage },
  { path: '/browser', name: 'Browser', component: BrowserPage },
  { path: '/stats', name: 'Stats', component: StatsPage },
  {
    path: '/solver/:schema',
    component: MCQNav,
    props: true
  }, 
  { path: '/login', component: Login }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
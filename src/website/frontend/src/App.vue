<script setup>
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { currentUser, logout } from '@/services/auth'

const router = useRouter()
const route = useRoute()

async function onLogout() {
  await logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <header v-if="route.meta.chrome !== false" class="topbar">
    <RouterLink class="brand" to="/ide">Cambridge IDE</RouterLink>
    <nav v-if="currentUser">
      <RouterLink to="/ide">IDE</RouterLink>
      <RouterLink to="/problems">Problems</RouterLink>
      <RouterLink to="/learn">Learn</RouterLink>
    </nav>

    <div v-if="currentUser" class="account">
      <span class="who">{{ currentUser.email || currentUser.displayName }}</span>
      <button type="button" class="signout" @click="onLogout">Sign out</button>
    </div>
  </header>

  <RouterView />
</template>

<style scoped>
.account {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.who {
  color: var(--muted);
  font-size: 0.85rem;
}

.signout {
  cursor: pointer;
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  padding: 0.3rem 0.6rem;
  background: var(--panel-2);
  color: var(--ink);
  font-size: 0.85rem;
}
</style>

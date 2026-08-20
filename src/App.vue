<script setup lang="ts">
// the application shell.
//
// This used to be a bare <RouterView>, because each page rendered its own
// <Sidebar> - fine when the app was only the solver's four pages, wrong now
// that the Cambridge IDE's pages are part of the same application and would
// each have to remember to do it.
//
// The sidebar is hoisted here and rendered from route meta instead, which also
// makes the two exceptions explicit rather than emergent:
//   - publicChrome: the landing page and login have no navigation, because
//     showing an app's nav to someone with no session advertises what they
//     cannot reach.
//   - fullscreen: the exam runner owns the viewport.
//
// The sidebar is position:fixed at 5vw, so pages offset themselves with
// padding-left rather than being wrapped in a flex row - unchanged from how
// the solver's pages already worked.
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import Sidebar from '@/components/Sidebar.vue';

const route = useRoute();
const showShell = computed(() => !route.meta.publicChrome && !route.meta.fullscreen);
</script>

<template>
  <Sidebar v-if="showShell" />
  <RouterView />
</template>

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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import Sidebar from '@/components/Sidebar.vue';
// unsupported phone layouts are replaced with an explicit non-interactive gate.
import MobileUnsupported from '@/components/MobileUnsupported.vue';
import { shouldBlockMobileLayout } from '@/lib/layout/mobileAccess';

const route = useRoute();
const showShell = computed(() => !route.meta.publicChrome && !route.meta.fullscreen);
// public landing and auth screens remain available so a phone user can
// sign in, recover access, or sign out; only the unsupported app layouts block.
const viewportWidth = ref(window.innerWidth);
const blockMobileLayout = computed(() =>
  shouldBlockMobileLayout(viewportWidth.value, Boolean(route.meta.supportsNarrowViewport)),
);
const updateViewportWidth = () => { viewportWidth.value = window.innerWidth; };
onMounted(() => window.addEventListener('resize', updateViewportWidth));
onBeforeUnmount(() => window.removeEventListener('resize', updateViewportWidth));
</script>

<template>
  <!-- do not mount app pages behind the blocker; this prevents hidden
       keyboard interaction and stops unsupported solver sessions from starting. -->
  <MobileUnsupported v-if="blockMobileLayout" />
  <template v-else>
    <Sidebar v-if="showShell" />
    <RouterView />
  </template>
</template>

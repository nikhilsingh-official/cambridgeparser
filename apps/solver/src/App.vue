<script setup lang="ts">
// `init()` moved to main.ts so the router guard can never await a promise
// whose resolver has not been scheduled yet - see the comment there.
//
// the unused `Sidebar` import was removed. Each page renders its own
// sidebar; this one was dead (docs/future_work.md §5). It also must NOT come back
// at this level - App.vue wraps the login page too, and a sidebar on the login
// screen would advertise the app's navigation to someone not signed in.
</script>
<template>
  <RouterView></RouterView>
</template>

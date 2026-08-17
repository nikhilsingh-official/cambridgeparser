<script setup>
import Sidebar from '@/components/Sidebar.vue';
import { useAuthStore } from '@/stores/useAuth';
const { init } = useAuthStore();
init();
</script>
<template>
  <RouterView></RouterView>
</template>
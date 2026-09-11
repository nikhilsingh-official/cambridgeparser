<script setup lang="ts">
import { computed } from 'vue';
import ThemeSwitcher from '@/components/ThemeSwitcher.vue';
import {
  renderPublicContent,
  type PublicContentPageKey,
} from '@/lib/publicSeoContent';

const props = defineProps<{ page: PublicContentPageKey }>();
const pageHtml = computed(() => renderPublicContent(props.page));
</script>

<template>
  <div class="public-product-page">
    <ThemeSwitcher class="public-theme-switcher" />
    <div v-html="pageHtml"></div>
  </div>
</template>

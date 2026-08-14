<script setup>
import { computed } from 'vue'
import { overlayTokenText } from '@/services/records'

const props = defineProps({
  layout: {
    type: Object,
    required: true,
  },
})

const pages = computed(() => props.layout?.pages || [])

function tokenStyle(token) {
  return {
    left: `${token.x}px`,
    top: `${token.y}px`,
    width: `${token.w}px`,
    height: `${token.h}px`,
    fontSize: `${Math.max(10, token.h * 0.66)}px`,
  }
}

function pageStyle(page) {
  return {
    width: `${page.width}px`,
    height: `${page.height}px`,
  }
}
</script>

<template>
  <div v-if="pages.length" class="selectable-text-overlay text-overlay">
    <div
      v-for="page in pages"
      :key="page.page_index"
      class="text-overlay-page"
      :style="pageStyle(page)"
    >
      <span
        v-for="(token, index) in page.tokens"
        :key="`${page.page_index}:${index}`"
        class="text-overlay-token"
        :class="{ mono: token.mono }"
        :style="tokenStyle(token)"
      >{{ overlayTokenText(page.tokens, index) }}</span>
    </div>
  </div>
</template>

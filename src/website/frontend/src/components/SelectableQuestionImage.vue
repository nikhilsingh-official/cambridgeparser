<script setup>
import { computed } from 'vue'
import SelectableTextOverlay from '@/components/SelectableTextOverlay.vue'

const props = defineProps({
  layout: {
    type: Object,
    required: true,
  },
  image: {
    type: Object,
    required: true,
  },
  alt: {
    type: String,
    default: 'Question',
  },
})

const emit = defineEmits(['error'])
const resourcesBase = `${import.meta.env.BASE_URL}resources/`
const imageUrl = computed(() => `${resourcesBase}${props.image.src}`)
const surfaceStyle = computed(() => ({
  width: `${props.image.width}px`,
  height: `${props.image.height}px`,
}))
</script>

<template>
  <div class="selectable-question-image" :style="surfaceStyle">
    <img
      class="question-image"
      :src="imageUrl"
      :alt="alt"
      draggable="false"
      @error="emit('error')"
    >
    <SelectableTextOverlay
      class="question-text-overlay"
      :layout="layout"
    />
  </div>
</template>

<script setup lang="ts">
// ==========================================================================
//
// The one-line reading of a section, sitting above its charts.
//
// The text comes from lib/stats/recommendations.ts - rules over the same data
// the charts draw, never a language model. See the header there for why.
//
// Tone is carried by an icon and a word as well as a colour, never colour
// alone: "warn" must still read as a warning to someone who cannot distinguish
// it from "good", and beside a chart is exactly where that matters.
// ==========================================================================
import { computed } from 'vue';
import { TrendingUp, AlertTriangle, Info } from 'lucide-vue-next';
import type { Recommendation } from '@/lib/stats/recommendations';

const props = defineProps<{ recommendation: Recommendation }>();

const icon = computed(() => ({
  good: TrendingUp, warn: AlertTriangle, info: Info,
}[props.recommendation.tone]));

const toneLabel = computed(() => ({
  good: 'On track', warn: 'Worth attention', info: 'Note',
}[props.recommendation.tone]));
</script>

<template>
  <div class="rec-banner" :class="`tone-${recommendation.tone}`" role="note">
    <component :is="icon" class="rec-icon" :size="18" aria-hidden="true" />
    <div class="rec-body">
      <p class="rec-finding">
        <span class="rec-tone-label">{{ toneLabel }}</span>
        {{ recommendation.finding }}
      </p>
      <p v-if="recommendation.action" class="rec-action">{{ recommendation.action }}</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.rec-banner {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.7rem 0.9rem;
  border-radius: var(--radius-control);
  background: var(--secondary-background);
  // A left rule rather than a tinted fill: the sections below are already dense
  // with colour, and a full-width wash would compete with the charts it is
  // meant to introduce.
  border-left: 3px solid var(--muted);
  box-sizing: border-box;
}

.rec-icon { flex: 0 0 auto; margin-top: 0.1rem; color: var(--muted); }
.rec-body { min-width: 0; }

.rec-finding {
  margin: 0;
  font-family: var(--font-body);
  font-size: 0.85rem;
  color: var(--text);
  line-height: 1.4;
}

.rec-tone-label {
  // The word carries the tone alongside the colour and the icon.
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  margin-right: 0.45rem;
}

.rec-action {
  margin: 0.2rem 0 0;
  font-family: var(--font-body);
  font-size: 0.78rem;
  color: var(--muted);
  line-height: 1.45;
}

.tone-good  { border-left-color: var(--success); .rec-icon, .rec-tone-label { color: var(--success); } }
.tone-warn  { border-left-color: var(--warning); .rec-icon, .rec-tone-label { color: var(--warning); } }
.tone-info  { border-left-color: var(--accent);  .rec-icon, .rec-tone-label { color: var(--accent); } }
</style>

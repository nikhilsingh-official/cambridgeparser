<script setup lang="ts">
// ==========================================================================
//
// One number in a box. The stats page has fourteen of these and they were all
// the literal word "microstat" before.
//
// A stat tile is a deliberate choice, not a fallback: a single value that has
// no shape over time reads faster as a number than as a one-bar chart. The
// value is the largest thing in the tile; the label sits above it, quiet, and
// the hint below explains what it means so the number is not a riddle.
// ==========================================================================
defineProps<{
  label: string;
  /** Null renders an em dash - "no data" must never look like zero. */
  value: string | null;
  hint?: string;
  /** Optional series colour, for tiles that pair with a chart. */
  accent?: string;
}>();
</script>

<template>
  <div class="micro-stat">
    <span class="micro-label">{{ label }}</span>
    <span class="micro-value" :style="accent ? { color: accent } : undefined">
      {{ value ?? '—' }}
    </span>
    <span v-if="hint" class="micro-hint">{{ hint }}</span>
  </div>
</template>

<style scoped lang="scss">
.micro-stat {
  // Container query units above need a container to measure.
  container-type: inline-size;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.15rem;
  height: 100%;
  padding: 0.75rem 0.9rem;
  box-sizing: border-box;
  overflow: hidden;
}

.micro-label {
  font-family: var(--font-body);
  font-size: 0.7rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.micro-value {
  // Tabular figures so a value that ticks upward does not jitter its own box.
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  // clamped rather than fixed. At 1.5rem "1274/1840" and "Chemistry"
  // overflowed their tiles and rendered as "1274/184" and "Chemistr" - a
  // truncated number is not a smaller number, it is a wrong one.
  font-size: clamp(0.95rem, 2.1cqw + 0.55rem, 1.5rem);
  line-height: 1.15;
  color: var(--text);
  overflow-wrap: anywhere;
}

.micro-hint {
  font-family: var(--font-body);
  font-size: 0.68rem;
  color: var(--muted);
  opacity: 0.8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

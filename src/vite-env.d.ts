/// <reference types="vite/client" />

// added. Without this, TypeScript has no declaration for `*.vue` imports,
// so any component NOT written in <script setup lang="ts"> resolved to an
// implicit `any` (TS7016) - Hero.vue, StatsPrev.vue, ZenMode.vue,
// HighlightModeSlider.vue and App.vue were all untyped at their import sites.
declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>;
  export default component;
}

// `?raw` imports (used by constants/codeMaps.ts for the inline SVG icons)
// are a Vite feature and need declaring too.
declare module '*.svg?raw' {
  const content: string;
  export default content;
}

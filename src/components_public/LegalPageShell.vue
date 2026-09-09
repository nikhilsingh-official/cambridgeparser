<script setup lang="ts">
// ============================================================================
//
// Shared public shell for CambridgeParser's policy and terms pages.
// ============================================================================

import { ArrowLeft, BookOpenCheck } from 'lucide-vue-next';
import { RouterLink } from 'vue-router';
import ThemeSwitcher from '@/components/ThemeSwitcher.vue';

defineProps<{
  eyebrow: string;
  title: string;
  summary: string;
  effectiveDate: string;
}>();
</script>

<template>
  <main class="legal-page">
    <a class="skip-link" href="#legal-content">Skip to policy</a>

    <nav class="legal-nav" aria-label="Policy navigation">
      <RouterLink class="brand" to="/" aria-label="CambridgeParser home">
        <span class="brand-mark" aria-hidden="true"><BookOpenCheck /></span>
        <span>CambridgeParser</span>
      </RouterLink>

      <div class="nav-links">
        <RouterLink to="/privacy">Privacy</RouterLink>
        <RouterLink to="/terms">Terms</RouterLink>
        <RouterLink to="/data-deletion">Data deletion</RouterLink>
        <ThemeSwitcher />
      </div>
    </nav>

    <article id="legal-content" class="legal-content">
      <header class="legal-heading">
        <p class="eyebrow">{{ eyebrow }}</p>
        <h1>{{ title }}</h1>
        <p class="summary">{{ summary }}</p>
        <p class="effective">Effective and last updated: {{ effectiveDate }}</p>
      </header>

      <div class="legal-body">
        <slot />
      </div>
    </article>

    <footer class="legal-footer">
      <RouterLink to="/"><ArrowLeft aria-hidden="true" /> Back to CambridgeParser</RouterLink>
      <nav aria-label="Legal links">
        <RouterLink to="/privacy">Privacy Policy</RouterLink>
        <RouterLink to="/terms">Terms and Conditions</RouterLink>
        <RouterLink to="/data-deletion">Data deletion</RouterLink>
      </nav>
    </footer>
  </main>
</template>

<style scoped>
.legal-page {
  min-height: 100vh;
  box-sizing: border-box;
  background:
    radial-gradient(circle at 82% 0%, color-mix(in srgb, var(--accent) 8%, transparent), transparent 28rem),
    var(--background);
  color: var(--text);
}

.skip-link {
  position: fixed;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 100;
  padding: 0.65rem 0.9rem;
  border-radius: var(--radius-control);
  background: var(--accent);
  color: var(--background);
  font-weight: 700;
  text-decoration: none;
  transform: translateY(-150%);
}

.skip-link:focus { transform: translateY(0); }

.legal-nav,
.legal-content,
.legal-footer {
  width: min(calc(100% - 3rem), 72rem);
  margin-inline: auto;
}

.legal-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 5rem;
  border-bottom: 1px solid var(--border);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  color: var(--text);
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 650;
  letter-spacing: -0.025em;
  text-decoration: none;
}

.brand-mark {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--border));
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--accent) 10%, var(--tertiary-background));
  color: var(--accent);
}

.brand-mark svg { width: 1.05rem; height: 1.05rem; }

.nav-links,
.legal-footer nav {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-links > a,
.legal-footer a {
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-decoration: none;
}

.nav-links > a:hover,
.nav-links > a.router-link-active,
.legal-footer a:hover { color: var(--text); }

.legal-content {
  display: grid;
  grid-template-columns: minmax(15rem, 0.42fr) minmax(0, 1fr);
  gap: clamp(3rem, 8vw, 8rem);
  padding-block: clamp(4rem, 8vw, 7rem);
}

.legal-heading { align-self: start; }

.eyebrow,
.effective {
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow {
  margin: 0 0 1rem;
  color: var(--accent);
  font-size: 0.66rem;
  font-weight: 600;
}

h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 5vw, 4.5rem);
  font-weight: 560;
  letter-spacing: -0.055em;
  line-height: 1;
}

.summary {
  margin: 1.4rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
  line-height: 1.7;
}

.effective {
  margin: 1.5rem 0 0;
  color: var(--muted);
  font-size: 0.58rem;
  line-height: 1.6;
}

.legal-body {
  min-width: 0;
  padding: clamp(1.5rem, 4vw, 3rem);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: color-mix(in srgb, var(--secondary-background) 92%, transparent);
  box-shadow: var(--card-shadow);
}

.legal-body :deep(section + section) {
  margin-top: 2.6rem;
  padding-top: 2.6rem;
  border-top: 1px solid var(--border);
}

.legal-body :deep(h2) {
  margin: 0 0 0.9rem;
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: -0.025em;
}

.legal-body :deep(h3) {
  margin: 1.5rem 0 0.55rem;
  font-family: var(--font-display);
  font-size: 0.92rem;
  font-weight: 600;
}

.legal-body :deep(p),
.legal-body :deep(li) {
  color: var(--muted);
  font-family: var(--font-body);
  font-size: 0.88rem;
  line-height: 1.78;
}

.legal-body :deep(p) { margin: 0.75rem 0 0; }
.legal-body :deep(ul) { margin: 0.8rem 0 0; padding-left: 1.25rem; }
.legal-body :deep(li + li) { margin-top: 0.45rem; }
.legal-body :deep(strong) { color: var(--text); }

.legal-body :deep(a) {
  color: var(--accent);
  text-underline-offset: 0.2em;
}

.legal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  min-height: 7rem;
  border-top: 1px solid var(--border);
}

.legal-footer > a { display: inline-flex; align-items: center; gap: 0.45rem; }
.legal-footer > a svg { width: 0.9rem; height: 0.9rem; }

a:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

@media (max-width: 48rem) {
  .legal-nav,
  .legal-content,
  .legal-footer { width: min(calc(100% - 2rem), 72rem); }

  .legal-content { grid-template-columns: 1fr; gap: 2.5rem; }
  .legal-heading { max-width: 36rem; }
  .legal-footer { align-items: flex-start; flex-direction: column; justify-content: center; }
}

@media (max-width: 34rem) {
  .nav-links > a { display: none; }
  .legal-body { padding: 1.25rem; }
  .legal-footer nav { align-items: flex-start; flex-direction: column; gap: 0.6rem; }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after { transition-duration: 0.01ms !important; }
}
</style>

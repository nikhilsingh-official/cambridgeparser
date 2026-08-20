<script setup>
import { RouterLink } from 'vue-router'
import ThemeToggle from '@/components_ide/ThemeToggle.vue'
</script>

<template>
  <main class="landing-page">
    <section class="hero" aria-labelledby="hero-title">
      <nav class="landing-nav" aria-label="Landing navigation">
        <RouterLink class="landing-brand" to="/" aria-label="Pseudocode home">
          <span class="brand-mark" aria-hidden="true">P/</span>
          <span>Pseudocode</span>
        </RouterLink>
        <div class="landing-actions">
          <ThemeToggle />
          <RouterLink class="landing-login" to="/login">Log in</RouterLink>
        </div>
      </nav>

      <div class="hero-copy">
        <h1 id="hero-title">Make every line<br><em>earn its mark.</em></h1>
        <p class="hero-lede">
          Write, run, and refine exam pseudocode with feedback grounded in the
          real mark scheme.
        </p>
        <RouterLink class="hero-cta" to="/login">
          Start solving
          <span aria-hidden="true">↗</span>
        </RouterLink>
      </div>

      <div class="hero-visual" aria-label="Pseudocode editor preview">
        <div class="code-window">
          <div class="window-bar">
            <span>Q4 · 6 marks</span>
            <span class="window-status">checking</span>
          </div>
          <pre><span class="line-no">01</span> <b>PROCEDURE</b> FindHighest()
<span class="line-no">02</span>   Highest ← Scores[1]
<span class="line-no">03</span>   <b>FOR</b> Index ← 2 <b>TO</b> 30
<span class="line-no">04</span>     <b>IF</b> Scores[Index] &gt; Highest <b>THEN</b>
<span class="line-no">05</span>       Highest ← Scores[Index]
<span class="line-no">06</span>     <b>ENDIF</b>
<span class="line-no">07</span>   <b>NEXT</b> Index
<span class="line-no">08</span> <b>ENDPROCEDURE</b></pre>
          <div class="scan-line" aria-hidden="true"></div>
        </div>
        <div class="mark-card">
          <span class="mark-check">✓</span>
          <div><strong>M3 earned</strong><small>Correct loop bounds</small></div>
          <span class="mark-score">1/1</span>
        </div>
        <span class="syntax-chip chip-one">REPEAT</span>
        <span class="syntax-chip chip-two">ENDIF</span>
      </div>

      <p class="hero-footnote">Built for Paper 2 · No setup, just solve.</p>
    </section>
  </main>
</template>

<style scoped>
.landing-page {
  min-height: 100vh;
  padding: clamp(0.9rem, 2vw, 1.5rem);
  background:
    radial-gradient(circle at 80% 22%, color-mix(in srgb, var(--accent) 11%, transparent), transparent 27rem),
    var(--bg);
  overflow: hidden;
}

.hero {
  position: relative;
  isolation: isolate;
  width: 100%;
  min-height: calc(100vh - clamp(1.8rem, 4vw, 3rem));
  max-width: 96rem;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(27rem, 1.1fr);
  grid-template-rows: auto 1fr auto;
  gap: 2rem 4rem;
  align-items: center;
  padding: clamp(1.25rem, 3vw, 3rem);
  border: 1px solid var(--border);
  border-radius: 1.5rem;
  background:
    linear-gradient(color-mix(in srgb, var(--accent) 5%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--accent) 5%, transparent) 1px, transparent 1px),
    linear-gradient(145deg, var(--panel-2) 0%, var(--panel) 72%);
  background-size: 3rem 3rem, 3rem 3rem, auto;
  box-shadow: 0 2rem 7rem rgba(0, 0, 0, 0.32);
}

.hero::before {
  content: '';
  position: absolute;
  inset: 5.5rem auto auto 47%;
  width: 1px;
  height: calc(100% - 8rem);
  background: linear-gradient(transparent, var(--border), transparent);
  z-index: -1;
}

.landing-nav {
  grid-column: 1 / -1;
  align-self: start;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.landing-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.landing-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  color: var(--ink);
  font-family: var(--font-display);
  font-weight: 600;
  text-decoration: none;
  letter-spacing: -0.02em;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.55rem;
  background: var(--accent);
  color: var(--background);
  font-family: var(--font-display);
  font-size: 0.78rem;
  font-weight: 700;
}

.landing-login,
.hero-cta {
  text-decoration: none;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.landing-login {
  padding: 0.55rem 1rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: 0.88rem;
  font-weight: 600;
}

.landing-login:hover {
  border-color: var(--secondary-color);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
}

.hero-copy {
  max-width: 39rem;
  padding-bottom: 2rem;
}

h1 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-display);
  font-size: clamp(3.25rem, 6.5vw, 7rem);
  font-weight: 600;
  letter-spacing: -0.06em;
  line-height: 0.94;
}

h1 em {
  color: var(--accent);
  font-family: var(--font-display);
  font-weight: 500;
  font-style: normal;
}

.hero-lede {
  max-width: 32rem;
  margin: 1.8rem 0 2rem;
  color: var(--muted);
  font-size: clamp(1rem, 1.3vw, 1.18rem);
  line-height: 1.65;
}

.hero-cta {
  display: inline-flex;
  align-items: center;
  gap: 2rem;
  padding: 0.85rem 1rem 0.85rem 1.2rem;
  border-radius: 0.65rem;
  background: var(--accent);
  color: var(--background);
  font-family: var(--font-display);
  font-weight: 600;
}

.hero-cta span {
  font-size: 1.1rem;
}

.hero-cta:hover {
  transform: translateY(-2px);
  background: var(--secondary-color-lightened);
}

.hero-visual {
  position: relative;
  width: min(100%, 42rem);
  justify-self: center;
  padding: 2.8rem 1.5rem 3.5rem;
  transform: rotate(1.3deg);
}

.code-window {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 1rem;
  background: var(--term);
  box-shadow: 0 2.3rem 5rem rgba(0, 0, 0, 0.32);
}

.window-bar {
  display: flex;
  justify-content: space-between;
  padding: 0.78rem 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.72rem;
}

.window-status {
  color: var(--accent);
}

.window-status::before {
  content: '';
  display: inline-block;
  width: 0.4rem;
  height: 0.4rem;
  margin-right: 0.45rem;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0.8rem currentColor;
}

pre {
  margin: 0;
  padding: clamp(1.2rem, 3vw, 2.1rem);
  color: var(--term-ink);
  font-family: var(--font-mono);
  font-size: clamp(0.7rem, 1.15vw, 0.9rem);
  line-height: 2;
  white-space: pre;
}

pre b {
  color: var(--accent);
  font-weight: 600;
}

.line-no {
  display: inline-block;
  width: 1.8rem;
  color: color-mix(in srgb, var(--muted) 55%, var(--term));
  user-select: none;
}

.scan-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 42%;
  height: 2.15rem;
  border-top: 1px solid color-mix(in srgb, var(--accent) 18%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 8%, transparent);
  background: color-mix(in srgb, var(--accent) 5%, transparent);
  animation: scan 5s ease-in-out infinite alternate;
  pointer-events: none;
}

.mark-card {
  position: absolute;
  right: -1.25rem;
  bottom: 0.65rem;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.7rem;
  min-width: 15rem;
  padding: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--border));
  border-radius: 0.75rem;
  background: var(--panel-2);
  color: var(--ink);
  box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.38);
  transform: rotate(-3deg);
}

.mark-check {
  display: grid;
  place-items: center;
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 50%;
  background: var(--accent);
  color: var(--background);
  font-weight: 800;
}

.mark-card strong,
.mark-card small {
  display: block;
}

.mark-card strong {
  font-size: 0.78rem;
}

.mark-card small {
  margin-top: 0.1rem;
  color: var(--muted);
  font-size: 0.68rem;
}

.mark-score {
  color: var(--accent);
  font-size: 0.8rem;
  font-weight: 600;
}

.syntax-chip {
  position: absolute;
  padding: 0.4rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel-2);
  color: var(--secondary-color-lightened);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.62rem;
  box-shadow: 0 0.8rem 2rem rgba(0, 0, 0, 0.25);
}

.chip-one {
  top: 0.4rem;
  right: 5rem;
  transform: rotate(5deg);
}

.chip-two {
  left: -0.3rem;
  bottom: 3rem;
  transform: rotate(-7deg);
}

.hero-footnote {
  grid-column: 1 / -1;
  align-self: end;
  margin: 0;
  color: var(--muted);
  font-size: 0.74rem;
}

@keyframes scan {
  from { transform: translateY(-4rem); }
  to { transform: translateY(5rem); }
}

@media (max-width: 58rem) {
  .hero {
    grid-template-columns: 1fr;
    align-content: start;
  }

  .hero::before {
    display: none;
  }

  .hero-copy {
    padding: 2.5rem 0 0;
  }

  .hero-visual {
    width: min(100%, 38rem);
    padding-top: 1rem;
  }
}

@media (max-width: 34rem) {
  .landing-page {
    padding: 0;
  }

  .hero {
    min-height: 100vh;
    padding: 1.2rem;
    border: 0;
    border-radius: 0;
  }

  h1 {
    font-size: clamp(3rem, 16vw, 4.5rem);
  }

  .hero-visual {
    padding-inline: 0;
    transform: none;
  }

  .mark-card {
    right: -0.3rem;
  }

  .syntax-chip {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .scan-line {
    animation: none;
  }
}
</style>

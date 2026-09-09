<script setup lang="ts">
// ============================================================================
//
// Public product landing page for the unified CambridgeParser study platform.
// ============================================================================

import { RouterLink } from 'vue-router';
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleCheck,
  Clock3,
  Code2,
  FileText,
  Flag,
  Gauge,
  Lightbulb,
  MousePointer2,
  Search,
  Sparkles,
  Target,
  TimerReset,
  TrendingUp,
} from 'lucide-vue-next';
import ThemeSwitcher from '@/components/ThemeSwitcher.vue';

const productAreas = [
  {
    index: '01',
    icon: FileText,
    eyebrow: 'Paper solver',
    title: 'Sit the paper, not a watered-down quiz.',
    description:
      'Work directly on the original PDF with a timer, question navigation, option elimination, flags, and a locked review after you finish.',
    points: ['Original paper layout', 'Question-by-question controls', 'Persisted attempts'],
    links: [{ to: '/browser', label: 'Browse papers' }],
  },
  {
    index: '02',
    icon: BrainCircuit,
    eyebrow: 'Progress intelligence',
    title: 'Turn every attempt into a better next move.',
    description:
      'See subject progress, topic mastery, confidence patterns, pacing, answer changes, and recommendations built from the work you actually did.',
    points: ['Subject-scoped analytics', 'Focus and confidence signals', 'Topic recommendations'],
    links: [{ to: '/stats', label: 'See your progress' }],
  },
  {
    index: '03',
    icon: Code2,
    eyebrow: 'Pseudocode lab',
    title: 'Practice Paper 2 with exam-level discipline.',
    description:
      'Learn core syllabus techniques, search the 9618 question corpus, write or complete pseudocode, and receive feedback against the real rubric.',
    points: ['Guided syllabus lessons', 'Searchable question corpus', 'WASM parser diagnostics', 'Rubric-grounded grading'],
    links: [
      { to: '/problems', label: 'Explore problems' },
      { to: '/learn', label: 'Learn a topic' },
    ],
  },
];

const workflow = [
  {
    number: '01',
    title: 'Choose the work',
    description: 'Find a supported MCQ paper or a focused pseudocode problem.',
    icon: Search,
  },
  {
    number: '02',
    title: 'Solve honestly',
    description: 'Use exam-shaped tools without losing the context of the original question.',
    icon: TimerReset,
  },
  {
    number: '03',
    title: 'Review the evidence',
    description: 'Inspect marks, decisions, confidence, timing, and feedback—not just a score.',
    icon: BarChart3,
  },
  {
    number: '04',
    title: 'Target the next gap',
    description: 'Return to the topics and question types where another attempt matters most.',
    icon: Target,
  },
];
</script>

<template>
  <main id="top" class="landing-page">
    <a class="skip-link" href="#main-content">Skip to content</a>

    <nav class="landing-nav" aria-label="Primary navigation">
      <RouterLink class="brand" to="/" aria-label="CambridgeParser home">
        <span class="brand-mark" aria-hidden="true">
          <BookOpenCheck />
        </span>
        <span>CambridgeParser</span>
      </RouterLink>

      <div class="nav-links" aria-label="Page sections">
        <a href="#platform">Platform</a>
        <a href="#workflow">How it works</a>
        <a href="#insights">Insights</a>
      </div>

      <div class="nav-actions">
        <ThemeSwitcher />
        <RouterLink class="nav-login" to="/login">Sign in</RouterLink>
      </div>
    </nav>

    <div id="main-content">
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero-glow" aria-hidden="true"></div>

        <div class="hero-copy">
          <p class="eyebrow"><Sparkles /> One workspace for Cambridge revision</p>
          <h1 id="hero-title">
            Study the paper.<br />
            <span>Understand the pattern.</span>
          </h1>
          <p class="hero-lede">
            Sit real MCQ papers, practise 9618 pseudocode, and turn both into a
            clear picture of what to work on next.
          </p>

          <div class="hero-actions">
            <RouterLink class="button button-primary" to="/login">
              Start studying <ArrowRight />
            </RouterLink>
            <a class="button button-secondary" href="#platform">
              Explore the platform <ChevronRight />
            </a>
          </div>

          <ul class="hero-proof" aria-label="Platform highlights">
            <li><Check /> Original exam papers</li>
            <li><Check /> One progress history</li>
            <li><Check /> No installation</li>
          </ul>
        </div>

        <div class="hero-product" aria-label="Example CambridgeParser study workspace">
          <div class="product-window">
            <div class="product-topbar">
              <div class="window-brand">
                <span class="window-dot"></span>
                <span>Study workspace</span>
              </div>
              <span class="live-label"><span></span> Attempt in progress</span>
            </div>

            <div class="workspace-tabs" aria-hidden="true">
              <span class="active"><FileText /> Paper</span>
              <span><Code2 /> Pseudocode</span>
              <span><BarChart3 /> Progress</span>
            </div>

            <div class="workspace-body">
              <div class="paper-pane">
                <div class="paper-heading">
                  <div>
                    <span class="micro-label">0610 · Biology</span>
                    <strong>Question 18 of 40</strong>
                  </div>
                  <span class="timer"><Clock3 /> 31:42</span>
                </div>

                <div class="question-sheet">
                  <span class="question-number">18</span>
                  <p>Which structure controls the movement of substances into and out of a cell?</p>
                  <div class="answer-grid">
                    <span><b>A</b> cell membrane</span>
                    <span><b>B</b> cell wall</span>
                    <span><b>C</b> cytoplasm</span>
                    <span><b>D</b> nucleus</span>
                  </div>
                </div>

                <div class="paper-toolbar">
                  <span><MousePointer2 /> Select answer</span>
                  <span><Flag /> Flag for review</span>
                </div>
              </div>

              <aside class="signal-pane">
                <div class="signal-heading">
                  <span class="micro-label">Next focus</span>
                  <Lightbulb />
                </div>
                <strong>Cell structure</strong>
                <p>Recent evidence suggests one more focused pass.</p>
                <div class="signal-chart" aria-hidden="true">
                  <span style="--bar: 72%"></span>
                  <span style="--bar: 44%"></span>
                  <span style="--bar: 61%"></span>
                  <span style="--bar: 36%"></span>
                  <span style="--bar: 52%"></span>
                </div>
                <div class="signal-note"><TrendingUp /> Built from completed attempts</div>
              </aside>
            </div>
          </div>

          <div class="floating-card floating-score" aria-hidden="true">
            <CircleCheck />
            <div><strong>Review saved</strong><span>Every decision stays attached</span></div>
          </div>
          <div class="floating-card floating-code" aria-hidden="true">
            <Code2 />
            <div><strong>Parser ready</strong><span>Syntax checked locally</span></div>
          </div>
        </div>
      </section>

      <section id="platform" class="platform section-shell" aria-labelledby="platform-title">
        <div class="section-intro">
          <p class="section-kicker">The complete platform</p>
          <h2 id="platform-title">Three tools. One learning loop.</h2>
          <p>
            CambridgeParser has grown beyond a single editor. Papers, code, and
            progress now share one account and one continuous record of your work.
          </p>
        </div>

        <div class="product-grid">
          <article v-for="area in productAreas" :key="area.index" class="product-card">
            <div class="product-card-top">
              <span class="card-index">{{ area.index }}</span>
              <span class="card-icon"><component :is="area.icon" /></span>
            </div>
            <p class="card-eyebrow">{{ area.eyebrow }}</p>
            <h3>{{ area.title }}</h3>
            <p class="card-description">{{ area.description }}</p>
            <ul>
              <li v-for="point in area.points" :key="point"><Check /> {{ point }}</li>
            </ul>
            <div class="card-links">
              <RouterLink v-for="link in area.links" :key="link.to" :to="link.to">
                {{ link.label }} <ArrowRight />
              </RouterLink>
            </div>
          </article>
        </div>
      </section>

      <section id="workflow" class="workflow section-shell" aria-labelledby="workflow-title">
        <div class="workflow-heading">
          <p class="section-kicker">A repeatable study system</p>
          <h2 id="workflow-title">From “I did a paper” to “I know what changed.”</h2>
        </div>

        <ol class="workflow-list">
          <li v-for="step in workflow" :key="step.number">
            <div class="workflow-icon"><component :is="step.icon" /></div>
            <span>{{ step.number }}</span>
            <h3>{{ step.title }}</h3>
            <p>{{ step.description }}</p>
          </li>
        </ol>
      </section>

      <section class="showcase section-shell" aria-label="Platform details">
        <article class="showcase-block paper-showcase">
          <div class="showcase-copy">
            <p class="section-kicker">Paper-first by design</p>
            <h2>Keep the context Cambridge put on the page.</h2>
            <p>
              Diagrams, tables, wording, and page structure matter. The solver
              keeps the original PDF in view while giving you fast controls for
              answering, eliminating options, flagging uncertainty, and moving
              between questions.
            </p>
            <ul class="detail-list">
              <li><CircleCheck /> Clickable question navigation</li>
              <li><CircleCheck /> Review answers against the marking scheme</li>
              <li><CircleCheck /> Attempts persist into dashboard and stats</li>
            </ul>
            <RouterLink class="text-link" to="/browser">Find a paper <ArrowRight /></RouterLink>
          </div>

          <div class="paper-stack" aria-hidden="true">
            <div class="paper-shadow paper-shadow-one"></div>
            <div class="paper-shadow paper-shadow-two"></div>
            <div class="exam-paper">
              <div class="exam-header">
                <span>Cambridge IGCSE™</span>
                <b>BIOLOGY</b>
                <small>0610/21 · Multiple Choice</small>
              </div>
              <div class="exam-rule"></div>
              <div class="exam-question">
                <b>18</b>
                <div>
                  <span class="text-line long"></span>
                  <span class="text-line medium"></span>
                  <div class="cell-diagram"><span></span><i></i><b></b></div>
                  <div class="exam-options">
                    <span>A</span><span>B</span><span>C</span><span>D</span>
                  </div>
                </div>
              </div>
              <div class="annotation-ring">A</div>
              <div class="annotation-note">active question</div>
            </div>
          </div>
        </article>

        <article class="showcase-block code-showcase">
          <div class="code-preview" aria-hidden="true">
            <div class="code-preview-bar">
              <span>9618 · Arrays</span>
              <span>4 marks</span>
            </div>
            <pre><span>01</span> <b>PROCEDURE</b> FindLargest(Values)
<span>02</span>   Largest ← Values[1]
<span>03</span>   <b>FOR</b> Index ← 2 <b>TO</b> LENGTH(Values)
<span>04</span>     <b>IF</b> Values[Index] &gt; Largest <b>THEN</b>
<span>05</span>       Largest ← Values[Index]
<span>06</span>     <b>ENDIF</b>
<span>07</span>   <b>NEXT</b> Index
<span>08</span> <b>ENDPROCEDURE</b></pre>
            <div class="code-result">
              <CircleCheck />
              <div><strong>Structure recognised</strong><span>Ready for rubric grading</span></div>
              <span>3/4</span>
            </div>
          </div>

          <div class="showcase-copy">
            <p class="section-kicker">More than syntax highlighting</p>
            <h2>Write pseudocode where the question and rubric stay close.</h2>
            <p>
              Move from a searchable exam-question corpus into a focused editor.
              Catch supported syntax errors in the browser, complete structured
              blanks, and submit free-form answers for rubric-level feedback.
            </p>
            <ul class="detail-list">
              <li><CircleCheck /> Direct links to individual questions</li>
              <li><CircleCheck /> Local parser feedback without a server round trip</li>
              <li><CircleCheck /> Marking points shown beside the response</li>
            </ul>
            <RouterLink class="text-link" to="/problems">Open the problem set <ArrowRight /></RouterLink>
          </div>
        </article>
      </section>

      <section id="insights" class="insights section-shell" aria-labelledby="insights-title">
        <div class="insights-copy">
          <p class="section-kicker">Useful signals, not vanity numbers</p>
          <h2 id="insights-title">Accuracy alone is too blunt.</h2>
          <p>
            CambridgeParser keeps the evidence around an answer so the review can
            separate a knowledge gap from a rushed guess, fading retention, or
            misplaced confidence.
          </p>
          <RouterLink class="button button-secondary" to="/stats">
            Explore progress <ArrowRight />
          </RouterLink>
        </div>

        <div class="insight-grid">
          <article>
            <div class="insight-icon"><Gauge /></div>
            <span>Focus</span>
            <h3>How the answer happened</h3>
            <p>Timing, elimination, changes, flags, and confidence retain the story behind the mark.</p>
          </article>
          <article>
            <div class="insight-icon"><TrendingUp /></div>
            <span>Mastery</span>
            <h3>Evidence over time</h3>
            <p>Recent work carries more weight, while thin evidence stays visibly uncertain.</p>
          </article>
          <article>
            <div class="insight-icon"><BrainCircuit /></div>
            <span>Next step</span>
            <h3>A focused return path</h3>
            <p>Recommendations surface topics that are weak, fading, or ready for productive practice.</p>
          </article>
        </div>
      </section>

      <section class="final-cta section-shell" aria-labelledby="cta-title">
        <div class="cta-mark" aria-hidden="true"><BookOpenCheck /></div>
        <p class="section-kicker">Your next attempt starts here</p>
        <h2 id="cta-title">Build a revision record that gets more useful every time you study.</h2>
        <p>One account for papers, pseudocode, review, and progress.</p>
        <RouterLink class="button button-primary" to="/login">
          Start with CambridgeParser <ArrowRight />
        </RouterLink>
      </section>
    </div>

    <footer class="landing-footer section-shell">
      <RouterLink class="brand" to="/" aria-label="CambridgeParser home">
        <span class="brand-mark" aria-hidden="true"><BookOpenCheck /></span>
        <span>CambridgeParser</span>
      </RouterLink>
      <div class="footer-middle">
        <p>Past-paper practice and pseudocode in one focused workspace.</p>
        <nav aria-label="Legal links">
          <RouterLink to="/privacy">Privacy Policy</RouterLink>
          <RouterLink to="/terms">Terms and Conditions</RouterLink>
          <RouterLink to="/data-deletion">Data deletion</RouterLink>
        </nav>
      </div>
      <a href="#top">Back to top <ArrowRight /></a>
    </footer>
  </main>
</template>

<style scoped>
.landing-page {
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 82% 5%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 28rem),
    radial-gradient(circle at 12% 42%, color-mix(in srgb, var(--secondary-color) 5%, transparent), transparent 34rem),
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

.section-shell,
.landing-nav,
.hero {
  width: min(calc(100% - 3rem), 82rem);
  margin-inline: auto;
}

.landing-nav {
  position: relative;
  z-index: 20;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  min-height: 5rem;
  border-bottom: 1px solid var(--border);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  width: max-content;
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

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.8rem;
}

.nav-links a,
.nav-login {
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 600;
  text-decoration: none;
  transition: color 160ms ease;
}

.nav-links a:hover,
.nav-login:hover { color: var(--text); }

.nav-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.65rem;
}

.nav-login {
  padding: 0.55rem 0.9rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  color: var(--text);
}

.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 0.88fr) minmax(31rem, 1.12fr);
  gap: clamp(3rem, 7vw, 7rem);
  align-items: center;
  min-height: calc(100vh - 5rem);
  padding-block: clamp(4.5rem, 8vw, 8rem);
}

.hero-glow {
  position: absolute;
  top: 8%;
  right: 13%;
  width: 18rem;
  height: 18rem;
  border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent);
  border-radius: 50%;
  box-shadow:
    0 0 0 5rem color-mix(in srgb, var(--accent) 2%, transparent),
    0 0 0 10rem color-mix(in srgb, var(--accent) 1%, transparent);
  pointer-events: none;
}

.hero-copy { position: relative; z-index: 2; }

.eyebrow,
.section-kicker,
.micro-label,
.card-eyebrow {
  font-family: var(--font-mono);
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1.5rem;
  color: var(--accent);
  font-size: 0.68rem;
  font-weight: 600;
}

.eyebrow svg { width: 0.9rem; height: 0.9rem; }

.hero h1 {
  max-width: 46rem;
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(3.5rem, 6.4vw, 6.7rem);
  font-weight: 560;
  letter-spacing: -0.065em;
  line-height: 0.93;
}

.hero h1 span { color: var(--accent); }

.hero-lede {
  max-width: 38rem;
  margin: 1.8rem 0 0;
  color: var(--muted);
  font-size: clamp(1rem, 1.4vw, 1.2rem);
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 2.2rem;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  min-height: 2.85rem;
  box-sizing: border-box;
  padding: 0.75rem 1rem;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 650;
  text-decoration: none;
  transition: transform 160ms ease, background 160ms ease, border-color 160ms ease;
}

.button svg,
.text-link svg,
.product-card > a svg,
.landing-footer > a svg {
  width: 1rem;
  height: 1rem;
  transition: transform 160ms ease;
}

.button:hover { transform: translateY(-2px); }
.button:hover svg,
.text-link:hover svg,
.product-card > a:hover svg,
.landing-footer > a:hover svg { transform: translateX(3px); }

.button-primary {
  background: var(--accent);
  color: var(--background);
}

.button-primary:hover { background: var(--secondary-color-lightened); }

.button-secondary {
  border-color: var(--border);
  background: color-mix(in srgb, var(--tertiary-background) 72%, transparent);
  color: var(--text);
}

.button-secondary:hover { border-color: color-mix(in srgb, var(--accent) 48%, var(--border)); }

.hero-proof {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.2rem;
  margin: 1.5rem 0 0;
  padding: 0;
  color: var(--muted);
  font-size: 0.7rem;
  list-style: none;
}

.hero-proof li { display: inline-flex; align-items: center; gap: 0.35rem; }
.hero-proof svg { width: 0.8rem; height: 0.8rem; color: var(--success); }

.hero-product {
  position: relative;
  z-index: 2;
  perspective: 80rem;
}

.product-window {
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--accent) 22%, var(--border));
  border-radius: var(--radius-card);
  background: var(--secondary-background);
  box-shadow: var(--card-shadow);
  transform: rotateY(-4deg) rotateX(1deg);
  transform-origin: center right;
}

.product-topbar,
.workspace-tabs,
.paper-heading,
.signal-heading,
.code-preview-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.product-topbar {
  min-height: 2.7rem;
  padding-inline: 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.62rem;
}

.window-brand,
.live-label,
.timer,
.paper-toolbar span,
.signal-note {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.window-dot,
.live-label > span {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 50%;
  background: var(--accent);
}

.live-label { color: var(--accent); }
.live-label > span { box-shadow: 0 0 0 0.25rem color-mix(in srgb, var(--accent) 10%, transparent); }

.workspace-tabs {
  justify-content: flex-start;
  gap: 0.35rem;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid var(--border);
}

.workspace-tabs span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.48rem 0.65rem;
  border-radius: var(--radius-control);
  color: var(--muted);
  font-size: 0.65rem;
}

.workspace-tabs span.active { background: var(--tertiary-background); color: var(--text); }
.workspace-tabs svg { width: 0.8rem; height: 0.8rem; }

.workspace-body {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(11rem, 0.75fr);
  min-height: 24rem;
}

.paper-pane { padding: 1.25rem; }

.paper-heading strong,
.signal-pane > strong {
  display: block;
  margin-top: 0.25rem;
  font-family: var(--font-display);
}

.paper-heading strong { font-size: 0.86rem; }

.micro-label {
  color: var(--muted);
  font-size: 0.55rem;
}

.timer {
  padding: 0.45rem 0.55rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.62rem;
}

.timer svg { width: 0.72rem; height: 0.72rem; }

.question-sheet {
  position: relative;
  min-height: 14rem;
  margin-top: 1rem;
  padding: 1.4rem 1.2rem 1.2rem 3rem;
  border: 1px solid color-mix(in srgb, var(--paper-ink) 10%, var(--border));
  background: var(--paper);
  color: var(--paper-ink);
}

.question-number {
  position: absolute;
  top: 1.4rem;
  left: 1.15rem;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
}

.question-sheet p {
  margin: 0;
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 550;
  line-height: 1.6;
}

.answer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.55rem;
  margin-top: 1.4rem;
}

.answer-grid span {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem;
  border: 1px solid color-mix(in srgb, var(--paper-ink) 13%, transparent);
  font-size: 0.6rem;
}

.answer-grid span:first-child {
  border-color: color-mix(in srgb, var(--accent) 68%, var(--paper-ink));
  background: color-mix(in srgb, var(--accent) 12%, var(--paper));
}

.answer-grid b {
  display: grid;
  width: 1.2rem;
  height: 1.2rem;
  place-items: center;
  border-radius: 50%;
  background: var(--paper-ink);
  color: var(--paper);
  font-size: 0.55rem;
}

.paper-toolbar {
  display: flex;
  gap: 1rem;
  margin-top: 0.85rem;
  color: var(--muted);
  font-size: 0.58rem;
}

.paper-toolbar svg { width: 0.72rem; height: 0.72rem; }

.signal-pane {
  padding: 1.25rem;
  border-left: 1px solid var(--border);
  background: color-mix(in srgb, var(--tertiary-background) 60%, transparent);
}

.signal-heading svg { width: 1rem; height: 1rem; color: var(--accent); }
.signal-pane > strong { margin-top: 1.15rem; font-size: 1rem; }
.signal-pane > p { margin: 0.6rem 0 0; color: var(--muted); font-size: 0.65rem; line-height: 1.55; }

.signal-chart {
  display: flex;
  align-items: flex-end;
  gap: 0.35rem;
  height: 7.5rem;
  margin-top: 1.25rem;
  padding-bottom: 0.45rem;
  border-bottom: 1px solid var(--border);
}

.signal-chart span {
  width: 100%;
  height: var(--bar);
  border-radius: calc(var(--radius-control) / 2) calc(var(--radius-control) / 2) 0 0;
  background: color-mix(in srgb, var(--accent) 65%, var(--primary-color));
  opacity: 0.35;
}

.signal-chart span:nth-child(3) { opacity: 1; }

.signal-note {
  margin-top: 1rem;
  color: var(--muted);
  font-size: 0.55rem;
}

.signal-note svg { width: 0.72rem; height: 0.72rem; color: var(--success); }

.floating-card {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 11.5rem;
  padding: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--accent) 32%, var(--border));
  border-radius: var(--radius-control);
  background: var(--secondary-background);
  box-shadow: var(--card-shadow);
  animation: float 5s ease-in-out infinite;
}

.floating-card > svg { width: 1.15rem; height: 1.15rem; color: var(--accent); }
.floating-card strong,
.floating-card span { display: block; }
.floating-card strong { font-size: 0.66rem; }
.floating-card span { margin-top: 0.16rem; color: var(--muted); font-size: 0.52rem; }
.floating-score { right: -1.25rem; bottom: -1.25rem; }
.floating-code { top: 6rem; left: -2rem; animation-delay: -2.5s; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-0.5rem); }
}

.platform,
.workflow,
.showcase,
.insights {
  padding-block: clamp(5rem, 10vw, 9rem);
}

.section-intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.65fr);
  gap: 1rem 5rem;
  align-items: end;
  margin-bottom: 3rem;
}

.section-kicker {
  grid-column: 1 / -1;
  margin: 0 0 0.65rem;
  color: var(--accent);
  font-size: 0.65rem;
  font-weight: 650;
}

.section-intro h2,
.workflow-heading h2,
.showcase-copy h2,
.insights-copy h2,
.final-cta h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.1rem, 4vw, 4.2rem);
  font-weight: 560;
  letter-spacing: -0.05em;
  line-height: 1.04;
}

.section-intro > p:last-child,
.showcase-copy > p,
.insights-copy > p,
.final-cta > p:not(.section-kicker) {
  margin: 0;
  color: var(--muted);
  line-height: 1.75;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.product-card {
  display: flex;
  min-height: 32rem;
  flex-direction: column;
  padding: clamp(1.5rem, 3vw, 2.25rem);
  border-right: 1px solid var(--border);
  background: color-mix(in srgb, var(--secondary-background) 65%, transparent);
  transition: background 180ms ease, transform 180ms ease;
}

.product-card:first-child { border-left: 1px solid var(--border); }
.product-card:hover { background: var(--secondary-background); transform: translateY(-0.35rem); }

.product-card-top { display: flex; align-items: center; justify-content: space-between; }
.card-index { color: var(--muted); font-family: var(--font-mono); font-size: 0.62rem; }
.card-icon,
.workflow-icon,
.insight-icon,
.cta-mark {
  display: grid;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-control);
  background: var(--tertiary-background);
  color: var(--accent);
}

.card-icon { width: 2.6rem; height: 2.6rem; }
.card-icon svg { width: 1.15rem; height: 1.15rem; }
.card-eyebrow { margin: 3.2rem 0 0.8rem; color: var(--accent); font-size: 0.6rem; }

.product-card h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.45rem, 2.25vw, 2rem);
  font-weight: 540;
  letter-spacing: -0.04em;
  line-height: 1.15;
}

.card-description {
  margin: 1rem 0 0;
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.7;
}

.product-card ul,
.detail-list {
  display: grid;
  gap: 0.65rem;
  margin: 1.5rem 0 0;
  padding: 0;
  list-style: none;
}

.product-card li,
.detail-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--muted);
  font-size: 0.7rem;
}

.product-card li svg,
.detail-list li svg { width: 0.85rem; height: 0.85rem; color: var(--success); flex: 0 0 auto; }

.card-links a,
.text-link,
.landing-footer > a {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  width: max-content;
  color: var(--text);
  font-family: var(--font-display);
  font-size: 0.74rem;
  font-weight: 650;
  text-decoration: none;
}

.card-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.35rem;
  margin-top: auto;
  padding-top: 2rem;
}

.workflow {
  border-top: 1px solid var(--border);
}

.workflow-heading {
  display: grid;
  grid-template-columns: 0.5fr 1fr;
  gap: 3rem;
  align-items: start;
}

.workflow-heading .section-kicker { grid-column: auto; padding-top: 0.5rem; }

.workflow-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin: 4rem 0 0;
  padding: 0;
  list-style: none;
}

.workflow-list li {
  position: relative;
  min-height: 15rem;
  padding: 1.5rem 1.5rem 1.5rem 0;
  border-top: 1px solid var(--border);
}

.workflow-list li:not(:last-child)::after {
  content: '';
  position: absolute;
  top: -1px;
  right: 1.5rem;
  left: 0;
  height: 1px;
  background: var(--accent);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 300ms ease;
}

.workflow-list li:hover::after { transform: scaleX(1); }
.workflow-icon { width: 2.5rem; height: 2.5rem; margin-bottom: 2rem; }
.workflow-icon svg { width: 1rem; height: 1rem; }
.workflow-list li > span { color: var(--accent); font-family: var(--font-mono); font-size: 0.6rem; }
.workflow-list h3 { margin: 0.75rem 0 0; font-family: var(--font-display); font-size: 1rem; }
.workflow-list p { max-width: 15rem; margin: 0.65rem 0 0; color: var(--muted); font-size: 0.72rem; line-height: 1.65; }

.showcase {
  display: grid;
  gap: clamp(6rem, 12vw, 11rem);
}

.showcase-block {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: clamp(3rem, 8vw, 8rem);
  align-items: center;
}

.showcase-copy .section-kicker { grid-column: auto; }
.showcase-copy > p { margin-top: 1.4rem; }
.detail-list { margin-top: 1.6rem; }
.text-link { margin-top: 2rem; color: var(--accent); }

.paper-stack { position: relative; min-height: 34rem; }

.paper-shadow,
.exam-paper {
  position: absolute;
  top: 50%;
  left: 50%;
  width: min(78%, 24rem);
  aspect-ratio: 0.71;
  border: 1px solid var(--border);
}

.paper-shadow { background: var(--tertiary-background); }
.paper-shadow-one { transform: translate(-58%, -48%) rotate(-7deg); }
.paper-shadow-two { transform: translate(-42%, -52%) rotate(6deg); }

.exam-paper {
  box-sizing: border-box;
  padding: 2.5rem 2rem;
  overflow: hidden;
  background: var(--paper);
  color: var(--paper-ink);
  box-shadow: var(--card-shadow);
  transform: translate(-50%, -50%) rotate(-1deg);
}

.exam-header { display: grid; gap: 0.3rem; font-size: 0.52rem; }
.exam-header b { font-size: 0.9rem; letter-spacing: 0.08em; }
.exam-rule { height: 2px; margin: 1rem 0 1.5rem; background: var(--paper-ink); opacity: 0.75; }
.exam-question { display: grid; grid-template-columns: auto 1fr; gap: 0.8rem; font-size: 0.68rem; }
.text-line { display: block; height: 0.32rem; margin-bottom: 0.45rem; background: var(--paper-ink); opacity: 0.65; }
.text-line.long { width: 92%; }
.text-line.medium { width: 67%; }

.cell-diagram {
  position: relative;
  width: 7.5rem;
  height: 6rem;
  margin: 2rem auto 1.2rem;
  border: 2px solid var(--paper-ink);
  border-radius: 46% 54% 55% 45%;
}

.cell-diagram span,
.cell-diagram i,
.cell-diagram b {
  position: absolute;
  display: block;
  border: 1px solid var(--paper-ink);
  border-radius: 50%;
}

.cell-diagram span { inset: 1rem 1.2rem; }
.cell-diagram i { top: 2rem; left: 2.7rem; width: 1.6rem; height: 1.25rem; background: color-mix(in srgb, var(--accent) 18%, var(--paper)); }
.cell-diagram b { right: 1.1rem; bottom: 0.8rem; width: 0.7rem; height: 0.7rem; }
.exam-options { display: flex; justify-content: space-between; margin-top: 1.6rem; font-family: var(--font-mono); }

.annotation-ring {
  position: absolute;
  right: 1.55rem;
  bottom: 2.2rem;
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 2px solid var(--accent);
  border-radius: 50%;
  color: var(--accent);
  font-family: var(--font-mono);
  font-weight: 700;
}

.annotation-note {
  position: absolute;
  right: 4rem;
  bottom: 2.75rem;
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 0.55rem;
}

.code-preview {
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--accent) 25%, var(--border));
  border-radius: var(--radius-card);
  background: var(--term);
  box-shadow: var(--card-shadow);
}

.code-preview-bar {
  padding: 0.9rem 1rem;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.62rem;
}

.code-preview pre {
  margin: 0;
  padding: clamp(1.2rem, 3vw, 2rem);
  overflow-x: auto;
  color: var(--term-ink);
  font-family: var(--font-mono);
  font-size: clamp(0.58rem, 1.1vw, 0.76rem);
  line-height: 2;
}

.code-preview pre span { display: inline-block; width: 1.7rem; color: var(--muted); user-select: none; }
.code-preview pre b { color: var(--accent); font-weight: 650; }

.code-result {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.75rem;
  margin: 0 1rem 1rem;
  padding: 0.8rem;
  border: 1px solid color-mix(in srgb, var(--success) 35%, var(--border));
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--success-darkened) 45%, var(--tertiary-background));
}

.code-result > svg { width: 1.1rem; height: 1.1rem; color: var(--success); }
.code-result strong,
.code-result div span { display: block; }
.code-result strong { font-size: 0.7rem; }
.code-result div span { margin-top: 0.15rem; color: var(--muted); font-size: 0.55rem; }
.code-result > span { color: var(--success); font-family: var(--font-mono); font-size: 0.72rem; }

.insights {
  display: grid;
  grid-template-columns: minmax(0, 0.72fr) minmax(32rem, 1.28fr);
  gap: clamp(3rem, 8vw, 8rem);
  align-items: start;
  border-top: 1px solid var(--border);
}

.insights-copy .section-kicker { grid-column: auto; }
.insights-copy > p { margin-top: 1.25rem; }
.insights-copy .button { margin-top: 1.8rem; }

.insight-grid { display: grid; grid-template-columns: repeat(3, 1fr); }
.insight-grid article { min-height: 20rem; padding: 1.4rem; border: 1px solid var(--border); border-right: 0; }
.insight-grid article:last-child { border-right: 1px solid var(--border); }
.insight-icon { width: 2.4rem; height: 2.4rem; margin-bottom: 3.5rem; }
.insight-icon svg { width: 1rem; height: 1rem; }
.insight-grid article > span { color: var(--accent); font-family: var(--font-mono); font-size: 0.58rem; text-transform: uppercase; }
.insight-grid h3 { margin: 0.75rem 0 0; font-family: var(--font-display); font-size: 1rem; line-height: 1.35; }
.insight-grid p { margin: 0.7rem 0 0; color: var(--muted); font-size: 0.68rem; line-height: 1.65; }

.final-cta {
  position: relative;
  display: grid;
  justify-items: center;
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 8vw, 8rem);
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--accent) 25%, var(--border));
  border-radius: var(--radius-card);
  background:
    linear-gradient(color-mix(in srgb, var(--accent) 6%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--accent) 6%, transparent) 1px, transparent 1px),
    var(--secondary-background);
  background-size: 2.5rem 2.5rem;
  text-align: center;
}

.cta-mark { width: 3.3rem; height: 3.3rem; margin-bottom: 1.6rem; }
.cta-mark svg { width: 1.4rem; height: 1.4rem; }
.final-cta .section-kicker { grid-column: auto; }
.final-cta h2 { max-width: 52rem; }
.final-cta > p:not(.section-kicker) { margin-top: 1rem; }
.final-cta .button { margin-top: 2rem; }

.landing-footer {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  min-height: 8rem;
  margin-top: 4rem;
  border-top: 1px solid var(--border);
}

.footer-middle { text-align: center; }
.footer-middle p { margin: 0; color: var(--muted); font-size: 0.7rem; }
.footer-middle nav { display: flex; flex-wrap: wrap; justify-content: center; gap: 0.5rem 1rem; margin-top: 0.6rem; }
.footer-middle a { color: var(--muted); font-size: 0.68rem; text-underline-offset: 0.2em; }
.footer-middle a:hover { color: var(--text); }
.landing-footer > a:last-child { justify-self: end; color: var(--muted); }
.landing-footer > a:last-child svg { transform: rotate(-45deg); }

a:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

@media (max-width: 68rem) {
  .hero {
    grid-template-columns: 1fr;
    gap: 4rem;
    padding-top: 5rem;
  }

  .hero-copy { max-width: 50rem; }
  .hero-product { width: min(100%, 46rem); justify-self: center; }
  .product-window { transform: none; }
  .section-intro { grid-template-columns: 1fr; max-width: 46rem; }
  .product-card { min-height: 34rem; }
  .showcase-block { gap: 3rem; }
  .insights { grid-template-columns: 1fr; }
  .insights-copy { max-width: 42rem; }
}

@media (max-width: 52rem) {
  .landing-nav { grid-template-columns: 1fr auto; }
  .nav-links { display: none; }
  .product-grid { grid-template-columns: 1fr; border-bottom: 0; }
  .product-card { min-height: 0; border: 1px solid var(--border); border-top: 0; }
  .product-card:first-child { border-top: 1px solid var(--border); }
  .card-links { margin-top: 2rem; }
  .card-eyebrow { margin-top: 2rem; }
  .workflow-heading { grid-template-columns: 1fr; gap: 0.5rem; }
  .workflow-list { grid-template-columns: 1fr 1fr; }
  .showcase-block { grid-template-columns: 1fr; }
  .code-showcase .code-preview { order: 2; }
  .paper-stack { min-height: 30rem; }
  .insight-grid { grid-template-columns: 1fr; }
  .insight-grid article { min-height: 0; border-right: 1px solid var(--border); border-bottom: 0; }
  .insight-grid article:last-child { border-bottom: 1px solid var(--border); }
  .insight-icon { margin-bottom: 2rem; }
  .landing-footer { grid-template-columns: 1fr auto; gap: 1rem; }
  .footer-middle { grid-column: 1 / -1; grid-row: 2; }
}

@media (max-width: 42rem) {
  .section-shell,
  .landing-nav,
  .hero { width: min(calc(100% - 2rem), 82rem); }
  .landing-nav { min-height: 4.5rem; }
  .nav-actions :deep(.theme-switcher span) { display: none; }
  .hero { min-height: auto; padding-block: 4rem 6rem; }
  .hero h1 { font-size: clamp(3rem, 14vw, 5rem); }
  .hero-glow { right: -8rem; }
  .workspace-body { grid-template-columns: 1fr; }
  .signal-pane { display: none; }
  .floating-card { display: none; }
  .product-topbar { padding-inline: 0.7rem; }
  .workspace-tabs span { padding-inline: 0.5rem; }
  .workspace-tabs span:nth-child(3) { display: none; }
  .paper-pane { padding: 0.85rem; }
  .answer-grid { grid-template-columns: 1fr; }
  .question-sheet { min-height: 18rem; }
  .workflow-list { grid-template-columns: 1fr; }
  .workflow-list li { min-height: 0; padding-block: 1.5rem 2.5rem; }
  .paper-stack { min-height: 26rem; }
  .exam-paper { width: min(88%, 21rem); padding: 2rem 1.5rem; }
  .paper-shadow { width: min(88%, 21rem); }
  .code-preview pre { font-size: 0.52rem; }
  .landing-footer { min-height: 10rem; }
}

@media (max-width: 30rem) {
  .brand > span:last-child { font-size: 0.78rem; }
  .brand-mark { width: 1.8rem; height: 1.8rem; }
  .nav-login { padding-inline: 0.65rem; }
  .hero-actions { display: grid; }
  .button { width: 100%; }
  .hero-proof { display: grid; }
  .workspace-tabs span { font-size: 0.58rem; }
  .live-label { display: none; }
  .paper-heading { align-items: flex-start; }
  .paper-toolbar { flex-direction: column; gap: 0.45rem; }
  .landing-footer .brand > span:last-child { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>

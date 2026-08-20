// ==========================================================================
// dev server and a live Supabase.
//
// This is the regression check for the MutationObserver feedback loop that
// pinned the Paper Solver at 100% CPU. The unit test in
// tests/stripInlineBackground.test.ts locks the idempotence invariant, but the
// actual defect was in the CALLER (writing the style attribute unconditionally
// from inside an observer watching that attribute), and no DOM-free seam can
// catch that. This can.
//
// Prerequisites:
//   npx supabase start
//   npx vite --port 5177
//   a user matching the credentials below
//   npm i playwright-core        (uses the system Chrome, no browser download)
//
// Run:  BASE=http://localhost:5177 SECONDS=15 node tests/perf/solver-cpu.mjs
//
// Expected on the LOADING screen: ~50% of one core (the lottie animation).
// Expected AFTER starting the exam: <10%.
// A sustained 100% with 0 style recalcs means the loop is back.
// ==========================================================================
// Perf harness for the Paper Solver route. Samples CDP Performance metrics
// while the route is open, so "resource-intensive" becomes a number.
import { chromium } from 'playwright-core';

const BASE   = process.env.BASE   || 'http://localhost:5177';
const SCHEMA = process.env.SCHEMA || '0455_w22_12';
const SECONDS = Number(process.env.SECONDS || 15);
const ROUTE  = process.env.ROUTE || `/solver/${SCHEMA}`;

const browser = await chromium.launch({
  executablePath: '/usr/bin/google-chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});
const page = await browser.newPage();

let consoleCount = 0;
const consoleSample = [];
page.on('console', (m) => {
  consoleCount++;
  if (consoleSample.length < 5) consoleSample.push(m.text().slice(0, 90));
});

// --- sign in through the real login form -------------------------------
await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
await page.fill('input[type="email"]', 'perftest@example.com');
await page.fill('input[type="password"]', 'perftest123456');
await page.click('button[type="submit"]');
await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 15000 });
console.log('signed in ->', new URL(page.url()).pathname);

const cdp = await page.context().newCDPSession(page);
await cdp.send('Performance.enable');

const read = async () => {
  const { metrics } = await cdp.send('Performance.getMetrics');
  return Object.fromEntries(metrics.map((m) => [m.name, m.value]));
};

const before = await read();
const t0 = Date.now();
await page.goto(`${BASE}${ROUTE}`, { waitUntil: 'domcontentloaded' });

const samples = [];
while (Date.now() - t0 < SECONDS * 1000) {
  await new Promise((r) => setTimeout(r, 1000));
  const m = await read();
  samples.push({
    t: ((Date.now() - t0) / 1000).toFixed(1),
    heapMB: (m.JSHeapUsedSize / 1048576).toFixed(1),
    nodes: m.Nodes,
    listeners: m.JSEventListeners,
    recalc: m.RecalcStyleCount,
    layout: m.LayoutCount,
    cpuS: (m.TaskDuration - (before.TaskDuration || 0)).toFixed(2),
  });
}

console.log(`\nroute ${ROUTE}  (${SECONDS}s)`);
console.log('  t/s   heapMB    nodes  listeners    recalcs   layouts   cpu(s)');
for (const s of samples) {
  console.log(
    `  ${String(s.t).padStart(4)}  ${String(s.heapMB).padStart(7)}  ${String(s.nodes).padStart(7)}  ${String(s.listeners).padStart(9)}  ${String(s.recalc).padStart(9)}  ${String(s.layout).padStart(8)}  ${String(s.cpuS).padStart(6)}`,
  );
}
const first = samples[0], last = samples[samples.length - 1];
const span = Number(last.t) - Number(first.t);
console.log(`\nDELTA over ${span}s:`);
console.log(`  heap    ${(last.heapMB - first.heapMB).toFixed(1)} MB`);
console.log(`  nodes   ${last.nodes - first.nodes}`);
console.log(`  recalcs ${last.recalc - first.recalc}   (${((last.recalc - first.recalc) / span).toFixed(0)}/s)`);
console.log(`  layouts ${last.layout - first.layout}   (${((last.layout - first.layout) / span).toFixed(0)}/s)`);
console.log(`  cpu     ${(last.cpuS - first.cpuS).toFixed(2)}s of ${span}s wall  = ${(((last.cpuS - first.cpuS) / span) * 100).toFixed(0)}% of one core`);
console.log(`  console messages: ${consoleCount}`);
if (consoleSample.length) console.log('  sample:', consoleSample.join(' | '));

await browser.close();

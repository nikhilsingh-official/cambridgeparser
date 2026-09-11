// ============================================================================
//
// SEO contract tests for public indexing and route-specific crawler metadata.
// ============================================================================

import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  INDEXABLE_SEO_PAGES,
  SEO_PAGES,
  STATIC_SEO_ROUTES,
  renderSeoDocument,
  resolveSeoMetadata,
} from '../src/lib/seo.ts';
import { config as vercelConfig } from '../vercel.ts';

const expectedPages = [
  'aLevelPseudocode',
  'browser',
  'dashboard',
  'dataDeletion',
  'ide',
  'ideRecord',
  'igcsePseudocode',
  'landing',
  'learn',
  'login',
  'pastPaperSolver',
  'privacy',
  'problems',
  'pseudocodeIde',
  'resetPassword',
  'solver',
  'stats',
  'terms',
] as const;

test('every application page has unique, concise metadata', () => {
  assert.deepEqual(Object.keys(SEO_PAGES).sort(), [...expectedPages]);
  assert.equal(new Set(Object.values(SEO_PAGES).map(page => page.title)).size, expectedPages.length);
  assert.equal(new Set(Object.values(SEO_PAGES).map(page => page.description)).size, expectedPages.length);

  for (const page of Object.values(SEO_PAGES)) {
    assert.ok(page.title.length <= 60, `${page.title} is too long`);
    assert.ok(page.description.length >= 70, `${page.title} description is too short`);
    assert.ok(page.description.length <= 170, `${page.title} description is too long`);
  }
});

test('only public product and policy pages are indexable', () => {
  assert.deepEqual([...INDEXABLE_SEO_PAGES].sort(), [
    'aLevelPseudocode',
    'dataDeletion',
    'igcsePseudocode',
    'landing',
    'pastPaperSolver',
    'privacy',
    'pseudocodeIde',
    'terms',
  ]);

  for (const page of expectedPages) {
    const resolved = resolveSeoMetadata(page, SEO_PAGES[page].canonicalPath);
    assert.equal(resolved.canonicalUrl.startsWith('https://www.cambridgeparser.com/'), true);
    assert.equal(resolved.robots.startsWith(INDEXABLE_SEO_PAGES.has(page) ? 'index, follow' : 'noindex, nofollow'), true);
  }
});

test('dynamic private routes get useful titles without becoming indexable', () => {
  const paper = resolveSeoMetadata('solver', '/solver/9700_w25_13', { schema: '9700_w25_13' });
  assert.equal(paper.title, '9700 W25 13 Paper | CambridgeParser');
  assert.equal(paper.canonicalUrl, 'https://www.cambridgeparser.com/solver/9700_w25_13');
  assert.match(paper.robots, /^noindex, nofollow/);

  const problem = resolveSeoMetadata('ideRecord', '/ide/42', { id: '42' });
  assert.equal(problem.title, 'Pseudocode Problem 42 | CambridgeParser');
  assert.match(problem.robots, /^noindex, nofollow/);
});

test('the static build covers every route metadata shape', () => {
  assert.deepEqual(new Set(STATIC_SEO_ROUTES.map(route => route.page)), new Set(expectedPages));
  assert.equal(new Set(STATIC_SEO_ROUTES.map(route => route.outputFile)).size, expectedPages.length);
});

test('static crawler documents replace every critical head value', () => {
  const template = `<!doctype html><html><head>
    <title>old</title>
    <meta name="description" content="old" />
    <meta name="robots" content="old" />
    <link rel="canonical" href="https://old.example" />
    <meta property="og:title" content="old" />
    <meta property="og:description" content="old" />
    <meta property="og:url" content="https://old.example" />
    <meta name="twitter:title" content="old" />
    <meta name="twitter:description" content="old" />
    <script id="seo-structured-data" type="application/ld+json">{}</script>
  </head><body></body></html>`;
  const seo = resolveSeoMetadata('privacy', '/privacy');
  const rendered = renderSeoDocument(template, seo);

  assert.match(rendered, /<title>Privacy Policy \| CambridgeParser<\/title>/);
  assert.match(rendered, /name="robots" content="index, follow/);
  assert.match(rendered, /rel="canonical" href="https:\/\/www\.cambridgeparser\.com\/privacy"/);
  assert.match(rendered, /property="og:url" content="https:\/\/www\.cambridgeparser\.com\/privacy"/);
  assert.match(rendered, /"@type":"WebPage"/);
  assert.doesNotMatch(rendered, /content="old"/);
});

test('public product documents contain useful HTML before JavaScript runs', () => {
  const template = '<!doctype html><html><head><title>old</title></head><body><div id="app"></div></body></html>';
  const pages = [
    ['landing', 'Cambridge past paper solver and pseudocode IDE'],
    ['pastPaperSolver', 'Cambridge past paper solver'],
    ['pseudocodeIde', 'Cambridge pseudocode IDE'],
    ['igcsePseudocode', 'IGCSE Computer Science pseudocode practice'],
    ['aLevelPseudocode', 'A Level Computer Science pseudocode practice'],
  ] as const;

  for (const [page, heading] of pages) {
    const metadata = SEO_PAGES[page];
    const rendered = renderSeoDocument(
      template,
      resolveSeoMetadata(page, metadata.canonicalPath),
    );
    assert.match(rendered, /<main[\s>]/, page);
    assert.match(rendered, new RegExp(`<h1[^>]*>${heading}<\\/h1>`, 'i'), page);
    assert.match(rendered, /<a href="\//, page);
    assert.doesNotMatch(rendered, /<div id="app"><\/div>/, page);
  }
});

test('sitemap exposes every indexable public product page', async () => {
  const sitemap = await readFile(new URL('../public/sitemap.xml', import.meta.url), 'utf8');
  for (const path of [
    '/',
    '/cambridge-past-paper-solver',
    '/cambridge-pseudocode-ide',
    '/igcse-computer-science-pseudocode',
    '/a-level-computer-science-pseudocode',
    '/privacy',
    '/terms',
    '/data-deletion',
  ]) {
    assert.match(sitemap, new RegExp(`<loc>https://www\\.cambridgeparser\\.com${path === '/' ? '/' : path}<\\/loc>`));
  }
});

test('Vercel serves known routes without turning unknown URLs into soft 404s', async () => {
  assert.equal(vercelConfig.trailingSlash, false);
  const rewrites = vercelConfig.rewrites;
  assert.equal(rewrites.some(rewrite => rewrite.source === '/(.*)'), false);
  assert.ok(rewrites.some(rewrite => rewrite.source === '/cambridge-past-paper-solver'));
  assert.ok(rewrites.some(rewrite => rewrite.source === '/solver/(.*)'));

  const notFound = await readFile(new URL('../public/404.html', import.meta.url), 'utf8');
  assert.match(notFound, /<meta name="robots" content="noindex, nofollow"/);
  assert.match(notFound, /<h1>That page does not exist\.<\/h1>/);

  assert.ok(vercelConfig.redirects.some(redirect =>
    redirect.has.some(condition => condition.type === 'host' && condition.value === 'cambridgeparser.vercel.app')
    && redirect.destination === 'https://www.cambridgeparser.com/$1'
  ));
});

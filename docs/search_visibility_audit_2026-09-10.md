<!-- =========================================================================
     Dated live-site audit focused on why CambridgeParser has little search
     visibility and what to prioritize next. Checked 2026-09-10.
     ========================================================================= -->

# CambridgeParser search-visibility audit

This is a dated companion to [the full SEO setup runbook](./seo_setup.md), not
a replacement for it. The site already has most baseline metadata. Its present
bottleneck is the amount of useful, crawlable public content available for the
queries it wants to rank for.

## Live findings

| Finding | Status | Impact |
|---|---|---|
| `cambridgeparser.com` redirects to `www.cambridgeparser.com` | Good: HTTP 308 | Consolidates the apex and `www` hosts. Vercel recommends choosing one primary host and redirecting the other ([Vercel domain guidance](https://vercel.com/docs/domains/working-with-domains/deploying-and-redirecting)). |
| Homepage canonical | Good: `https://www.cambridgeparser.com/` | The page declares the intended canonical host. |
| Search Console DNS token | Present in the root-domain TXT records | This is consistent with Domain-property verification, although only Search Console can confirm ownership status and collected data. A Domain property covers protocols and subdomains ([Google property types](https://support.google.com/webmasters/answer/34592)). |
| `robots.txt` and `sitemap.xml` | Both return HTTP 200 | Discovery plumbing is present. The sitemap uses absolute canonical URLs, as Google recommends ([Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)). |
| Indexable pages in sitemap | Four: homepage and three legal pages | Only one page addresses a study/product search intent. Privacy, terms, and deletion pages establish trust but are not substitutes for useful search landing pages. |
| Initial homepage HTML | Metadata plus `<div id="app"></div>`; no visible H1 or product copy | Google must execute JavaScript before it can understand the main content and internal links. Google supports this, but says rendering is queued and recommends server-side rendering or prerendering ([Google JavaScript SEO guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)). |
| Keyword-to-page alignment | Weak for “Cambridge past paper solver” | The source title says “Past Papers & Pseudocode IDE”; the rendered H1 says “Study the paper. Understand the pattern.” Neither is a direct, descriptive match for the target intent. Google uses the title, visible main heading, prominent text, and link text when forming result titles ([Google title guidance](https://developers.google.com/search/docs/appearance/title-link)). |
| Unknown paths | Return the homepage shell with HTTP 200 | These can be interpreted as soft 404s. Unknown public URLs should return a real 404 rather than an indexable copy of the homepage shell. |

A sampled web search did not surface CambridgeParser for its brand or the target
phrase. That observation is not a definitive index test: use Search Console's
URL Inspection report to see Google's indexed copy, selected canonical, and
rendered HTML for a specific URL ([URL Inspection](https://support.google.com/webmasters/answer/9012289)).

## Prioritized actions

### 1. Confirm discovery in Search Console today

1. Open the Domain property `cambridgeparser.com`.
2. Submit `https://www.cambridgeparser.com/sitemap.xml` in **Sitemaps**.
3. Inspect `https://www.cambridgeparser.com/`, run **Test live URL**, and view
   the rendered page and HTML. Confirm the H1, body copy, navigation links,
   canonical, and structured data are visible to Google.
4. If it is indexable, use **Request indexing** once. Submission helps discovery
   but does not guarantee indexing or ranking ([Google URL Inspection](https://support.google.com/webmasters/answer/9012289)).
5. In **Page indexing**, check the exact exclusion reason for the homepage. In
   **Performance**, filter queries for `cambridge`, `past paper`, `solver`,
   `pseudocode`, `0478`, and `9618`.

### 2. Prerender the public marketing content

The current build prerenders route-specific `<head>` metadata, but not the Vue
page body. Render the homepage and future public search pages to meaningful HTML
at build time or on the server. Keep authenticated tools client-rendered and
`noindex`; the public pages need visible copy and crawlable `<a href>` links in
their initial responses. Google says every important page should be linked from
another page with descriptive anchor text ([Google link guidance](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)).

### 3. Build a small public content surface around real student intents

Do not generate hundreds of thin pages. Start with several substantial,
original pages whose tools or guidance are useful without signing in:

- `/cambridge-past-paper-solver` — what the solver does, supported subjects,
  screenshots, how marking works, and a clear route into the product.
- `/igcse-computer-science-pseudocode` — 0478 coverage, representative original
  guidance, common task types, and links into practice.
- `/a-level-computer-science-pseudocode` — 9618 coverage and level-specific
  guidance.
- `/cambridge-pseudocode-ide` — syntax supported, examples, parser behavior,
  limitations, and a usable demonstration.
- Durable topic guides for genuine curriculum concepts where CambridgeParser
  can add original explanations and worked examples.

Give each page a unique title, descriptive H1, concise introduction, canonical,
description, and contextual internal links. Use target phrases naturally where
they accurately describe the page. Google prioritizes helpful, original,
people-first content and advises against mass-producing pages primarily for
search traffic ([Google people-first content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)).

### 4. Make the homepage's promise explicit

The homepage can retain its visual headline, but its source title, primary H1,
and opening paragraph should collectively say plainly that CambridgeParser is a
Cambridge past-paper solver and pseudocode practice environment. This improves
both human comprehension and query alignment; it is not a keyword-density task.

### 5. Consolidate every Vercel hostname

Keep the apex-to-`www` redirect. Identify the production `*.vercel.app` alias
and confirm it either redirects to the custom domain or responds with
`X-Robots-Tag: noindex`. Vercel warns that an indexable production alias and a
custom domain can be treated as separate copies; preview deployments are
normally noindexed automatically ([Vercel duplicate-content guidance](https://vercel.com/kb/guide/avoiding-duplicate-content-with-vercel-app-urls)).

### 6. Measure outcomes rather than repeatedly resubmitting

In Search Console, compare 28-day periods and monitor non-branded impressions,
clicks, CTR, and landing pages. Pages with impressions but low CTR are candidates
for clearer titles and descriptions; pages with no impressions usually need
better intent coverage, discovery, or legitimate references from elsewhere
([Google Performance report guidance](https://support.google.com/webmasters/answer/17010961)).

Enable Vercel Speed Insights and watch mobile routes at the 75th percentile.
Google's good Core Web Vitals thresholds are LCP at most 2.5 seconds, INP below
200 milliseconds, and CLS at most 0.1 ([Google Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals),
[Vercel Speed Insights](https://vercel.com/docs/speed-insights)). Vercel Web
Analytics can measure landing-page visits and referrers, but analytics itself is
not a ranking control ([Vercel Web Analytics](https://vercel.com/docs/analytics)).

## What is unlikely to solve this alone

- Adding more meta keywords; Google does not use the keywords meta tag for web
  ranking.
- Repeatedly requesting indexing without adding or materially improving pages.
- Adding unsupported schema or fabricated reviews and ratings.
- Publishing near-duplicate syllabus or past-paper pages whose only purpose is
  matching keyword variations.
- Buying links or posting repetitive promotional comments. Seek genuine mentions
  from computing teachers, school resource pages, revision communities, and
  useful discussions because the tool genuinely helps their audience.

The practical target is not “make Search Console rank the homepage.” Search
Console reports and diagnoses Google's view of the site. The ranking opportunity
comes from exposing the product's real expertise as fast, useful, public pages,
then using Search Console to learn which of those pages and queries are gaining
traction.

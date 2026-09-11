# SEO release and growth runbook

Reviewed against Google Search Central, Search Console, and Vercel documentation
on 2026-09-11. These steps improve discovery and search clarity; none guarantees
indexing or a particular ranking.

## What the application now does

The production build generates crawler-readable HTML for these canonical,
indexable routes:

- `/`
- `/cambridge-past-paper-solver`
- `/cambridge-pseudocode-ide`
- `/igcse-computer-science-pseudocode`
- `/a-level-computer-science-pseudocode`
- `/privacy`, `/terms`, and `/data-deletion`

The five product pages include an H1, opening copy, useful sections, CTAs, and
ordinary `<a href>` internal links in the initial HTML. They do not depend on
Google's JavaScript rendering stage for their main meaning. The content is
generated from `src/lib/publicSeoContent.ts`, which also supplies the rendered
Vue product pages, so crawler and user copy cannot quietly drift apart. The
landing page uses the same central summary and search-focused heading in its
richer Vue layout.

This is build-time static HTML, not server-side rendering. Vue replaces the
initial markup when the application starts. That is appropriate for stable
marketing content; authenticated pages remain client-rendered and `noindex`.
Google can process JavaScript, but static or server-rendered primary content
removes a separate rendering dependency and works for crawlers that do not run
JavaScript ([Google JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)).

The sitemap now contains five product pages and three legal pages. Known app
deep links have explicit Vercel rewrites; there is no catch-all homepage
rewrite. An unknown hard URL can therefore return the custom `404.html` with a
real 404 response instead of a soft 404. The stable
`cambridgeparser.vercel.app` alias is configured to redirect to the same path
on `www.cambridgeparser.com`.

## Deployment acceptance checks

Run these after the new Vercel deployment is promoted to production:

```bash
curl -sS https://www.cambridgeparser.com/ | grep -E '<h1>Cambridge past paper solver|381 canonical'
curl -sS https://www.cambridgeparser.com/igcse-computer-science-pseudocode | grep -E '<h1>IGCSE|205 canonical'
curl -sSI https://www.cambridgeparser.com/not-a-real-page
curl -sSI https://cambridgeparser.vercel.app/cambridge-pseudocode-ide
curl -sS https://www.cambridgeparser.com/sitemap.xml
```

Expected results:

- the first two responses contain useful body content without executing JS;
- the unknown URL returns HTTP 404, not 200 or a homepage redirect;
- the Vercel production alias permanently redirects to the equivalent `www`
  URL;
- the sitemap exposes all eight canonical public URLs.

Also inspect one private route such as `/dashboard` and confirm both its HTML
robots tag and `X-Robots-Tag` say `noindex`.

## Google Search Console: exact next steps

1. Add or retain a **Domain property** for `cambridgeparser.com`, verified with
   the DNS TXT record. This covers HTTP/HTTPS, apex, `www`, and other
   subdomains ([property types](https://support.google.com/webmasters/answer/34592)).
2. In **Sitemaps**, submit exactly
   `https://www.cambridgeparser.com/sitemap.xml`. Re-submit the same sitemap
   after this deployment if Search Console shows the old four-URL fetch.
3. In **URL Inspection**, test the live URL for `/` and each of the four public
   product pages. Check that the page is allowed to index, the rendered HTML
   and screenshot are complete, and the user-declared canonical is the same
   `www` URL.
4. Request indexing once for the homepage and four product pages after the
   deployment. Repeated requests do not accelerate crawling
   ([recrawl guidance](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl)).
5. After Google processes them, confirm the Google-selected canonical matches
   the user-declared canonical. Investigate any “Duplicate” or “Crawled -
   currently not indexed” result page by page rather than changing every tag.
6. In **Performance → Search results**, compare 28-day periods. Track queries
   containing `cambridge`, `past paper`, `solver`, `pseudocode`, `0478`, `9608`,
   and `9618`, then filter by page to see which intent each landing page owns.
7. Watch **Page indexing**, **Core Web Vitals**, **HTTPS**, **Manual actions**,
   and **Security issues**. Use **Links** to identify which useful pages gain
   external references.

Search Console has no keyword field that makes a page rank. It reports how
Google discovered, indexed, and presented the site; an indexing request is not
a ranking request ([URL Inspection](https://support.google.com/webmasters/answer/9012289)).

## Vercel: exact next steps

1. Deploy this revision and make `www.cambridgeparser.com` the primary
   production domain. Keep the apex assigned and permanently redirected to
   `www` ([Vercel custom domains](https://vercel.com/docs/domains/set-up-custom-domain)).
2. Confirm that the configured host redirect catches the exact stable alias
   `cambridgeparser.vercel.app`. If the project dashboard shows a different
   production alias, update the host condition in `vercel.ts`.
3. Enable **Web Analytics** and **Speed Insights** in the project dashboard.
   Their Vue components and packages are already installed in the application
   ([Web Analytics](https://vercel.com/docs/analytics/package),
   [Speed Insights](https://vercel.com/docs/speed-insights/quickstart)).
4. Let field data accumulate, then use Speed Insights to find route-specific
   LCP, INP, and CLS problems. Treat the public landing templates first; they
   are the search entry points.
5. Keep preview deployments protected. Vercel normally adds `noindex` to
   preview and outdated production deployments, but a stable production alias
   needs its own redirect or noindex treatment
   ([Vercel response headers](https://vercel.com/docs/headers/response-headers),
   [duplicate-content guidance](https://vercel.com/kb/guide/avoiding-duplicate-content-with-vercel-app-urls)).

## On-page and content priorities

The homepage is now the broad platform page. Its title and H1 clearly describe
a Cambridge past paper solver and pseudocode IDE. The dedicated solver page is
narrower: it explains the PDF, timer, marking, review, and paper-browser
workflow. Keep those purposes distinct so the two pages do not become
near-duplicates.

The strongest next growth work is useful public material, not more meta tags:

- publish original worked pseudocode examples by technique, with explanations
  that are useful without signing in;
- publish a transparent coverage/methodology page explaining syllabus codes,
  years, deduplication, topic tagging, and known gaps;
- add genuine product screenshots with descriptive filenames, visible captions,
  useful alt text, explicit dimensions, and compressed WebP/AVIF sources;
- add an About/contact page identifying who maintains the tool and how coverage
  is checked;
- add public release notes when coverage or parser behavior changes;
- link each guide contextually to its qualification page and appropriate app
  action.

Do not publish hundreds of thin syllabus/year/query variants. Do not expose
copyrighted paper content merely to create indexable pages. Google recommends
original, useful, people-first content rather than pages made mainly to capture
search variations
([helpful-content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)).

Use concise, descriptive titles and one clear main heading. Exact phrases do
not need repetition; Google can construct title links from the title, headings,
prominent copy, and link text
([title-link guidance](https://developers.google.com/search/docs/appearance/title-link)).

## Internal links, canonicals, and sitemap discipline

Every public page must remain reachable through ordinary descriptive links,
not only JavaScript click handlers. Crawlable anchors help discovery and give
the destination context
([link guidance](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)).

Keep `https://www.cambridgeparser.com` as the only canonical origin. Each
indexable page needs an absolute self-referencing canonical, and internal links
and sitemap entries should use the same URL form. Vercel is configured to
redirect trailing-slash variants to that URL form. Redirects and canonicals are
strong consolidation signals; sitemap inclusion is weaker
([canonicalization guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)).

List only canonical, indexable URLs in the sitemap. Use `<lastmod>` only for a
substantive page update. Google ignores sitemap `<priority>` and `<changefreq>`,
and sitemap submission does not guarantee indexing
([sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)).

Keep login, password recovery, dashboard, solver sessions, problem records,
and personal analytics out of the sitemap and marked `noindex`. Do not block a
URL in `robots.txt` when a crawler needs to fetch it to observe `noindex`
([robots meta guidance](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)).

## Structured data

The homepage has truthful `WebSite` and `WebApplication` data; public secondary
pages use `WebPage`. This helps machines understand the site but is not a
general ranking boost. Do not fabricate ratings, prices, reviews, organization
details, or FAQs for rich-result eligibility. Markup must describe content the
visitor can see
([structured-data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies),
[site-name guidance](https://developers.google.com/search/docs/appearance/site-names)).

## Authority and distribution

An established Reddit result has history, crawlable discussion, and incoming
links. Technical SEO makes CambridgeParser eligible to compete; it does not
create independent authority. Earn relevant references by sharing genuinely
useful guides and tools with teachers, school computing departments, revision
communities, and maintainers of legitimate resource lists. Ask for links only
where the page helps that audience, and avoid bought links, automated directory
submissions, and copied forum posts.

Use Search Console impressions as the first signal. New pages often move from
discovery to low-position impressions before meaningful clicks. Evaluate
changes over weeks, not hours, while continuing to improve the public pages
that already receive relevant impressions.

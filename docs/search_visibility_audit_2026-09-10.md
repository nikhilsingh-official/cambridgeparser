# CambridgeParser search-visibility audit

Originally checked on 2026-09-10 and updated for the 2026-09-11 implementation.
See [the release and growth runbook](./seo_setup.md) for the operational steps.

## Revised state

| Area | Implemented state | Deployment check |
|---|---|---|
| Initial HTML | The build inserts an H1, opening copy, sections, CTAs, and crawlable links into the five product documents. | `curl` production and confirm the body is not an empty `#app` element. |
| Homepage intent | The title and visible H1 identify a Cambridge past paper solver and pseudocode IDE. | Inspect the live title link and rendered H1 in Search Console. |
| Public search surface | Four distinct product/qualification pages supplement the homepage. | Confirm each returns its own content and self-canonical. |
| Sitemap | Eight canonical URLs: five product pages and three legal pages. | Re-submit the sitemap and verify the discovered URL count. |
| Canonical host | Apex redirects to `www`; the stable Vercel alias is configured to redirect path-for-path to `www`. | Check both redirects after production deploy. |
| Unknown paths | The blanket SPA fallback was removed and a noindex custom 404 was added. | Confirm an invented hard URL returns HTTP 404. |
| Private routes | Login and authenticated app routes remain out of the sitemap and carry page/header `noindex`. | Inspect `/dashboard` response metadata. |
| Measurement | Vercel Web Analytics and Speed Insights Vue integrations are installed. | Enable both products in the Vercel dashboard and wait for field data. |

## Why the HTML change matters

The old production response contained only `<div id="app"></div>`, so every
useful word and link depended on a later JavaScript rendering pass. Google can
render JavaScript, but static primary content removes that dependency and is
available to link-preview bots and other crawlers as well. Google recommends
server-side or static rendering as a robust option for JavaScript sites
([Google JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)).

The new Vite post-build step writes route-specific documents from the same
metadata and public-content catalogues used by the browser application. It is
static generation, not an attempt to show search engines different content.
The authenticated application remains client-rendered because its personal
pages are intentionally not search destinations.

## Remaining gaps

The public surface is now technically crawlable but still small. The four new
pages establish distinct solver, IDE, IGCSE, and AS/A Level intents; they are a
foundation rather than a complete content strategy. The largest remaining
opportunities are original worked guides, transparent coverage methodology,
real product screenshots, identifiable maintainer/about information, and
legitimate links from relevant education resources.

The legal pages have crawler-readable titles and summaries before JavaScript;
their full policy text is still rendered by Vue. That is acceptable for the
current static legal content, but moving the full policy bodies into the shared
static renderer would further reduce JavaScript dependence.

The route and alias behavior cannot be proven until this revision is deployed.
Vercel must return the custom 404 with status 404, honor the stable-alias host
redirect, and enable Analytics and Speed Insights in the project dashboard.

## Expected search progression

After deployment, submit and inspect the five product URLs in Search Console.
The first meaningful improvement should be correct discovery, rendering,
canonical selection, and impressions for relevant queries. Ranking above an
established Reddit thread additionally requires stronger public usefulness and
external authority; metadata and sitemap changes alone cannot guarantee that.

Google's documentation treats sitemap submission as a discovery hint and
structured data as eligibility information, not a ranking promise
([sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap),
[structured-data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)).

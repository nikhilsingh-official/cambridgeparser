<!-- =========================================================================

     Production SEO deployment and search-console runbook for
     cambridgeparser.com. Reviewed against first-party documentation on
     2026-09-09.
     ========================================================================= -->

# SEO deployment and console setup

This is an implementation and release checklist, not a promise of placement or
ranking. Google explicitly says that meeting its requirements, submitting a
sitemap, or requesting indexing does not guarantee crawling, indexing, or a
particular result appearance ([Search Essentials](https://developers.google.com/search/docs/essentials),
[recrawl guidance](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl)).

## Canonical and indexable surface

Use `https://www.cambridgeparser.com` as the one production origin. In Vercel,
assign both the apex and `www` domains to the project, make `www` primary, and
configure a permanent apex-to-`www` redirect. Vercel recommends `www` as the
primary host and documents the project-domain redirect; Google treats redirects
and `rel="canonical"` as stronger canonical signals than sitemap inclusion
([Vercel domain redirects](https://vercel.com/docs/domains/working-with-domains/deploying-and-redirecting),
[Google canonicalization](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)).

The intended crawl policy is:

| Route group | Index? | Sitemap? | Reason |
|---|---:|---:|---|
| `/` | Yes | Yes | Public product landing page |
| `/privacy`, `/terms`, `/data-deletion` | Yes | Yes | Public, stable policy pages that support provider trust |
| `/login`, `/reset-password` | No | No | Transactional/account screens with no useful search landing content |
| `/dashboard`, `/browser`, `/stats`, `/solver/**`, `/problems`, `/ide/**`, `/learn` | No | No | Authenticated application state, not independently crawlable public content |

Apply a self-referencing canonical to every indexable route. Canonical URLs,
internal links, Open Graph URLs, and sitemap entries must all use HTTPS, `www`,
and the same trailing-slash policy. Use `noindex, nofollow` on account recovery
and authenticated routes. Do not try to hide them only with `robots.txt`:
Google must be able to crawl a URL to read a page-level `noindex` directive, and
robots.txt is not an indexing-removal mechanism
([robots meta specification](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag),
[robots.txt introduction](https://developers.google.com/search/docs/crawling-indexing/robots/intro)).

Return a real HTTP `404` for unknown routes when the hosting architecture makes
that possible. The current SPA fallback sends `index.html` for every path, so
its client-side catch-all can otherwise look like a soft 404 to crawlers.

## Metadata and rendering

Each indexable page should have a distinct, concise `<title>`, one descriptive
meta description, a single clear visible `<h1>`, a canonical link, and matching
Open Graph metadata. Google uses titles, headings, prominent content,
`og:title`, link text, and other signals when creating title links; it may use a
meta description for the result snippet
([title-link guidance](https://developers.google.com/search/docs/appearance/title-link),
[supported meta tags](https://developers.google.com/search/docs/crawling-indexing/special-tags)).

For social previews, provide `og:title`, `og:type=website`, `og:image`, and
`og:url`; also provide `og:description`, `og:site_name`, and `og:image:alt`.
Those fields follow the published Open Graph protocol
([Open Graph protocol](https://ogp.me/)). The preview image should be an absolute
HTTPS URL, stable, publicly accessible, and large enough to remain legible when
cropped. Social preview metadata should describe the visible page, not add
search keywords that are absent from it.

This is a client-rendered Vue SPA. Google can process JavaScript-set titles and
descriptions, but says canonical information is clearest in the original HTML
and should not conflict with JavaScript. Social preview fetchers may not execute
the app at all. Treat build-time prerendering or SSR for the four public route
groups as the highest-value next architectural SEO improvement; until then,
keep the source-document fallback metadata accurate and update route metadata
consistently ([Google JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)).

Keep the favicon stable, square, crawlable, and visually representative. Google
supports common favicon formats, requires at least 8 by 8 pixels, and recommends
more than 48 by 48 pixels ([favicon guidance](https://developers.google.com/search/docs/appearance/favicon-in-search)).

## Discovery files

Serve `/robots.txt` as plain text:

```text
User-agent: *
Allow: /
Sitemap: https://www.cambridgeparser.com/sitemap.xml
```

Do not place access-control secrets or ineffective attempts to secure account
pages in this file; it is public. Serve a UTF-8 XML sitemap at the site root
using fully qualified canonical URLs. Include only pages intended for search,
and use `<lastmod>` only when it can be kept truthful. Google treats sitemap
submission as a discovery hint, recommends root placement, and limits each
sitemap to 50,000 URLs or 50 MB uncompressed
([Google sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)).

For the current public site, the sitemap should contain `/`, `/privacy`,
`/terms`, and `/data-deletion`. Add future content only when it is public,
substantive, linked from the site, canonical, and returns a successful response.

## Structured data

Place one JSON-LD graph on the homepage, ensuring every assertion matches
visible content:

- `WebSite`: `name: "CambridgeParser"`, an honest `alternateName` such as
  `"cambridgeparser.com"`, and canonical `url`. Google identifies this as the
  principal way to state a preferred site name
  ([site-name guidance](https://developers.google.com/search/docs/appearance/site-names)).
- `Organization`: only if CambridgeParser is genuinely operated as an
  organization. Include a stable `@id`, name, canonical URL, crawlable logo, and
  only verified `sameAs` profiles/contact details. Do not invent an address,
  legal name, or social account. Google recommends homepage-level Organization
  markup and truthful applicable properties
  ([Organization guidance](https://developers.google.com/search/docs/appearance/structured-data/organization)).
- `WebApplication`: suitable as a Schema.org description of this browser app,
  with truthful fields such as name, URL, description, browser requirements,
  `applicationCategory: "EducationalApplication"`, and `operatingSystem:
  "Any"` ([Schema.org WebApplication](https://schema.org/WebApplication)). A
  Google Software App rich result additionally requires `offers.price` and a
  genuine `aggregateRating` or `review`. Do not fabricate ratings or reviews
  merely to pass validation
  ([Google SoftwareApplication requirements](https://developers.google.com/search/docs/appearance/structured-data/software-app)).

Use `BreadcrumbList` only on public pages that expose a real breadcrumb trail
and meaningful hierarchy. The current shallow policy pages do not need it.
Google requires at least two breadcrumb list items and recommends representing
a normal user path rather than blindly mirroring the URL
([breadcrumb guidance](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb)).

Do not mark the authenticated solver corpus as Course, Q&A, Quiz, or Practice
Problem content. Those features require qualifying content to be present on a
public crawlable page and to satisfy feature-specific rules. If CambridgeParser
later publishes durable public lesson/problem pages, assess each page against
the relevant Google feature guidance rather than applying site-wide markup
([structured-data feature list](https://developers.google.com/search/docs/appearance),
[Education Q&A requirements](https://developers.google.com/search/docs/appearance/structured-data/education-qa)).

Validate general Schema.org syntax with the
[Schema Markup Validator](https://validator.schema.org/) and supported Google
features with the [Rich Results Test](https://search.google.com/test/rich-results).
Valid markup is only an eligibility signal and does not guarantee a rich result
([structured-data guidelines](https://developers.google.com/search/docs/appearance/structured-data/sd-policies)).

## Google Search Console release steps

1. Add a Domain property named `cambridgeparser.com`. Verify it with the exact
   DNS TXT record Search Console supplies. A Domain property includes protocols
   and all subdomains and can only be DNS-verified
   ([property types](https://support.google.com/webmasters/answer/34592),
   [ownership verification](https://support.google.com/webmasters/answer/9008080)).
2. Retain the DNS record permanently and give access to named accounts rather
   than sharing credentials. Use an owner account that can also support Google
   OAuth brand/domain verification.
3. Open **Sitemaps**, submit `https://www.cambridgeparser.com/sitemap.xml`, and
   resolve fetch or parsing errors. Also retain the sitemap directive in
   `robots.txt`.
4. In **URL Inspection**, test the live canonical homepage and each policy page.
   Confirm successful fetch, rendered content, indexability, structured data,
   and that the user-declared and Google-selected canonicals converge. Then use
   **Request indexing** once per materially changed URL. Repeated requests do
   not make crawling faster
   ([URL Inspection](https://support.google.com/webmasters/answer/9012289),
   [recrawl guidance](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl)).
5. Monitor **Page indexing**, **Sitemaps**, **Core Web Vitals**, **HTTPS**,
   **Manual actions**, **Security issues**, and the **Performance** report after
   deployment. New property data can take several days to appear.

Search Console has no setting that supplies page keywords or guarantees a site
name. The website itself remains the source of titles, content, links,
canonicals, and structured data.

## Page experience and performance

Monitor field data in Search Console and individual templates in PageSpeed
Insights. Google's “good” Core Web Vitals thresholds are LCP at or below 2.5
seconds, INP at or below 200 milliseconds, and CLS at or below 0.1. Optimize the
landing page independently from authenticated application bundles, reserve
image/layout dimensions, avoid render-blocking assets, and verify mobile
behavior ([Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals)).

Also keep HTTPS valid, avoid mixed content and intrusive interstitials, and
ensure the primary content remains usable on mobile. Google states there is no
single page-experience signal and that good metrics do not guarantee rankings
([page-experience guidance](https://developers.google.com/search/docs/appearance/page-experience)).

## Bing Webmaster Tools and IndexNow

After Search Console verification, create a Bing Webmaster Tools account and
import the verified property and sitemap from Google, or verify it manually.
Bing documents direct Search Console import and automatic verification
([Bing site verification](https://www2.bing.com/webmasters/help/add-and-verify-site-12184f8b)).
Inspect sitemap processing and crawl/index reports there as well
([Bing sitemaps](https://www.bing.com/webmasters/help/sitemaps-3b5cf6ed)).

IndexNow is optional for this small, mostly static public surface. It becomes
useful when public pages are frequently created, updated, or deleted. If added:

1. Generate an IndexNow key and host its verification text file on the same
   canonical host.
2. Submit only changed canonical public URLs from the deployment/content
   pipeline—not on every page view and not authenticated URLs.
3. Monitor submissions in Bing Webmaster Tools' IndexNow report.

Bing recommends IndexNow for automated change notification across participating
engines; a notification still does not guarantee indexing
([Bing URL submission](https://www.bing.com/webmasters/help/URL-Submission-62f2860b),
[IndexNow protocol](https://www.indexnow.org/documentation)).

## Ongoing content opportunities

Technical metadata cannot substitute for public useful content. The strongest
future search surface would be stable, internally linked, server-rendered pages
for syllabus topics, pseudocode concepts, worked examples, and original study
guides. Each should answer a distinct student need, expose meaningful text
without login, have its own title/description/canonical, and link naturally to
the relevant app workflow. Google recommends people-first content and says no
special files or schema are required for its AI search features
([people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content),
[AI features and websites](https://developers.google.com/search/docs/appearance/ai-features)).

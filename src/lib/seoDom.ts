// ===========================================================================
//
// Browser-only application of the universal metadata catalogue in seo.ts.
// Kept separate because Vite imports seo.ts in its Node build configuration,
// where DOM globals and types intentionally do not exist.
// ===========================================================================
import type { ResolvedSeoMetadata } from './seo';

function upsertMeta(attribute: 'name' | 'property', key: string, content: string): void {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`);
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute(attribute, key);
    document.head.append(element);
  }
  element.content = content;
}

export function applySeoMetadata(seo: ResolvedSeoMetadata): void {
  document.title = seo.title;
  document.documentElement.lang = 'en';

  upsertMeta('name', 'description', seo.description);
  upsertMeta('name', 'robots', seo.robots);
  upsertMeta('property', 'og:title', seo.title);
  upsertMeta('property', 'og:description', seo.description);
  upsertMeta('property', 'og:url', seo.canonicalUrl);
  upsertMeta('property', 'og:image', seo.imageUrl);
  upsertMeta('property', 'og:image:alt', seo.imageAlt);
  upsertMeta('name', 'twitter:title', seo.title);
  upsertMeta('name', 'twitter:description', seo.description);
  upsertMeta('name', 'twitter:image', seo.imageUrl);
  upsertMeta('name', 'twitter:image:alt', seo.imageAlt);

  let canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!canonical) {
    canonical = document.createElement('link');
    canonical.rel = 'canonical';
    document.head.append(canonical);
  }
  canonical.href = seo.canonicalUrl;

  const existingScript = document.getElementById('seo-structured-data');
  if (!seo.structuredData) {
    existingScript?.remove();
    return;
  }
  const script = existingScript ?? document.createElement('script');
  script.id = 'seo-structured-data';
  script.setAttribute('type', 'application/ld+json');
  script.textContent = JSON.stringify(seo.structuredData);
  if (!existingScript) document.head.append(script);
}

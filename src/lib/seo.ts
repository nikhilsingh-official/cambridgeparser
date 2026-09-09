// ============================================================================
//
// One metadata catalogue for runtime navigation and build-time crawler HTML.
// ============================================================================

export const SEO_ORIGIN = 'https://www.cambridgeparser.com';
export const SEO_IMAGE_URL = `${SEO_ORIGIN}/og-image.png`;

type SeoPageDefinition = {
  title: string;
  description: string;
  canonicalPath: string;
};

export const SEO_PAGES = {
  landing: {
    title: 'CambridgeParser | Past Papers & Pseudocode IDE',
    description: 'Practise Cambridge International past papers and pseudocode in one workspace, with automatic marking, study analytics, and progress tracking.',
    canonicalPath: '/',
  },
  login: {
    title: 'Sign In | CambridgeParser',
    description: 'Sign in to CambridgeParser to continue past-paper practice, pseudocode exercises, saved answers, and personal study progress.',
    canonicalPath: '/login',
  },
  resetPassword: {
    title: 'Reset Password | CambridgeParser',
    description: 'Securely reset the password for your CambridgeParser study account and return to your saved papers, pseudocode work, and progress.',
    canonicalPath: '/reset-password',
  },
  privacy: {
    title: 'Privacy Policy | CambridgeParser',
    description: 'Read how CambridgeParser collects, uses, protects, retains, and deletes account, OAuth, study, and AI-assisted grading information.',
    canonicalPath: '/privacy',
  },
  terms: {
    title: 'Terms and Conditions | CambridgeParser',
    description: 'Read the terms governing CambridgeParser accounts, educational tools, AI-assisted grading, acceptable use, and third-party services.',
    canonicalPath: '/terms',
  },
  dataDeletion: {
    title: 'Data Deletion | CambridgeParser',
    description: 'Learn how to request deletion of your CambridgeParser account, saved study history, pseudocode submissions, and browser-stored drafts.',
    canonicalPath: '/data-deletion',
  },
  dashboard: {
    title: 'Study Dashboard | CambridgeParser',
    description: 'Review your private CambridgeParser study dashboard, recent paper attempts, pseudocode activity, recommendations, and revision progress.',
    canonicalPath: '/dashboard',
  },
  browser: {
    title: 'Past Paper Browser | CambridgeParser',
    description: 'Browse supported Cambridge International multiple-choice papers by subject, session, year, variant, and personal completion status.',
    canonicalPath: '/browser',
  },
  stats: {
    title: 'Study Analytics | CambridgeParser',
    description: 'Explore private study analytics for accuracy, pacing, confidence, topic mastery, answer changes, and revision recommendations.',
    canonicalPath: '/stats',
  },
  solver: {
    title: 'Paper Solver | CambridgeParser',
    description: 'Complete a private timed Cambridge multiple-choice paper with PDF annotation, answer tracking, confidence, flags, and automatic marking.',
    canonicalPath: '/solver',
  },
  problems: {
    title: 'Pseudocode Problems | CambridgeParser',
    description: 'Browse private Cambridge 9618 pseudocode problems by topic and practise structured answers against question-specific marking criteria.',
    canonicalPath: '/problems',
  },
  ide: {
    title: 'Pseudocode IDE | CambridgeParser',
    description: 'Write and parse Cambridge-style pseudocode in a private browser workspace with diagnostics, question context, and rubric-based feedback.',
    canonicalPath: '/ide',
  },
  ideRecord: {
    title: 'Pseudocode Problem | CambridgeParser',
    description: 'Work through a selected Cambridge pseudocode problem in the private IDE with parser diagnostics, saved progress, and grading feedback.',
    canonicalPath: '/ide',
  },
  learn: {
    title: 'Learn Pseudocode | CambridgeParser',
    description: 'Study Cambridge-style pseudocode techniques and examples in a private learning workspace connected to practical problems and feedback.',
    canonicalPath: '/learn',
  },
} as const satisfies Record<string, SeoPageDefinition>;

export type SeoPageKey = keyof typeof SEO_PAGES;

export const INDEXABLE_SEO_PAGES: ReadonlySet<SeoPageKey> = new Set([
  'landing',
  'privacy',
  'terms',
  'dataDeletion',
]);

export const STATIC_SEO_ROUTES: ReadonlyArray<{
  page: SeoPageKey;
  routePath: string;
  outputFile: string;
}> = [
  { page: 'landing', routePath: '/', outputFile: 'index.html' },
  { page: 'login', routePath: '/login', outputFile: 'login.html' },
  { page: 'resetPassword', routePath: '/reset-password', outputFile: 'reset-password.html' },
  { page: 'privacy', routePath: '/privacy', outputFile: 'privacy.html' },
  { page: 'terms', routePath: '/terms', outputFile: 'terms.html' },
  { page: 'dataDeletion', routePath: '/data-deletion', outputFile: 'data-deletion.html' },
  { page: 'dashboard', routePath: '/dashboard', outputFile: 'dashboard.html' },
  { page: 'browser', routePath: '/browser', outputFile: 'browser.html' },
  { page: 'stats', routePath: '/stats', outputFile: 'stats.html' },
  { page: 'solver', routePath: '/solver', outputFile: 'solver.html' },
  { page: 'problems', routePath: '/problems', outputFile: 'problems.html' },
  { page: 'ide', routePath: '/ide', outputFile: 'ide.html' },
  { page: 'ideRecord', routePath: '/ide/problem', outputFile: 'ide-record.html' },
  { page: 'learn', routePath: '/learn', outputFile: 'learn.html' },
];

export type ResolvedSeoMetadata = {
  title: string;
  description: string;
  canonicalUrl: string;
  robots: string;
  imageUrl: string;
  imageAlt: string;
  structuredData: Record<string, unknown> | null;
};

function cleanRoutePath(path: string): string {
  const withoutQuery = path.split(/[?#]/, 1)[0] ?? '/';
  const normalized = `/${withoutQuery.replace(/^\/+/, '').replace(/\/+$/, '')}`;
  return normalized === '/' ? '/' : normalized;
}

function structuredDataFor(
  page: SeoPageKey,
  title: string,
  description: string,
  canonicalUrl: string,
): Record<string, unknown> | null {
  if (!INDEXABLE_SEO_PAGES.has(page)) return null;

  const websiteId = `${SEO_ORIGIN}/#website`;
  if (page === 'landing') {
    return {
      '@context': 'https://schema.org',
      '@graph': [
        {
          '@type': 'WebSite',
          '@id': websiteId,
          url: `${SEO_ORIGIN}/`,
          name: 'CambridgeParser',
          description,
          inLanguage: 'en',
          image: SEO_IMAGE_URL,
        },
        {
          '@type': 'WebApplication',
          '@id': `${SEO_ORIGIN}/#webapp`,
          name: 'CambridgeParser',
          url: `${SEO_ORIGIN}/`,
          description,
          applicationCategory: 'EducationalApplication',
          operatingSystem: 'Any',
          browserRequirements: 'Requires JavaScript and a modern web browser.',
          educationalUse: ['assessment', 'practice', 'self study'],
          audience: {
            '@type': 'EducationalAudience',
            educationalRole: 'student',
          },
          image: SEO_IMAGE_URL,
          isPartOf: { '@id': websiteId },
        },
      ],
    };
  }

  return {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: title,
    description,
    url: canonicalUrl,
    inLanguage: 'en',
    dateModified: '2026-09-09',
    isPartOf: {
      '@type': 'WebSite',
      '@id': websiteId,
      name: 'CambridgeParser',
      url: `${SEO_ORIGIN}/`,
    },
  };
}

export function resolveSeoMetadata(
  page: SeoPageKey,
  routePath: string,
  params: Record<string, unknown> = {},
): ResolvedSeoMetadata {
  const definition = SEO_PAGES[page];
  const isIndexable = INDEXABLE_SEO_PAGES.has(page);
  const path = isIndexable ? definition.canonicalPath : cleanRoutePath(routePath || definition.canonicalPath);
  const canonicalUrl = new URL(path.replace(/^\/+/, ''), `${SEO_ORIGIN}/`).href;
  let title: string = definition.title;

  if (page === 'solver' && typeof params.schema === 'string' && params.schema) {
    title = `${params.schema.replace(/_/g, ' ').toUpperCase()} Paper | CambridgeParser`;
  } else if (page === 'ideRecord' && typeof params.id === 'string' && params.id) {
    title = `Pseudocode Problem ${params.id} | CambridgeParser`;
  }

  return {
    title,
    description: definition.description,
    canonicalUrl,
    robots: isIndexable
      ? 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
      : 'noindex, nofollow, noarchive',
    imageUrl: SEO_IMAGE_URL,
    imageAlt: 'CambridgeParser document and structured-data logo beside the product name.',
    structuredData: structuredDataFor(page, title, definition.description, canonicalUrl),
  };
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function replaceAttributeTag(
  html: string,
  attribute: 'name' | 'property' | 'rel',
  key: string,
  valueAttribute: 'content' | 'href',
  value: string,
): string {
  const pattern = new RegExp(
    `(<(?:meta|link)\\s+${attribute}="${key}"\\s+${valueAttribute}=")[^"]*("\\s*\\/?>)`,
    'i',
  );
  return html.replace(pattern, `$1${escapeHtml(value)}$2`);
}

export function renderSeoDocument(html: string, seo: ResolvedSeoMetadata): string {
  let rendered = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtml(seo.title)}</title>`);
  rendered = replaceAttributeTag(rendered, 'name', 'description', 'content', seo.description);
  rendered = replaceAttributeTag(rendered, 'name', 'robots', 'content', seo.robots);
  rendered = replaceAttributeTag(rendered, 'rel', 'canonical', 'href', seo.canonicalUrl);
  rendered = replaceAttributeTag(rendered, 'property', 'og:title', 'content', seo.title);
  rendered = replaceAttributeTag(rendered, 'property', 'og:description', 'content', seo.description);
  rendered = replaceAttributeTag(rendered, 'property', 'og:url', 'content', seo.canonicalUrl);
  rendered = replaceAttributeTag(rendered, 'property', 'og:image', 'content', seo.imageUrl);
  rendered = replaceAttributeTag(rendered, 'property', 'og:image:alt', 'content', seo.imageAlt);
  rendered = replaceAttributeTag(rendered, 'name', 'twitter:title', 'content', seo.title);
  rendered = replaceAttributeTag(rendered, 'name', 'twitter:description', 'content', seo.description);
  rendered = replaceAttributeTag(rendered, 'name', 'twitter:image', 'content', seo.imageUrl);
  rendered = replaceAttributeTag(rendered, 'name', 'twitter:image:alt', 'content', seo.imageAlt);

  const scriptPattern = /\s*<script id="seo-structured-data" type="application\/ld\+json">[\s\S]*?<\/script>/i;
  if (!seo.structuredData) return rendered.replace(scriptPattern, '');
  const json = JSON.stringify(seo.structuredData).replace(/</g, '\\u003c');
  return rendered.replace(
    scriptPattern,
    `\n    <script id="seo-structured-data" type="application/ld+json">${json}</script>`,
  );
}

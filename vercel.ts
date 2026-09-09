// ============================================================================
//
// Vercel delivery, security, crawler, and route-specific metadata rules.
// ============================================================================

const noIndex = [
  '/login',
  '/reset-password',
  '/dashboard',
  '/browser',
  '/stats',
  '/solver/(.*)',
  '/problems',
  '/ide',
  '/ide/(.*)',
  '/learn',
];

const metadataDocuments = [
  ['/login', '/login.html'],
  ['/reset-password', '/reset-password.html'],
  ['/privacy', '/privacy.html'],
  ['/terms', '/terms.html'],
  ['/data-deletion', '/data-deletion.html'],
  ['/dashboard', '/dashboard.html'],
  ['/browser', '/browser.html'],
  ['/stats', '/stats.html'],
  ['/solver/(.*)', '/solver.html'],
  ['/problems', '/problems.html'],
  ['/ide', '/ide.html'],
  ['/ide/(.*)', '/ide-record.html'],
  ['/learn', '/learn.html'],
];

export const config = {
  framework: 'vite',
  buildCommand: 'npm run build',
  outputDirectory: 'dist',
  headers: [
    {
      source: '/(.*)',
      headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
      ],
    },
    {
      source: '/assets/(.*)',
      headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
    },
    ...noIndex.map(source => ({
      source,
      headers: [{ key: 'X-Robots-Tag', value: 'noindex, nofollow, noarchive' }],
    })),
    ...['/robots.txt', '/sitemap.xml'].map(source => ({
      source,
      headers: [{ key: 'Cache-Control', value: 'public, max-age=0, s-maxage=3600' }],
    })),
  ],
  rewrites: [
    ...metadataDocuments.map(([source, destination]) => ({ source, destination })),
    { source: '/(.*)', destination: '/index.html' },
  ],
};

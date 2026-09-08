// ==========================================================================
//
// Theme selection, persisted. Mirrors the Cambridge IDE's services/theme.js
// so the two apps behave identically, but generalised from a light/dark
// boolean to a named list - SmartSolver ships three themes, not two.
// ==========================================================================
import { computed, ref } from 'vue';

/** the erasable const-object pattern - tsconfig sets erasableSyntaxOnly, which forbids `enum`. */
export const Theme = {
  /** The original teal-on-near-black aesthetic. Default. */
  SoluerDark: 'soluer-dark',
  /** Cambridge IDE light: warm paper, oxblood ink, square geometry. */
  ExamPaper: 'exam-paper',
  /** Cambridge IDE dark: amber on slate, square geometry. */
  CambridgeDark: 'cambridge-dark',
} as const;
export type Theme = typeof Theme[keyof typeof Theme];

export const ALL_THEMES = Object.values(Theme) as Theme[];

/** shown in the switcher. Kept beside the enum so adding a theme is one edit. */
export const THEME_LABEL: Record<Theme, string> = {
  [Theme.SoluerDark]: 'Teal Dark',
  [Theme.ExamPaper]: 'Exam Paper',
  [Theme.CambridgeDark]: 'Cambridge Dark',
};

/** drives <meta name="theme-color">, which colours mobile browser chrome. */
const THEME_COLOUR: Record<Theme, string> = {
  [Theme.SoluerDark]: '#171717',
  [Theme.ExamPaper]: '#faf8f3',
  [Theme.CambridgeDark]: '#0e1116',
};

export const DEFAULT_THEME: Theme = Theme.SoluerDark;

// read from the <html data-theme-storage> attribute, matching the IDE's
// convention, so the key lives in one place (index.html) for both the
// pre-paint bootstrap and this module. They MUST agree or the bootstrap picks
// one theme and the app then switches to another - a visible flash.
function storageKey(): string {
  return document.documentElement.dataset.themeStorage ?? 'smartsolver-theme';
}

export function isTheme(value: unknown): value is Theme {
  return typeof value === 'string' && (ALL_THEMES as string[]).includes(value);
}

export const currentTheme = ref<Theme>(DEFAULT_THEME);
export const isLightTheme = computed(() => currentTheme.value === Theme.ExamPaper);

function readSaved(): Theme | null {
  try {
    const raw = window.localStorage.getItem(storageKey());
    return isTheme(raw) ? raw : null;
  } catch {
    // localStorage throws in private mode / when cookies are blocked.
    // A theme preference is not worth breaking the app over.
    return null;
  }
}

export function setTheme(theme: Theme, { persist = true } = {}): void {
  const next = isTheme(theme) ? theme : DEFAULT_THEME;
  currentTheme.value = next;
  document.documentElement.dataset.theme = next;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', THEME_COLOUR[next]);

  if (!persist) return;
  try {
    window.localStorage.setItem(storageKey(), next);
  } catch {
    // The chosen theme still applies for this session.
  }
}

/**
 * adopts whatever index.html already stamped, rather than re-deciding.
 *
 * The inline script in index.html runs before CSS paints so there is no
 * wrong-theme flash. If this function re-derived the theme it could disagree
 * with that decision and cause the exact flash the bootstrap exists to avoid -
 * so the stamped value wins, and this only falls back when it is missing
 * (tests, or a different entry point).
 */
export function initializeTheme(): void {
  const stamped = document.documentElement.dataset.theme;
  const theme = isTheme(stamped) ? stamped : (readSaved() ?? DEFAULT_THEME);
  setTheme(theme, { persist: false });
}

/** cycles in list order - the switcher is a single button, not a menu. */
export function cycleTheme(): void {
  const index = ALL_THEMES.indexOf(currentTheme.value);
  setTheme(ALL_THEMES[(index + 1) % ALL_THEMES.length]!);
}

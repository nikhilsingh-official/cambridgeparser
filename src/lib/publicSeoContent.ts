export type PublicContentSection = {
  heading: string;
  paragraphs: readonly string[];
  points?: readonly string[];
};

export type PublicContentPage = {
  eyebrow: string;
  heading: string;
  summary: string;
  highlights: readonly string[];
  sections: readonly PublicContentSection[];
  primaryAction: { href: string; label: string };
  secondaryAction?: { href: string; label: string };
};

export const PUBLIC_PRODUCT_CONTENT = {
  landing: {
    eyebrow: 'Cambridge revision in one workspace',
    heading: 'Cambridge past paper solver and pseudocode IDE',
    summary: 'Practise Cambridge International past papers in their original layout, write syllabus-style pseudocode, and use saved attempts to decide what to revise next.',
    highlights: ['Original paper context', 'Automatic marking', 'Pseudocode feedback', 'Progress analytics'],
    sections: [
      {
        heading: 'Solve Cambridge past papers without losing the paper',
        paragraphs: ['Work directly with the original PDF while using a timer, question navigation, option elimination, confidence flags, and a locked review after submission.'],
        points: ['IGCSE, O Level, AS and A Level multiple-choice papers', 'Question-level review and saved attempts', 'Subject and paper-specific progress'],
      },
      {
        heading: 'Practise Cambridge pseudocode against real marking criteria',
        paragraphs: ['Search a curated corpus covering IGCSE 0478 and AS/A Level 9608 and 9618 Paper 2 questions, then write or complete answers in the browser-based IDE.'],
        points: ['381 canonical exam questions', 'Local parser diagnostics', 'Rubric-grounded grading feedback'],
      },
      {
        heading: 'Turn attempts into a focused revision plan',
        paragraphs: ['CambridgeParser connects marks with timing, confidence, answer changes, and topic history so recommendations reflect how an answer happened, not only whether it was correct.'],
      },
    ],
    primaryAction: { href: '/login', label: 'Start practising' },
    secondaryAction: { href: '/cambridge-past-paper-solver', label: 'Explore the past paper solver' },
  },
  pastPaperSolver: {
    eyebrow: 'Original-paper practice',
    heading: 'Cambridge past paper solver',
    summary: 'Solve supported Cambridge International multiple-choice papers with the original PDF, timed navigation, automatic marking, saved review, and progress tracking.',
    highlights: ['Original PDFs', 'Timed attempts', 'Automatic marking', 'Saved review'],
    sections: [
      {
        heading: 'A solver built around the real exam paper',
        paragraphs: ['The PDF stays visible while CambridgeParser adds controls around it. You can move between detected questions, choose or eliminate options, flag uncertainty, and keep the page context that diagrams and tables provide.'],
      },
      {
        heading: 'Review more than the final percentage',
        paragraphs: ['After submission, answers are locked for an honest review. The result connects each question with the answer key, time spent, confidence, changes, and flags.'],
        points: ['Question-by-question answer review', 'Published paper boundaries where available', 'Attempt history and topic signals'],
      },
      {
        heading: 'Choose a supported Cambridge paper',
        paragraphs: ['The authenticated paper browser filters supported IGCSE, O Level, AS and A Level multiple-choice papers by subject, year, series, component, and completion status.'],
      },
    ],
    primaryAction: { href: '/browser', label: 'Open the paper browser' },
    secondaryAction: { href: '/cambridge-pseudocode-ide', label: 'Explore the pseudocode IDE' },
  },
  pseudocodeIde: {
    eyebrow: 'Browser-based programming practice',
    heading: 'Cambridge pseudocode IDE',
    summary: 'Write Cambridge-style pseudocode beside real exam questions, catch supported syntax problems locally, and get feedback grounded in each mark scheme.',
    highlights: ['No installation', 'Syntax diagnostics', 'Real questions', 'Rubric feedback'],
    sections: [
      {
        heading: 'Keep the question beside the code',
        paragraphs: ['Open a question from the searchable corpus and retain its diagrams, tables, wording, marks, and parent-question context while you work.'],
      },
      {
        heading: 'Use the right answer mode for the task',
        paragraphs: ['CambridgeParser supports free-form pseudocode responses and structured completion tasks. The local WebAssembly parser identifies supported syntax issues before grading.'],
        points: ['Editable full answers and detected blanks', 'Formatting and browser-local draft persistence', 'Question-specific marking points after submission'],
      },
      {
        heading: 'One corpus across IGCSE and AS/A Level',
        paragraphs: ['The current collection contains 381 canonical questions from Cambridge 0478, 9608, and 9618 papers, tagged by the relevant syllabus topics.'],
      },
    ],
    primaryAction: { href: '/problems', label: 'Browse pseudocode problems' },
    secondaryAction: { href: '/igcse-computer-science-pseudocode', label: 'See IGCSE coverage' },
  },
  igcsePseudocode: {
    eyebrow: 'Cambridge IGCSE Computer Science',
    heading: 'IGCSE Computer Science pseudocode practice',
    summary: 'Prepare for Cambridge IGCSE Computer Science 0478 Paper 2 with searchable algorithm and programming questions from the 2016–2025 archive.',
    highlights: ['205 canonical questions', '69 source papers audited', 'Topics 7 and 8', '2016–2025'],
    sections: [
      {
        heading: 'Coverage built for 0478 Paper 2',
        paragraphs: ['The corpus contains 205 unique questions selected from all 69 valid 0478 Paper 2 source papers in the local 2016–2025 archive. Ten verbatim repeats are merged while their source-paper provenance is retained.'],
      },
      {
        heading: 'Practise the forms questions actually take',
        paragraphs: ['Tasks include writing and completing algorithms, tracing and correcting pseudocode, validation, arrays, loops, selection, string handling, and file processing.'],
        points: ['Every question has syllabus tags', 'Every trusted grading record has answer text', 'Every retained record has structured marking points'],
      },
      {
        heading: 'Work in an exam-focused editor',
        paragraphs: ['Move from topic filtering into the pseudocode IDE without separating the question, its marks, and its original paper context from your answer.'],
      },
    ],
    primaryAction: { href: '/problems', label: 'Practise IGCSE pseudocode' },
    secondaryAction: { href: '/a-level-computer-science-pseudocode', label: 'See AS/A Level coverage' },
  },
  aLevelPseudocode: {
    eyebrow: 'Cambridge International AS & A Level Computer Science',
    heading: 'A Level Computer Science pseudocode practice',
    summary: 'Practise Cambridge 9608 and 9618 Paper 2 pseudocode questions with searchable topic tags, original question context, parser diagnostics, and rubric-based feedback.',
    highlights: ['176 canonical questions', '9608 and 9618', 'Paper 2 focus', '2016–2025'],
    sections: [
      {
        heading: 'Focused coverage of Paper 2 programming',
        paragraphs: ['The current AS/A Level collection contains 176 canonical questions from legacy 9608 and current 9618 Paper 2 papers. It supports AS content used within the full A Level but does not claim coverage of the A-Level-only Papers 3 and 4.'],
      },
      {
        heading: 'Search by the technique you need to practise',
        paragraphs: ['Topic tags cover algorithm design, selection, iteration, arrays, records, procedures, functions, validation, searching, sorting, file handling, and related programming concepts.'],
      },
      {
        heading: 'Review against question-specific evidence',
        paragraphs: ['Trusted examiner answer text and structured marking points stay on the server until an answer is submitted, while the public browser receives only question and mark metadata.'],
        points: ['Original question and context images', 'Marks capped to the paper rubric', 'Saved IDE attempt history'],
      },
    ],
    primaryAction: { href: '/problems', label: 'Practise AS/A Level pseudocode' },
    secondaryAction: { href: '/cambridge-pseudocode-ide', label: 'Explore the IDE' },
  },
} as const satisfies Record<string, PublicContentPage>;

export type PublicContentPageKey = keyof typeof PUBLIC_PRODUCT_CONTENT;

export const PUBLIC_PRODUCT_LINKS: ReadonlyArray<{ href: string; label: string }> = [
  { href: '/cambridge-past-paper-solver', label: 'Past paper solver' },
  { href: '/cambridge-pseudocode-ide', label: 'Pseudocode IDE' },
  { href: '/igcse-computer-science-pseudocode', label: 'IGCSE pseudocode' },
  { href: '/a-level-computer-science-pseudocode', label: 'AS & A Level pseudocode' },
];

function escapeText(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderLink(link: { href: string; label: string }, className = ''): string {
  const classAttribute = className ? ` class="${className}"` : '';
  return `<a${classAttribute} href="${escapeText(link.href)}">${escapeText(link.label)}</a>`;
}

export function renderPublicContent(page: PublicContentPageKey): string {
  const content: PublicContentPage = PUBLIC_PRODUCT_CONTENT[page];
  const navigation = PUBLIC_PRODUCT_LINKS
    .map(link => renderLink(link))
    .join('');
  const highlights = content.highlights
    .map(highlight => `<li>${escapeText(highlight)}</li>`)
    .join('');
  const sections = content.sections.map(section => {
    const paragraphs = section.paragraphs
      .map(paragraph => `<p>${escapeText(paragraph)}</p>`)
      .join('');
    const points = section.points
      ? `<ul>${section.points.map(point => `<li>${escapeText(point)}</li>`).join('')}</ul>`
      : '';
    return `<section><h2>${escapeText(section.heading)}</h2>${paragraphs}${points}</section>`;
  }).join('');
  const secondaryAction = content.secondaryAction
    ? renderLink(content.secondaryAction, 'secondary-action')
    : '';

  return `<main class="seo-prerender" data-seo-page="${page}">
    <nav aria-label="Product navigation">
      <a class="brand" href="/">CambridgeParser</a>
      ${navigation}
      <a href="/login">Sign in</a>
    </nav>
    <article>
      <header>
        <p class="eyebrow">${escapeText(content.eyebrow)}</p>
        <h1>${escapeText(content.heading)}</h1>
        <p class="summary">${escapeText(content.summary)}</p>
        <div class="actions">${renderLink(content.primaryAction, 'primary-action')}${secondaryAction}</div>
        <ul class="highlights">${highlights}</ul>
      </header>
      <div class="content-sections">${sections}</div>
    </article>
    <footer>
      <a href="/">CambridgeParser</a>
      <span>Independent study software. Not affiliated with or endorsed by Cambridge International Education.</span>
      <a href="/privacy">Privacy</a>
      <a href="/terms">Terms</a>
    </footer>
  </main>`;
}

// ==========================================================================
//
// Turns the two scraped files at the repo root into the topic migration:
//
//   structure.json       canonical syllabus topics, per subject, with ids
//   question_topics.json one label per exam question, free text
//
// and writes supabase/seeds/03_topics.sql.
//
// WHY A BUILD STEP AND NOT HAND-WRITTEN SQL
// question_topics.json holds ~125k labels that were Title-Cased out of
// structure.json by the scraper, so they carry its typos and spacing quirks
// ('P4..', 'THE BEHAVIOR OF METALS ', doubled spaces) plus HTML entities. They
// also concatenate multiple topics with ', ' - while several canonical topic
// NAMES contain a comma of their own ('Acids, bases and salts', 'Waves,
// including light and sound'). Splitting on the comma is therefore wrong. The
// only reliable reading is to match whole canonical names, longest first, and
// treat whatever is left over as an error rather than a guess. Rerun with:
//
//   npm run topics:build
// ==========================================================================

import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/**
 * Subject codes to emit question rows for: the multiple-choice syllabuses in
 * paperCatalogue.ts. The taxonomy itself is emitted in full for every subject
 * in structure.json, so widening the catalogue later is a data-only
 * regeneration - add the code and its paper numbers here and rerun.
 */
const CATALOGUE_PAPERS = new Set([
  '0610/1', '0610/2', '0620/1', '0620/2', '0625/1', '0625/2', '0653/1', '0653/2',
  '0654/1', '0654/2', '0455/1', '9700/1', '9701/1', '9702/1', '9708/1',
  '5090/1', '5070/1', '5054/1', '2281/1',
]);

const SERIES: Record<string, string> = { Spring: 'm', Summer: 's', Winter: 'w' };

// --------------------------------------------------------------------------
// 1. The cleaning pass.
//    Runs over canonical names and over labels identically - that is the whole
//    point of it, and what makes the two sides normalise onto each other.
// --------------------------------------------------------------------------

const ENTITIES: Record<string, string> = {
  '&amp;': '&', '&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'",
};
const QUOTES: Record<string, string> = { '‘': "'", '’': "'", '“': '"', '”': '"' };

/** Display form: fix the encoding damage, keep the wording. */
function clean(raw: string): string {
  return raw
    .replace(/&(amp|nbsp|lt|gt|quot|#39);/g, (m) => ENTITIES[m])
    .normalize('NFKC')
    .replace(/[‐-―−]/g, '-')
    .replace(/[‘’“”]/g, (c) => QUOTES[c])
    .replace(/[\s ]+/g, ' ')
    .trim();
}

/**
 * Match form. Punctuation is discarded except the comma, which has to survive
 * because it appears inside canonical names. '&' and 'and' are used
 * interchangeably by the scraper ('FORCES, DENSITY & PRESSURE' against the
 * label 'Forces, Density And Pressure'), so both collapse to 'and'.
 */
function matchKey(raw: string): string {
  return clean(raw)
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/\(excluded\)/g, '')
    .replace(/[^a-z0-9,]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Half the subjects are scraped in ALL CAPS and half in sentence case. */
function displayName(raw: string): string {
  const c = clean(raw).replace(/\.\.+/g, '.');
  return (/[a-z]/.test(c) ? c : c.toLowerCase()).replace(/^./, (m) => m.toUpperCase());
}

// --------------------------------------------------------------------------
// 2. The canonical vocabulary, per subject.
// --------------------------------------------------------------------------

interface Canon {
  id: string;
  key: string;
}

interface TopicRow {
  subjectCode: string;
  code: string;
  name: string;
  sortOrder: number;
}

type Structure = Record<string, Record<string, { name: string; id: string }[]>>;

/** 'B1. Cells', 'P4.. Properties of waves', 'P1 - Motion' -> the bare name. */
const UNIT_PREFIX = /^[bcp]\s?\d{1,2}\b\.*\s*/;

function buildCanon(structure: Structure): { canon: Map<string, Canon[]>; topics: TopicRow[] } {
  const canon = new Map<string, Canon[]>();
  const topics: TopicRow[] = [];
  const seenTopic = new Set<string>();

  for (const subjects of Object.values(structure)) {
    for (const [subjectKey, list] of Object.entries(subjects)) {
      const m = /^(.*)\((\d{4})\)-(\d+)$/.exec(subjectKey);
      if (!m) throw new Error(`unparseable subject key in structure.json: ${subjectKey}`);
      const code = m[2];

      const entries = canon.get(code) ?? [];
      list.forEach((t, i) => {
        // 9709 is split across nine structure.json entries (Pure 1, Mechanics,
        // ...). They share a subject code, so their topics merge into one
        // vocabulary - which is what we want; the ids are unique file-wide.
        if (!seenTopic.has(`${code}/${t.id}`)) {
          seenTopic.add(`${code}/${t.id}`);
          topics.push({ subjectCode: code, code: t.id, name: displayName(t.name), sortOrder: i });
        }
        entries.push({ id: t.id, key: matchKey(t.name) });
      });
      canon.set(code, entries);
    }
  }

  for (const [code, entries] of canon) {
    const seen = new Set<string>();
    const primary: Canon[] = [];
    // Longest key first, so 'Waves, including light and sound' is consumed
    // before the bare 'Waves' can claim its first word.
    for (const e of [...entries].sort((a, b) => b.key.length - a.key.length)) {
      if (e.key && !seen.has(e.key)) {
        seen.add(e.key);
        primary.push(e);
      }
    }
    // Aliases for the unit-prefixed subjects, where some labels drop the 'B1.'.
    // These sort below their prefixed form, so they only fire when it is absent.
    const aliases: Canon[] = [];
    for (const e of primary) {
      const bare = e.key.replace(UNIT_PREFIX, '').trim();
      if (bare && !seen.has(bare)) {
        seen.add(bare);
        aliases.push({ id: e.id, key: bare });
      }
    }
    canon.set(code, [...primary, ...aliases].sort((a, b) => b.key.length - a.key.length));
  }

  return { canon, topics };
}

// --------------------------------------------------------------------------
// 3. Segmentation.
// --------------------------------------------------------------------------

/** matchKey() emits only [a-z0-9, ], so a pipe cannot collide with real text. */
const CONSUMED = '|';

/**
 * Consume the label with canonical names, longest first. Whatever survives the
 * matches and the separators is `residue`; a non-empty residue means the label
 * said something the canon does not contain, and gets reported rather than
 * silently dropped.
 */
function segment(canon: Canon[], label: string): { ids: string[]; residue: string } {
  let rest = matchKey(label);
  if (!rest) return { ids: [], residue: '' };

  const hits: { at: number; id: string }[] = [];
  for (const { id, key } of canon) {
    // The boundaries stop 'Waves' matching inside 'Microwaves'.
    const re = new RegExp(`(?<![a-z0-9])${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![a-z0-9])`);
    for (let m = re.exec(rest); m; m = re.exec(rest)) {
      hits.push({ at: m.index, id });
      rest = rest.slice(0, m.index) + CONSUMED + rest.slice(m.index + m[0].length);
    }
  }
  hits.sort((a, b) => a.at - b.at);
  return {
    ids: [...new Set(hits.map((h) => h.id))],
    residue: rest.replace(/[|,\s]+/g, ''),
  };
}

// --------------------------------------------------------------------------
// 4. Drive it.
// --------------------------------------------------------------------------

interface Link {
  paperId: string;
  question: number;
  subjectCode: string;
  topicCode: string;
}

const LABEL_KEY = /^(\d{4})\/(\d)(\d)_([A-Za-z]+)_(\d{4})_Q(\d+)$/;

function main(): void {
  const structure: Structure = JSON.parse(readFileSync(resolve(ROOT, 'structure.json'), 'utf8'));
  const labels: Record<string, string> = JSON.parse(
    readFileSync(resolve(ROOT, 'question_topics.json'), 'utf8'),
  );
  const { canon, topics } = buildCanon(structure);

  const links: Link[] = [];
  const residues = new Map<string, number>();
  let malformed = 0;
  let blank = 0;
  let considered = 0;
  let multi = 0;

  for (const [key, rawLabel] of Object.entries(labels)) {
    const m = LABEL_KEY.exec(key);
    if (!m) {
      malformed++;
      continue;
    }
    const [, code, paperNo, variant, season, year, question] = m;
    if (!CATALOGUE_PAPERS.has(`${code}/${paperNo}`)) continue;
    const series = SERIES[season];
    if (!series) continue;

    considered++;
    if (!clean(rawLabel)) {
      blank++;
      continue;
    }

    const { ids, residue } = segment(canon.get(code) ?? [], rawLabel);
    if (residue) {
      const k = `${code}  ${clean(rawLabel)}`;
      residues.set(k, (residues.get(k) ?? 0) + 1);
      continue; // never guess; leave the question untagged
    }
    if (ids.length > 1) multi++;

    const yy = String(Number(year) % 100).padStart(2, '0');
    const paperId = `${code}_${series}${yy}_${paperNo}${variant}`;
    for (const id of ids) {
      links.push({ paperId, question: Number(question), subjectCode: code, topicCode: id });
    }
  }

  const out = resolve(ROOT, 'supabase/seeds/03_topics.sql');
  writeFileSync(out, renderSql(topics, links));

  const papers = new Set(links.map((l) => l.paperId));
  const unmatched = [...residues.values()].reduce((a, b) => a + b, 0);
  console.log(`taxonomy   : ${topics.length} topics across ${new Set(topics.map((t) => t.subjectCode)).size} subjects`);
  console.log(`labels     : ${considered} on catalogue papers, ${blank} blank, ${malformed} malformed keys (all subjects)`);
  console.log(`segmented  : ${links.length} links over ${papers.size} papers, ${multi} questions carrying >1 topic`);
  console.log(`unmatched  : ${unmatched} questions, ${residues.size} distinct labels`);
  for (const [k, n] of [...residues].sort((a, b) => b[1] - a[1]).slice(0, 10)) {
    console.log(`             ${n}x  ${k}`);
  }
  console.log(`wrote      : ${out}`);
}

const q = (s: string): string => `'${s.replace(/'/g, "''")}'`;

function renderSql(topics: TopicRow[], links: Link[]): string {
  const head = `-- ==========================================================================
--
-- GENERATED by scripts/buildTopics.ts from structure.json and
-- question_topics.json. Do not hand-edit; rerun \`npm run topics:build\`.
--
-- It lives in seeds/ rather than migrations/ because topics.subject_code is a
-- foreign key to subjects, and subjects is itself seeded (01_subjects.sql) -
-- a data migration would run BEFORE the seeds and find no subjects to hang
-- these off. See the note at the top of 00000000000004_question_topics.sql.
--
-- ${topics.length} topics, ${links.length} question -> topic links.
-- ==========================================================================

`;

  const topicValues = topics
    .map((t) => `  (${q(t.subjectCode)}, ${q(t.code)}, ${q(t.name)}, ${t.sortOrder})`)
    .join(',\n');

  // structure.json covers subjects that seeds/01_subjects.sql does not, and
  // topics.subject_code is a foreign key. Filter rather than let the migration
  // fail: the taxonomy being wider than the syllabus list is not an error.
  const topicSql = `insert into topics (subject_code, code, name, sort_order)
select v.subject_code, v.code, v.name, v.sort_order
from (values
${topicValues}
) as v(subject_code, code, name, sort_order)
where exists (select 1 from subjects s where s.code = v.subject_code)
on conflict (subject_code, code) do update
  set name = excluded.name, sort_order = excluded.sort_order;

`;

  const linkValues = links
    .map((l) => `  (${q(l.paperId)}, ${l.question}, ${q(l.subjectCode)}, ${q(l.topicCode)})`)
    .join(',\n');

  const linkSql = `insert into question_topics (paper_id, question_number, topic_id)
select v.paper_id, v.question_number, t.id
from (values
${linkValues}
) as v(paper_id, question_number, subject_code, topic_code)
join topics t on t.subject_code = v.subject_code and t.code = v.topic_code
on conflict do nothing;
`;

  return head + topicSql + linkSql;
}

main();

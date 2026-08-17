// ==========================================================================
//
// FILL-IN-THE-BLANK: syllabus topic taxonomy, per subject.
//
// This is the infrastructure for per-topic mastery ("you are at 45% on
// electromagnetism"). The plumbing is done - `topics` and
// `paper_answers.topic_id` exist in schema.sql, and v_topic_mastery reads
// them. What is missing is the content, which is yours to add.
//
// TWO THINGS TO FILL IN
//
//   1. SUBJECT_TOPICS - the topic list for each subject code. Add an entry
//      keyed by Cambridge subject code. `code` is yours to choose but must be
//      stable and unique within the subject (a syllabus reference like '4.1'
//      is the obvious choice). `parent` is optional and gives you a two-level
//      taxonomy.
//
//   2. PAPER_QUESTION_TOPICS - which topic each question of a given paper
//      belongs to. Keyed by the paper schema string, then question number.
//      This is the tedious part; it can also be populated straight into
//      `paper_answers.topic_id` in SQL if you would rather do it there.
//
// Two worked examples are included below so the shape is unambiguous. They are
// illustrative placeholders, NOT authoritative syllabus data - replace them.
//
// Nothing here is imported by the running app yet; `seedTopics()` at the
// bottom is the loader to call once you have filled it in.
// ==========================================================================

export interface Topic {
  code: string;        // stable within the subject, e.g. '4.1'
  name: string;        // 'Electromagnetic induction'
  parent?: string;     // optional parent topic `code`
  sortOrder?: number;
}

// --------------------------------------------------------------------------
// 1. Topic taxonomy per subject code.
//    Key = Cambridge subject code (see subjectCodes.ts).
// --------------------------------------------------------------------------
export const SUBJECT_TOPICS: Record<string, Topic[]> = {
  // ---- EXAMPLE ONLY - replace with the real 0625 syllabus breakdown -------
  '0625': [
    { code: '1', name: 'Motion, forces and energy', sortOrder: 1 },
    { code: '1.1', name: 'Physical quantities and measurement', parent: '1', sortOrder: 2 },
    { code: '1.2', name: 'Motion', parent: '1', sortOrder: 3 },
    { code: '2', name: 'Thermal physics', sortOrder: 4 },
    { code: '3', name: 'Waves', sortOrder: 5 },
    { code: '4', name: 'Electricity and magnetism', sortOrder: 6 },
    { code: '4.5', name: 'Electromagnetic induction', parent: '4', sortOrder: 7 },
    { code: '5', name: 'Nuclear physics', sortOrder: 8 },
    { code: '6', name: 'Space physics', sortOrder: 9 },
  ],

  // ---- EXAMPLE ONLY - replace with the real 9618 syllabus breakdown -------
  '9618': [
    { code: '1',  name: 'Information representation', sortOrder: 1 },
    { code: '2',  name: 'Communication', sortOrder: 2 },
    { code: '3',  name: 'Hardware', sortOrder: 3 },
    { code: '4',  name: 'Processor fundamentals', sortOrder: 4 },
    { code: '9',  name: 'Data representation', sortOrder: 5 },
    { code: '11', name: 'Algorithms and data structures', sortOrder: 6 },
  ],

  // '0620': [ ... ],
  // '0610': [ ... ],
  // '9702': [ ... ],
};

// --------------------------------------------------------------------------
// 2. Question -> topic mapping, per paper.
//    Key = paper schema string ('0625_s25_22'), value = { questionNumber: topicCode }.
//    Topic codes must exist in SUBJECT_TOPICS for that paper's subject.
// --------------------------------------------------------------------------
export const PAPER_QUESTION_TOPICS: Record<string, Record<number, string>> = {
  // ---- EXAMPLE ONLY -------------------------------------------------------
  // '0625_s25_22': { 1: '1.1', 2: '1.2', 3: '1.2', 4: '2', 5: '4.5' },
};

// --------------------------------------------------------------------------
// Loaders. Run once after filling the maps in; both are idempotent.
// --------------------------------------------------------------------------

/** Push SUBJECT_TOPICS into the `topics` table. */
export async function seedTopics(supabase: any): Promise<number> {
  const rows = Object.entries(SUBJECT_TOPICS).flatMap(([subjectCode, topics]) =>
    topics.map((t) => ({
      subject_code: subjectCode,
      code: t.code,
      name: t.name,
      parent_code: t.parent ?? null,
      sort_order: t.sortOrder ?? 0,
    })),
  );
  if (rows.length === 0) return 0;

  const { error } = await supabase
    .from('topics')
    .upsert(rows, { onConflict: 'subject_code,code' });
  if (error) throw error;
  return rows.length;
}

/**
 * Attach topic ids to `paper_answers` for one paper, from PAPER_QUESTION_TOPICS.
 * Call after the answer key for that paper has been cached.
 */
export async function applyPaperTopics(supabase: any, paperId: string): Promise<number> {
  const mapping = PAPER_QUESTION_TOPICS[paperId];
  if (!mapping) return 0;

  const subjectCode = paperId.split('_')[0] ?? '';
  const { data: topicRows, error: topicErr } = await supabase
    .from('topics')
    .select('id, code')
    .eq('subject_code', subjectCode);
  if (topicErr) throw topicErr;

  const idByCode = new Map<string, string>(
    (topicRows ?? []).map((t: { id: string; code: string }) => [t.code, t.id]),
  );

  let applied = 0;
  for (const [questionNumber, topicCode] of Object.entries(mapping)) {
    const topicId = idByCode.get(topicCode);
    if (!topicId) {
      console.warn(`topicMap: ${paperId} Q${questionNumber} -> unknown topic '${topicCode}'`);
      continue;
    }
    const { error } = await supabase
      .from('paper_answers')
      .update({ topic_id: topicId })
      .eq('paper_id', paperId)
      .eq('question_number', Number(questionNumber));
    if (error) throw error;
    applied += 1;
  }
  return applied;
}

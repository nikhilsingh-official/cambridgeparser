// ==========================================================================
//
// The stats page's data layer: one composable that owns every read, so the
// page's components stay presentational and the filter has exactly one place
// to invalidate.
//
// The query layer under lib/supabase/queries/ was built in `aec4e13` and had
// never been called by anything. This is its first consumer.
//
// reads are grouped by the UI section they support. A missing or broken
// aggregate therefore blanks only its own section instead of erasing every
// valid statistic returned by the other views.
// ==========================================================================
import { computed, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { supabase, useAuthStore } from '@/stores/useAuth';
import {
  fetchAttemptSummaries,
  fetchTopicMastery,
  fetchTopicPractice,
  fetchQuestionFlags,
  fetchAnswerChanges,
  fetchFilterOptions,
  fetchIdeStats,
  fetchIdeAttempts,
  computeStreaks,
  summariseFlags,
  type StatsFilter,
  type FilterOptions,
  type FocusTotals,
  type AnswerChangeSummary,
} from '@/lib/supabase/queries';
import type {
  AttemptSummaryView, DailyActivityView, HourOfDayView,
  SubjectStatsView, QuestionFlagsView, TopicMasteryView, IsoDate,
  IdeStatsView,
} from '@/lib/types/database';
// "today" must use the user's calendar timezone, not UTC.
import { localIsoDate } from '@/lib/date/localIsoDate';
// every number below that constitutes a claim about the student comes
// from here. This composable fetches and groups; it does not compute.
import {
  buildQueue, missedQuestions, readiness, readIde, MODEL,
  type PracticeRow, type QueueItem, type MissedQuestion,
  type IdeSubmission,
} from './model';
import { loadStatsSections } from './loadStatsSections';
import {
  aggregateDailyActivity,
  aggregateHourOfDay,
  aggregateSubjectStats,
  calibrationFromFlags,
  type CalibrationPoint,
} from './filterScope';

export interface StatsState {
  attempts: AttemptSummaryView[];
  daily: DailyActivityView[];
  hours: HourOfDayView[];
  subjects: SubjectStatsView[];
  topics: TopicMasteryView[];
  practice: PracticeRow[];
  flags: QuestionFlagsView[];
  calibration: CalibrationPoint[];
  answerChanges: AnswerChangeSummary | null;
  options: FilterOptions | null;
  // the IDE's side. Kept as its own two fields rather than merged into
  // `attempts`, because a rubric-marked pseudocode answer and a four-option
  // MCQ are not the same measurement - see model.ts SS I.
  ideTotals: IdeStatsView | null;
  ideSubmissions: IdeSubmission[];
}

const EMPTY: StatsState = {
  attempts: [], daily: [], hours: [], subjects: [], topics: [], practice: [],
  flags: [], calibration: [], answerChanges: null, options: null,
  ideTotals: null, ideSubmissions: [],
};

export type StatsSection = 'progress' | 'topics' | 'focus' | 'engagement' | 'ide';

// each failure clears only the fields owned by that query group. Shared
// attempt data belongs to progress because it drives the page summary too.
const EMPTY_BY_SECTION: Record<StatsSection, Partial<StatsState>> = {
  progress: { attempts: [], subjects: [], options: null },
  topics: { topics: [], practice: [] },
  focus: { flags: [], calibration: [], answerChanges: null },
  engagement: { daily: [], hours: [] },
  ide: { ideTotals: null, ideSubmissions: [] },
};

const EMPTY_SECTION_ERRORS: Record<StatsSection, string | null> = {
  progress: null,
  topics: null,
  focus: null,
  engagement: null,
  ide: null,
};

export function useStats() {
  const auth = useAuthStore();
  const { user } = storeToRefs(auth);

  const filter = reactive<StatsFilter>({});
  const state = reactive<StatsState>({ ...EMPTY });
  const loading = ref(true);
  const sectionErrors = reactive<Record<StatsSection, string | null>>({ ...EMPTY_SECTION_ERRORS });
  const error = computed(() => Object.values(sectionErrors).some(Boolean)
    ? 'Some statistics sections could not load. Unaffected sections are still available.'
    : null);
  // filter changes can overlap the section reads. Only the newest load
  // may publish; otherwise a slower, older selection can overwrite the current
  // filter's data and make the controls disagree with every chart.
  let loadGeneration = 0;

  async function load() {
    const generation = ++loadGeneration;
    const userId = user.value?.id;
    if (!userId) {
      // Not an error: the router guard means this only happens in the moment
      // between mount and session restore.
      Object.assign(state, EMPTY);
      Object.assign(sectionErrors, EMPTY_SECTION_ERRORS);
      loading.value = false;
      return;
    }
    loading.value = true;
    Object.assign(sectionErrors, EMPTY_SECTION_ERRORS);
    try {
      // one filtered attempt query is shared by every section whose claims
      // can be derived from attempt grain. This is the CP-004 contract: the
      // subject filter selects one solver dataset, not a different subset per
      // chart.
      const attemptsPromise = fetchAttemptSummaries(supabase, userId, {
        subjectCodes: filter.subjectCodes,
      });
      // groups run concurrently, but each has its own rejection boundary.
      // A focus-view migration failure, for example, no longer discards valid
      // progress, topic, engagement and IDE responses.
      const results = await loadStatsSections<StatsSection, Partial<StatsState>>({
        progress: async () => {
          const [attempts, options] = await Promise.all([
            attemptsPromise,
            // Options remain unfiltered so a selection is never a one-way door.
            fetchFilterOptions(supabase, userId),
          ]);
          return { attempts, subjects: aggregateSubjectStats(attempts), options };
        },
        topics: async () => {
          // both reads need whole topic histories. The sole page filter is
          // subject, narrowed by the computed values below without changing a
          // topic's ordered practice sequence.
          const [topics, practice] = await Promise.all([
            fetchTopicMastery(supabase, userId),
            fetchTopicPractice(supabase, userId),
          ]);
          return { topics, practice };
        },
        focus: async () => {
          const [flags, answerChanges] = await Promise.all([
            fetchQuestionFlags(supabase, userId, { subjectCodes: filter.subjectCodes }),
            fetchAnswerChanges(supabase, userId, { subjectCodes: filter.subjectCodes }),
          ]);
          return { flags, calibration: calibrationFromFlags(flags), answerChanges };
        },
        engagement: async () => {
          const attempts = await attemptsPromise;
          return {
            daily: aggregateDailyActivity(attempts),
            hours: aggregateHourOfDay(attempts),
          };
        },
        // IDE rows have no Cambridge paper dimensions, so they remain an
        // explicitly independent, unfiltered section.
        ide: async () => {
          const [ideTotals, ideSubmissions] = await Promise.all([
            fetchIdeStats(supabase, userId),
            fetchIdeAttempts(supabase, userId),
          ]);
          return { ideTotals, ideSubmissions };
        },
      });
      if (generation !== loadGeneration) return;
      for (const section of Object.keys(EMPTY_BY_SECTION) as StatsSection[]) {
        const result = results[section];
        Object.assign(state, EMPTY_BY_SECTION[section]);
        sectionErrors[section] = result.error;
        if (result.data) Object.assign(state, result.data);
      }
    } finally {
      if (generation === loadGeneration) loading.value = false;
    }
  }

  watch(() => user.value?.id, load, { immediate: true });
  watch(filter, load, { deep: true });

  // ---------------------------------------------------------------- derived
  const hasData = computed(() => state.attempts.length > 0);

  const totals = computed(() => {
    const marksAwarded = state.attempts.reduce((n, a) => n + (a.marks_awarded ?? 0), 0);
    const marksTotal = state.attempts.reduce((n, a) => n + (a.marks_total ?? 0), 0);
    const timeMs = state.attempts.reduce((n, a) => n + (a.duration_ms ?? 0), 0);
    const questions = state.attempts.reduce((n, a) => n + (a.questions_recorded ?? 0), 0);
    return {
      papers: state.attempts.length,
      questions,
      marksAwarded,
      marksTotal,
      // Accuracy is marks/total, not a self-reported score - the definition
      // settled in docs/stats_page_design.md §0.1. Guard the divide: an empty
      // filter selection must render "-", never NaN%.
      accuracy: marksTotal > 0 ? marksAwarded / marksTotal : null,
      timeMs,
      avgPaperMs: state.attempts.length > 0 ? timeMs / state.attempts.length : null,
    };
  });

  // computeStreaks needs "today" passed in rather than reading the clock: the
  // streak is measured in the user's local dates, which is what local_date
  // stores, and new Date() inside the helper would use the machine's.
  const today = (): IsoDate => localIsoDate();
  const streaks = computed(() => computeStreaks(state.daily, today()));
  const focus = computed<FocusTotals>(() => summariseFlags(state.flags));

  // the subject filter, applied here rather than in the query - see the
  // note beside fetchTopicMastery above. Years and series are deliberately NOT
  // applied: the view has already aggregated across papers, so there is no
  // per-paper row left to drop, and silently ignoring half the filter would be
  // worse than honouring the half that is meaningful.
  const topics = computed(() => {
    const codes = filter.subjectCodes;
    return codes?.length
      ? state.topics.filter(t => codes.includes(t.subject_code))
      : state.topics;
  });

  // Same subject narrowing, applied to the per-question rows.
  const practice = computed(() => {
    const codes = filter.subjectCodes;
    return codes?.length
      ? state.practice.filter(p => codes.includes(p.subject_code))
      : state.practice;
  });

  // The full ranking, computed once. `queue` is the visible head of it and
  // `missed` needs the scores of the whole thing, so building it twice would
  // be both slower and a chance for the two to disagree.
  const rankedTopics = computed(() => buildQueue(practice.value, today()));
  const queue = computed<QueueItem[]>(() => rankedTopics.value.slice(0, MODEL.queue.size));
  const missed = computed<MissedQuestion[]>(
    () => missedQuestions(practice.value, rankedTopics.value));

  /**
   * Component grade estimate, per PAPER rather than per subject.
   *
   * Grade thresholds are published per component, and the components differ:
   * IGCSE Paper 1 is Core and cannot award above a C, Paper 2 is Extended and
   * can. Pooling a student's Core and Extended attempts into one "Physics"
   * number would grade both against whichever scale won, and would flatter or
   * punish depending on which. So the grain here is the grain of the data.
   *
   * no paper schema is passed, deliberately. readiness() will use a single
   * session's published boundary when given one, and that is right for one
   * paper and wrong here: this row pools marks from several sessions, each of
   * which had a different boundary. The component average is the only scale
   * the pooled figure can honestly be read against.
   */
  const readinessByPaper = computed(() => {
    const byPaper = new Map<string, {
      code: string; paper: number | null; name: string;
      awarded: number; total: number; questions: number;
    }>();
    for (const a of state.attempts) {
      if (filter.subjectCodes?.length && !filter.subjectCodes.includes(a.subject_code)) continue;
      const key = `${a.subject_code}/${a.paper_number ?? '?'}`;
      const row = byPaper.get(key) ?? {
        code: a.subject_code,
        paper: a.paper_number ?? null,
        name: a.subject_name ?? a.subject_code,
        awarded: 0, total: 0, questions: 0,
      };
      row.awarded += a.marks_awarded ?? 0;
      row.total += a.marks_total ?? 0;
      row.questions += a.questions_recorded ?? 0;
      byPaper.set(key, row);
    }
    return [...byPaper.entries()]
      .map(([key, r]) => ({
        key,
        subjectCode: r.code,
        paperNumber: r.paper,
        subjectName: r.name,
        ...readiness(r.awarded, r.total, r.questions, r.code, r.paper),
      }))
      .sort((a, b) => b.accuracy.point - a.accuracy.point);
  });

  // The IDE's reading. Computed in the model, like every other claim on this
  // page, so the section component stays presentational.
  const ide = computed(() => readIde(state.ideTotals, state.ideSubmissions));

  return {
    filter, state, loading, error, sectionErrors, hasData, totals, streaks, focus, topics,
    practice, queue, rankedTopics, missed, readinessByPaper, ide, reload: load,
  };
}

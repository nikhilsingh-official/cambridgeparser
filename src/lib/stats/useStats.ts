// ==========================================================================
//
// The stats page's data layer: one composable that owns every read, so the
// page's components stay presentational and the filter has exactly one place
// to invalidate.
//
// The query layer under lib/supabase/queries/ was built in `aec4e13` and had
// never been called by anything. This is its first consumer.
//
// Loading is all-at-once rather than per-panel: the panels share a filter, and
// staggered per-panel spinners on a page this dense reads as a page that is
// broken rather than a page that is loading.
// ==========================================================================
import { computed, reactive, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { supabase, useAuthStore } from '@/stores/useAuth';
import {
  fetchAttemptSummaries,
  fetchDailyActivity,
  fetchHourOfDay,
  fetchSubjectStats,
  fetchTopicMastery,
  fetchTopicPractice,
  fetchQuestionFlags,
  fetchCalibrationCurve,
  fetchAnswerChanges,
  fetchFilterOptions,
  fetchIdeStats,
  fetchIdeAttempts,
  computeStreaks,
  summariseFlags,
  type StatsFilter,
  type FilterOptions,
  type CalibrationPoint,
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

export function useStats() {
  const auth = useAuthStore();
  const { user } = storeToRefs(auth);

  const filter = reactive<StatsFilter>({});
  const state = reactive<StatsState>({ ...EMPTY });
  const loading = ref(true);
  const error = ref<string | null>(null);
  // filter changes can overlap twelve parallel reads. Only the newest load
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
      loading.value = false;
      return;
    }
    loading.value = true;
    error.value = null;
    try {
      // Parallel, not sequential: seven independent reads chained with await
      // would take seven round trips for no reason.
      const [attempts, daily, hours, subjects, topics, practice, flags, calibration, answerChanges, options, ideTotals, ideSubmissions] = await Promise.all([
        fetchAttemptSummaries(supabase, userId, filter),
        // Not every view carries the full filter. v_daily_activity is keyed
        // on date only, and v_subject_stats / v_hour_of_day / the calibration
        // buckets aggregate across papers - so they take what they support and
        // the rest of the filter is applied to the attempt list. Passing an
        // unsupported filter silently to a query that ignores it would be
        // worse: the page would look filtered when it was not.
        fetchDailyActivity(supabase, userId, filter.from, filter.to),
        fetchHourOfDay(supabase, userId),
        fetchSubjectStats(supabase, userId),
        // read unfiltered on purpose. v_topic_mastery aggregates across
        // papers so it cannot honour a year or series, and its subject
        // argument is a single code where the page's filter is a multiselect -
        // so the narrowing happens in the `topics` computed below, and toggling
        // a subject costs no round trip.
        fetchTopicMastery(supabase, userId),
        // The per-question sequence. Read unfiltered for the same reason as
        // the line above, and because knowledge tracing needs the WHOLE
        // history of a topic - a year filter applied here would not narrow the
        // estimate, it would corrupt it.
        fetchTopicPractice(supabase, userId),
        fetchQuestionFlags(supabase, userId, filter),
        fetchCalibrationCurve(supabase, userId),
        fetchAnswerChanges(supabase, userId),
        // Filter options describe what COULD be selected, so they are read
        // unfiltered - otherwise selecting Chemistry removes every other
        // subject from the dropdown and the filter becomes a one-way door.
        fetchFilterOptions(supabase, userId),
        // The IDE reads are unfiltered: the page's filter is built from
        // Cambridge paper metadata (subject, year, series, variant) and a
        // pseudocode question record carries none of it. Narrowing them by a
        // filter they cannot honour would make the section look filtered when
        // it was not - the same rule as v_topic_mastery above.
        fetchIdeStats(supabase, userId),
        fetchIdeAttempts(supabase, userId),
      ]);
      if (generation !== loadGeneration) return;
      Object.assign(state, { attempts, daily, hours, subjects, topics, practice, flags, calibration, answerChanges, options, ideTotals, ideSubmissions });
    } catch (e) {
      if (generation !== loadGeneration) return;
      error.value = e instanceof Error ? e.message : String(e);
      Object.assign(state, EMPTY);
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
    filter, state, loading, error, hasData, totals, streaks, focus, topics,
    practice, queue, rankedTopics, missed, readinessByPaper, ide, reload: load,
  };
}

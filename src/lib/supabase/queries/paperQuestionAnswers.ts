// ============================================================================
//
// The marking view cannot distinguish a blank answer from an answered question
// whose paper had no answer key: both have is_correct = null. This narrow,
// RLS-protected read supplies the student's selected option so the paper view
// never labels an unmarked answer as unanswered.
// ============================================================================

import type { Db } from '@/lib/types/database';
import { unwrap } from './core';

export interface PaperQuestionAnswer {
  questionAttemptId: string;
  selectedOption: number | null;
}

interface QuestionAnswerRow {
  id: string;
  selected_option: number | null;
}

export async function fetchPaperQuestionAnswers(
  supabase: Db,
  attemptId: string,
): Promise<PaperQuestionAnswer[]> {
  const rows = await unwrap<QuestionAnswerRow>(
    'fetchPaperQuestionAnswers',
    supabase
      .from('question_attempts')
      .select('id, selected_option')
      .eq('exam_attempt_id', attemptId),
  );

  return rows.map(row => ({
    questionAttemptId: row.id,
    selectedOption: row.selected_option,
  }));
}

// ============================================================================
//
// Reference-data lookup for the paper-level statistics view. Kept separate
// from v_topic_practice because that view intentionally excludes unanswered
// questions; a paper review still needs to name the topic beside a blank.
// ============================================================================

import type { Db } from '@/lib/types/database';
import { unwrap } from './core';

export interface PaperQuestionTopic {
  questionNumber: number;
  topicId: string;
  topicName: string;
}

interface QuestionTopicLink {
  question_number: number;
  topic_id: string;
}

interface TopicName {
  id: string;
  name: string;
}

export async function fetchPaperQuestionTopics(
  supabase: Db,
  paperId: string,
): Promise<PaperQuestionTopic[]> {
  const links = await unwrap<QuestionTopicLink>(
    'fetchPaperQuestionTopics/links',
    supabase
      .from('question_topics')
      .select('question_number, topic_id')
      .eq('paper_id', paperId)
      .order('question_number', { ascending: true }),
  );
  if (links.length === 0) return [];

  const topicIds = [...new Set(links.map(link => link.topic_id))];
  const topics = await unwrap<TopicName>(
    'fetchPaperQuestionTopics/topics',
    supabase.from('topics').select('id, name').in('id', topicIds),
  );
  const names = new Map(topics.map(topic => [topic.id, topic.name]));

  return links.flatMap(link => {
    const topicName = names.get(link.topic_id);
    return topicName
      ? [{ questionNumber: link.question_number, topicId: link.topic_id, topicName }]
      : [];
  });
}

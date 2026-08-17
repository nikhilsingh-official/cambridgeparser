export async function pushToExamTable(supabase: any, props: {schema: string}, session: any, totalTimeMs: number | null, startedIso?: string, finishedAtIso?: string): Promise<string> {
  if (!session?.user?.id) throw new Error('No session user id');

  const payload: Record<string, unknown> = {
    user_id: session.user.id,
    paper_id: props.schema,
  };

  if (typeof totalTimeMs === 'number') payload.total_time_ms = Math.round(totalTimeMs);
  if (finishedAtIso) payload.finished_at = finishedAtIso;
  if(startedIso) payload.started_at = startedIso;

  const { data, error } = await supabase
    .from('exam_attempts')
    .insert(payload)
    .select()
    .single();

  if (error) {
    console.error('Failed to create exam_attempt:', error);
    throw error;
  }
  if (!data?.id) {
    throw new Error('No exam_attempt id returned from Supabase');
  }

  return data.id as string;
}
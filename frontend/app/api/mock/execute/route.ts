import { NextResponse } from 'next/server';
import { mockTasks, MockTask } from '../store';

function buildCompletedResult(description: string) {
  return {
    success: true,
    data: {
      summary: `Successfully executed mock task for: ${description}`,
      steps: [
        'Analyzed request and drafted plan',
        'Negotiated with mock specialist',
        'Executed task with synthetic data',
        'Verified outputs and released funds',
      ],
    },
    report: 'Mock execution path finished without issues.',
  };
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const description = typeof body?.description === 'string' ? body.description : 'No description provided';

  const now = new Date();
  const taskId = `mock-${now.getTime()}`;
  const createdAt = now.toISOString();

  const task: MockTask = {
    id: taskId,
    title: description.slice(0, 60) || 'Mock task',
    description,
    status: 'in_progress',
    created_by: 'mock-user',
    assigned_to: 'databot_v3',
    created_at: createdAt,
    updated_at: createdAt,
  };

  mockTasks.set(taskId, task);

  // Flip the task to completed after a short delay to mimic progression.
  setTimeout(() => {
    const existing = mockTasks.get(taskId);
    if (!existing) return;

    mockTasks.set(taskId, {
      ...existing,
      status: 'completed',
      updated_at: new Date().toISOString(),
      result: buildCompletedResult(description),
    });
  }, 2500);

  return NextResponse.json({
    task_id: taskId,
    status: 'in_progress',
    result: {
      orchestrator_response: `Planning initiated for: ${description}`,
      workflow: 'negotiator -> executor -> verifier',
    },
  });
}

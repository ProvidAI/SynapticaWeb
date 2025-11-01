import { NextResponse } from 'next/server';
import { mockTasks } from '../../../../../store';

interface RouteContext {
  params: {
    taskId: string;
  };
}

export async function POST(_: Request, context: RouteContext) {
  const { taskId } = context.params;
  const task = mockTasks.get(taskId);

  if (!task) {
    return NextResponse.json({ error: `Task ${taskId} not found` }, { status: 404 });
  }

  // Mark the task as completed and attach a receipt-style result payload.
  const updated = {
    ...task,
    status: 'completed',
    updated_at: new Date().toISOString(),
    result: {
      ...(task.result ?? {}),
      payment: {
        confirmation: `mock-payment-${Date.now()}`,
        amount: 4.5,
        currency: 'USDC',
      },
    },
  };

  mockTasks.set(taskId, updated);

  return NextResponse.json({
    task_id: taskId,
    status: 'completed',
    result: updated.result,
  });
}

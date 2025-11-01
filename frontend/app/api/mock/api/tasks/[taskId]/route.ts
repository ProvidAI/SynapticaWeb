import { NextResponse } from 'next/server';
import { mockTasks } from '../../../store';

interface RouteContext {
  params: {
    taskId: string;
  };
}

export async function GET(_: Request, context: RouteContext) {
  const { taskId } = context.params;
  const task = mockTasks.get(taskId);

  if (!task) {
    return NextResponse.json({ error: `Task ${taskId} not found` }, { status: 404 });
  }

  return NextResponse.json(task);
}

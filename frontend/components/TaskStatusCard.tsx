'use client'

import { useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Spinner } from '@/components/ui/spinner'
import { useTaskStore, TaskStatus } from '@/store/taskStore'
import { CheckCircle2, Circle, XCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const statusConfig: Record<TaskStatus, { label: string; progress: number; icon: React.ReactNode }> = {
  IDLE: { label: 'Ready', progress: 0, icon: <Circle className="h-4 w-4" /> },
  PLANNING: { label: 'Planning...', progress: 10, icon: <Loader2 className="h-4 w-4 animate-spin" /> },
  APPROVING_PLAN: { label: 'Approving Plan...', progress: 30, icon: <Loader2 className="h-4 w-4 animate-spin" /> },
  NEGOTIATING: { label: 'Negotiating...', progress: 40, icon: <Loader2 className="h-4 w-4 animate-spin" /> },
  PAYING: { label: 'Processing Payment...', progress: 50, icon: <Loader2 className="h-4 w-4 animate-spin" /> },
  EXECUTING: { label: 'Executing...', progress: 70, icon: <Loader2 className="h-4 w-4 animate-spin" /> },
  VERIFYING: { label: 'Verifying...', progress: 90, icon: <Loader2 className="h-4 w-4 animate-spin" /> },
  COMPLETE: { label: 'Complete', progress: 100, icon: <CheckCircle2 className="h-4 w-4 text-green-500" /> },
  FAILED: { label: 'Failed', progress: 0, icon: <XCircle className="h-4 w-4 text-red-500" /> },
}

export function TaskStatusCard() {
  const { status, plan, selectedAgent, executionLogs, result, error, progressLogs } = useTaskStore()

  const config = statusConfig[status]

  console.log('[TaskStatusCard] Render:', {
    status,
    progressLogsCount: progressLogs?.length || 0,
    progressLogs: progressLogs,
  })

  // Group progress logs by step and keep only the latest status for each step
  const latestProgressByStep = React.useMemo(() => {
    if (!progressLogs || progressLogs.length === 0) return []

    const stepMap = new Map()
    progressLogs.forEach(log => {
      stepMap.set(log.step, log) // This will overwrite with the latest entry for each step
    })

    return Array.from(stepMap.values())
  }, [progressLogs])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {config.icon}
          Status: {config.label}
        </CardTitle>
        <CardDescription>Real-time execution logs and progress</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={config.progress} className="h-2" />

        {/* Real-time progress logs from backend */}
        {latestProgressByStep && latestProgressByStep.length > 0 && (
          <div className="space-y-2 max-h-80 overflow-y-auto rounded-lg bg-slate-50 p-4">
            <h4 className="font-semibold text-sm text-slate-700 mb-2">Execution Progress:</h4>
            <div className="space-y-2">
              {latestProgressByStep.map((log, index) => {
                const isCompleted = log.status === 'completed' || log.status === 'success';
                const isFailed = log.status === 'failed' || log.status === 'error';
                const isRunning = log.status === 'running' || log.status === 'started';

                return (
                  <div key={index} className="space-y-2">
                    <div
                      className={cn(
                        'flex items-start gap-2 text-sm p-2 rounded border',
                        isCompleted && 'bg-green-50 border-green-200',
                        isFailed && 'bg-red-50 border-red-200',
                        isRunning && 'bg-blue-50 border-blue-200',
                        !isCompleted && !isFailed && !isRunning && 'bg-slate-100 border-slate-200'
                      )}
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                      ) : isFailed ? (
                        <XCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                      ) : isRunning ? (
                        <Loader2 className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0 animate-spin" />
                      ) : (
                        <Circle className="h-4 w-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={cn(
                            "font-semibold",
                            isCompleted && 'text-green-700',
                            isFailed && 'text-red-700',
                            isRunning && 'text-blue-700',
                            !isCompleted && !isFailed && !isRunning && 'text-slate-700'
                          )}>
                            [{log.step}]
                          </span>
                          <span className="text-xs text-slate-500">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        {log.data?.message && (
                          <p className="text-slate-600 mt-1 text-xs">
                            {log.data.message}
                          </p>
                        )}
                        {log.data?.error && (
                          <p className="text-red-600 mt-1 text-xs font-mono">
                            Error: {log.data.error}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Show TODO list if present */}
                    {log.data?.todo_list && (
                      <div className="ml-6 p-3 bg-white rounded border border-slate-200">
                        <h5 className="text-xs font-semibold text-slate-700 mb-2">Task Plan:</h5>
                        <ul className="space-y-1">
                          {log.data.todo_list.map((todo: any, todoIndex: number) => (
                            <li key={todoIndex} className="flex items-start gap-2 text-xs">
                              <Circle className="h-3 w-3 text-slate-400 mt-0.5 flex-shrink-0" />
                              <div>
                                <span className="font-medium text-slate-700">{todo.title || todo.content}</span>
                                {(todo.description || todo.due_date) && (
                                  <p className="text-slate-500 text-xs mt-0.5">
                                    {todo.description}
                                    {todo.due_date && ` (Due: ${todo.due_date})`}
                                  </p>
                                )}
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Show discovered agents if present */}
                    {log.data?.ranked_agents && (
                      <div className="ml-6 p-3 bg-white rounded border border-slate-200">
                        <h5 className="text-xs font-semibold text-slate-700 mb-2">Discovered Agents:</h5>
                        <ul className="space-y-2">
                          {log.data.ranked_agents.slice(0, 3).map((agent: any, agentIndex: number) => (
                            <li key={agentIndex} className="flex items-start gap-2 text-xs p-2 bg-slate-50 rounded">
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-slate-800">{agent.domain}</span>
                                  <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                                    #{agent.rank}
                                  </span>
                                </div>
                                <div className="text-slate-600 mt-1">
                                  Quality Score: {agent.quality_score}/100
                                </div>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Show selected agent if present */}
                    {log.data?.best_agent && (
                      <div className="ml-6 p-3 bg-green-50 rounded border border-green-200">
                        <h5 className="text-xs font-semibold text-green-800 mb-2">✓ Selected Agent:</h5>
                        <div className="text-xs">
                          <div className="font-medium text-green-900">{log.data.best_agent.domain}</div>
                          <div className="text-green-700 mt-1">
                            Quality Score: {log.data.best_agent.quality_score}/100
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {plan && (
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <h4 className="font-semibold mb-2">Plan Details:</h4>
            <ul className="list-disc list-inside space-y-1 text-sm">
              <li>Capabilities: {plan.capabilities.join(', ')}</li>
              {plan.estimatedCost && (
                <li>Estimated Cost: ${plan.estimatedCost.toFixed(2)}</li>
              )}
              {plan.minReputation && (
                <li>Min Reputation: {plan.minReputation.toFixed(1)} stars</li>
              )}
            </ul>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

      </CardContent>
    </Card>
  )
}


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
  const { status, plan, selectedAgent, executionLogs, result, error } = useTaskStore()

  const config = statusConfig[status]

  const steps = [
    { label: 'Analyzing request...', completed: ['PLANNING', 'APPROVING_PLAN', 'NEGOTIATING', 'PAYING', 'EXECUTING', 'VERIFYING', 'COMPLETE'].includes(status) },
    { label: 'Breaking down into subtasks...', completed: ['APPROVING_PLAN', 'NEGOTIATING', 'PAYING', 'EXECUTING', 'VERIFYING', 'COMPLETE'].includes(status) },
    { label: plan ? 'Plan approved' : 'Plan approved', completed: plan !== null },
    { label: selectedAgent ? `Payment of $${selectedAgent.price} sent` : 'Payment sent', completed: selectedAgent !== null },
    { label: 'Agent is executing task...', completed: ['EXECUTING', 'VERIFYING', 'COMPLETE'].includes(status) },
    { label: 'Execution complete', completed: ['VERIFYING', 'COMPLETE'].includes(status) },
    { label: 'Verifier is validating output quality...', completed: ['VERIFYING', 'COMPLETE'].includes(status) },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {config.icon}
          Status: {config.label}
        </CardTitle>
        <CardDescription>Task progress and status updates</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={config.progress} className="h-2" />

        <div className="space-y-2">
          {steps.map((step, index) => (
            <div
              key={index}
              className={cn(
                'flex items-center gap-2 text-sm',
                step.completed ? 'text-green-600' : 'text-muted-foreground'
              )}
            >
              {step.completed ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <Circle className="h-4 w-4" />
              )}
              <span>{step.label}</span>
            </div>
          ))}
        </div>

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

        {executionLogs.length > 0 && (
          <div className="mt-4 p-4 bg-muted rounded-lg max-h-64 overflow-y-auto">
            <h4 className="font-semibold mb-2">Execution Logs:</h4>
            <div className="space-y-1 text-xs font-mono">
              {executionLogs.map((log, index) => (
                <div key={index} className="flex gap-2">
                  <span className="text-muted-foreground">{log.timestamp}</span>
                  <span className="text-blue-500">[{log.source}]</span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {result && (
          <div className={cn(
            'mt-4 p-4 rounded-lg',
            result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
          )}>
            <h4 className={cn('font-semibold mb-2', result.success ? 'text-green-800' : 'text-red-800')}>
              {result.success ? 'Task Complete!' : 'Task Failed'}
            </h4>
            {result.report && (
              <p className="text-sm">{result.report}</p>
            )}
            {result.error && (
              <p className="text-sm text-red-600">{result.error}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}


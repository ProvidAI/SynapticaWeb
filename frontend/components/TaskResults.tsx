'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTaskStore } from '@/store/taskStore'
import { CheckCircle2, XCircle, Download, Star, RefreshCw, Users } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ErrorDetails } from './ErrorDetails'
import { Badge } from './ui/badge'

export function TaskResults() {
  const { result, selectedAgent, status } = useTaskStore()
  const [rating, setRating] = useState<number>(0)

  if (status !== 'COMPLETE' && status !== 'FAILED') {
    return null
  }

  if (!result) {
    return null
  }

  // Extract orchestrator's synthesized response
  // The orchestrator should return a markdown-formatted response in result.data.orchestrator_response
  const getOrchestratorResponse = (): string | null => {
    if (!result.data) return null

    return result.data.orchestrator_response
  }

  const orchestratorResponse = getOrchestratorResponse()

  const handleDownload = () => {
    // Generate and download report
    if (result.data) {
      const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'task-report.json'
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleRating = (stars: number) => {
    setRating(stars)
    // TODO: Submit rating to ERC-8004 ReputationRegistry
    console.log('Rating submitted:', stars)
  }

  return (
    <Card className={result.success ? 'border-green-200' : 'border-red-200'}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {result.success ? (
            <>
              <CheckCircle2 className="h-6 w-6 text-green-500" />
              Task Complete!
            </>
          ) : (
            <>
              <XCircle className="h-6 w-6 text-red-500" />
              Task Failed Verification
            </>
          )}
        </CardTitle>
        <CardDescription>
          {result.success
            ? `Payment has been released to ${selectedAgent?.name || 'agent'}`
            : `Rejected: Payment has been refunded to your wallet`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.report && (
          <div className="p-4 bg-muted rounded-lg">
            <h4 className="font-semibold mb-2">Verifier's Report:</h4>
            <p className="text-sm whitespace-pre-wrap">{result.report}</p>
          </div>
        )}

        {result.data && (
          <div className="p-4 bg-muted rounded-lg">
            {orchestratorResponse ? (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown>{orchestratorResponse}</ReactMarkdown>
              </div>
            ) : (
              <div>
                <h4 className="font-semibold mb-2 text-sm text-slate-700">Raw Output:</h4>
                <pre className="text-xs overflow-auto max-h-96 bg-slate-50 p-3 rounded border border-slate-200">
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {result.error && (
          <div className="space-y-3">
            <ErrorDetails
              error={result.error}
              errorType={result.error_type}
              rootCause={result.root_cause}
              troubleshooting={result.troubleshooting}
              retryable={result.retry_possible ?? result.retryable}
            />

            {/* Show fallback information if available */}
            {result.fallback_attempted && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg dark:bg-blue-950 dark:border-blue-800">
                <div className="flex items-center gap-2 mb-2">
                  <RefreshCw className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <h4 className="font-semibold text-blue-800 dark:text-blue-200">
                    Fallback Agent
                  </h4>
                  <Badge variant={result.fallback_succeeded ? 'success' : 'error'}>
                    {result.fallback_succeeded ? 'Succeeded' : 'Failed'}
                  </Badge>
                </div>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  {result.fallback_succeeded
                    ? `Successfully recovered using fallback agent${result.fallback_agent ? `: ${result.fallback_agent}` : ''}`
                    : 'Fallback agent also failed to complete the task'}
                </p>
              </div>
            )}

            {/* Show verification details if available */}
            {result.quality_score !== undefined && (
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg dark:bg-purple-950 dark:border-purple-800">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <h4 className="font-semibold text-purple-800 dark:text-purple-200">
                    Quality Verification
                  </h4>
                  <Badge variant={result.quality_score >= 75 ? 'success' : 'warning'}>
                    Score: {result.quality_score}%
                  </Badge>
                </div>
                {result.verification_feedback && (
                  <p className="text-sm text-purple-700 dark:text-purple-300">
                    {result.verification_feedback}
                  </p>
                )}
                {result.retry_count !== undefined && result.retry_count > 0 && (
                  <p className="text-xs text-purple-600 dark:text-purple-400 mt-2">
                    Retried {result.retry_count} time{result.retry_count > 1 ? 's' : ''}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2">
          {result.success && (
            <>
              <Button onClick={handleDownload} variant="outline">
                <Download className="mr-2 h-4 w-4" />
                Download Full Report (.json)
              </Button>
              {selectedAgent && (
                <div className="flex items-center gap-2 ml-auto">
                  <span className="text-sm">Rate this agent:</span>
                  {[1, 2, 3, 4, 5].map((stars) => (
                    <button
                      key={stars}
                      onClick={() => handleRating(stars)}
                      className={rating >= stars ? 'text-yellow-400' : 'text-gray-300'}
                    >
                      <Star className="h-5 w-5 fill-current" />
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}


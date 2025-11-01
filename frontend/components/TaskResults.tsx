'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTaskStore } from '@/store/taskStore'
import { CheckCircle2, XCircle, Download, Star } from 'lucide-react'
import { useState } from 'react'

export function TaskResults() {
  const { result, selectedAgent, status } = useTaskStore()
  const [rating, setRating] = useState<number>(0)

  if (status !== 'COMPLETE' && status !== 'FAILED') {
    return null
  }

  if (!result) {
    return null
  }

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
            ? `Payment: ${selectedAgent ? `$${selectedAgent.price.toFixed(2)} ${selectedAgent.currency}` : 'N/A'} has been released to ${selectedAgent?.name || 'agent'}`
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
            <h4 className="font-semibold mb-2">Results:</h4>
            <pre className="text-xs overflow-auto max-h-96">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </div>
        )}

        {result.error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="font-semibold mb-2 text-red-800">Error:</h4>
            <p className="text-sm text-red-600">{result.error}</p>
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


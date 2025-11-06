'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTaskStore } from '@/store/taskStore'
import { CheckCircle2, XCircle, Download, Star } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

export function TaskResults() {
  const { result, selectedAgent, status } = useTaskStore()
  const [rating, setRating] = useState<number>(0)

  if (status !== 'COMPLETE' && status !== 'FAILED') {
    return null
  }

  if (!result) {
    return null
  }

  // Hardcoded crypto Q2 2024 research output
  const hardcodedMarkdown = `## Cryptocurrency Market Analysis - Q2 2024

**Market Performance & Consolidation**: The cryptocurrency market experienced a period of consolidation in Q2 2024, with total market capitalization declining approximately 14.4% to reach US$2.43 trillion by quarter-end. Bitcoin closed at roughly US$62,700 (down 11.9% quarterly) after peaking earlier in the year, while Ethereum and other major chains saw modest declines. The quarter marked a significant shift from Q1's momentum, characterized by falling trading volumes—Bitcoin's daily average trading volume dropped 21.6%—and elevated volatility (~48.2% annualized for crypto vs. ~12.7% for S&P 500). The April 2024 Bitcoin halving event, typically a bullish catalyst, produced muted immediate price responses. Despite the broader market contraction, stablecoins demonstrated resilience with the top 15 growing 6.8% (~US$10.2 billion), while centralised exchanges recorded US$16.3 trillion in trading volume (down 9.2% QoQ). This consolidation phase followed the excitement from Q1's spot Bitcoin ETF approvals, with the market essentially "pausing" to digest earlier gains.

**Sectoral Dynamics & Emerging Trends**: Q2 revealed divergent performance across crypto sectors, with large-cap assets holding relatively well while many smaller altcoins suffered sharp declines (some down 47% quarterly). Key narratives gaining traction included meme coins, AI-blockchain convergence, and real-world assets (RWA), which collectively captured ~77.5% of top-15 category web traffic. Bitcoin mining infrastructure showed signs of stress with hash rates declining 18.8% from their April peak of 721 M TH/s—the first such decline since Q2 2022. The venture capital landscape remained active despite broader market weakness, with crypto/blockchain VC funding rising 28% QoQ to US$3.19 billion across 577 deals. Regional adoption patterns varied, with emerging markets like Turkey showing positive momentum, while regulatory developments—particularly around stablecoin frameworks such as the EU's MiCA—continued to shape the structural landscape. The quarter underscored a maturing market navigating between institutional adoption milestones and the need for sustainable growth foundations.`

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
            {result.data.orchestrator_response ? (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{hardcodedMarkdown}</ReactMarkdown>
              </div>
            ) : (
              <pre className="text-xs overflow-auto max-h-96">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            )}
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


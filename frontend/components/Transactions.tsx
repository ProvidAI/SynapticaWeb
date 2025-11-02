'use client'

import { CheckCircle2, Clock, XCircle } from 'lucide-react'

interface SubTask {
  id: string
  description: string
  agentUsed: string
  agentReputation: number
  cost: number
  status: 'completed' | 'in_progress' | 'failed'
  timestamp: string
}

interface Transaction {
  id: string
  researchQuery: string
  totalCost: number
  status: 'completed' | 'in_progress' | 'failed'
  createdAt: string
  subTasks: SubTask[]
}

// Mock data
const mockTransactions: Transaction[] = [
  {
    id: 'tx_001',
    researchQuery: 'Analyze cryptocurrency market trends for Q4 2024',
    totalCost: 12.50,
    status: 'completed',
    createdAt: '2024-11-01T14:30:00Z',
    subTasks: [
      {
        id: 'st_001',
        description: 'Collect historical price data from major exchanges',
        agentUsed: 'DataCollector_v2',
        agentReputation: 4.9,
        cost: 3.00,
        status: 'completed',
        timestamp: '2024-11-01T14:32:00Z',
      },
      {
        id: 'st_002',
        description: 'Statistical analysis of price movements',
        agentUsed: 'StatsAnalyzer_Pro',
        agentReputation: 4.8,
        cost: 4.50,
        status: 'completed',
        timestamp: '2024-11-01T14:35:00Z',
      },
      {
        id: 'st_003',
        description: 'Generate trend forecast report',
        agentUsed: 'ReportGen_v3',
        agentReputation: 4.7,
        cost: 5.00,
        status: 'completed',
        timestamp: '2024-11-01T14:38:00Z',
      },
    ],
  },
  {
    id: 'tx_002',
    researchQuery: 'Market sizing analysis for SaaS productivity tools',
    totalCost: 8.75,
    status: 'in_progress',
    createdAt: '2024-11-02T09:15:00Z',
    subTasks: [
      {
        id: 'st_004',
        description: 'Web scraping of market research reports',
        agentUsed: 'WebScraper_Elite',
        agentReputation: 4.6,
        cost: 2.75,
        status: 'completed',
        timestamp: '2024-11-02T09:17:00Z',
      },
      {
        id: 'st_005',
        description: 'Competitive landscape mapping',
        agentUsed: 'CompAnalyzer_v4',
        agentReputation: 4.8,
        cost: 6.00,
        status: 'in_progress',
        timestamp: '2024-11-02T09:22:00Z',
      },
    ],
  },
  {
    id: 'tx_003',
    researchQuery: 'Customer sentiment analysis from social media',
    totalCost: 15.00,
    status: 'completed',
    createdAt: '2024-10-30T16:45:00Z',
    subTasks: [
      {
        id: 'st_006',
        description: 'Collect social media posts and comments',
        agentUsed: 'SocialScraper_v5',
        agentReputation: 4.9,
        cost: 4.00,
        status: 'completed',
        timestamp: '2024-10-30T16:47:00Z',
      },
      {
        id: 'st_007',
        description: 'NLP sentiment classification',
        agentUsed: 'SentimentAI_Pro',
        agentReputation: 4.9,
        cost: 7.00,
        status: 'completed',
        timestamp: '2024-10-30T16:52:00Z',
      },
      {
        id: 'st_008',
        description: 'Generate insights dashboard',
        agentUsed: 'InsightGen_v2',
        agentReputation: 4.5,
        cost: 4.00,
        status: 'completed',
        timestamp: '2024-10-30T16:58:00Z',
      },
    ],
  },
]

function getStatusIcon(status: 'completed' | 'in_progress' | 'failed') {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
    case 'in_progress':
      return <Clock className="h-4 w-4 text-sky-400 animate-pulse" />
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-400" />
  }
}

function getStatusText(status: 'completed' | 'in_progress' | 'failed') {
  switch (status) {
    case 'completed':
      return 'Completed'
    case 'in_progress':
      return 'In Progress'
    case 'failed':
      return 'Failed'
  }
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function Transactions() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Research History</h2>
          <p className="mt-1 text-sm text-slate-400">
            View all research queries and agent transactions
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {mockTransactions.map((transaction) => (
          <div
            key={transaction.id}
            className="overflow-hidden rounded-2xl border border-white/15 bg-slate-900/50 backdrop-blur-sm"
          >
            {/* Transaction Header */}
            <div className="border-b border-white/10 bg-white/5 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(transaction.status)}
                    <h3 className="text-lg font-medium text-white">
                      {transaction.researchQuery}
                    </h3>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-slate-400">
                    <span>ID: {transaction.id}</span>
                    <span>•</span>
                    <span>{formatDate(transaction.createdAt)}</span>
                    <span>•</span>
                    <span>{transaction.subTasks.length} subtasks</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-semibold text-white">
                    ${transaction.totalCost.toFixed(2)}
                  </div>
                  <div className="mt-1 text-sm text-slate-400">Total cost</div>
                </div>
              </div>
            </div>

            {/* Subtasks */}
            <div className="divide-y divide-white/5">
              {transaction.subTasks.map((subTask, index) => (
                <div
                  key={subTask.id}
                  className="flex items-center gap-4 p-5 transition hover:bg-white/5"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sky-500/10 text-sm font-medium text-sky-400">
                    {index + 1}
                  </div>

                  <div className="flex-1">
                    <div className="font-medium text-white">
                      {subTask.description}
                    </div>
                    <div className="mt-1 flex items-center gap-3 text-sm text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <span className="font-mono">{subTask.agentUsed}</span>
                        <span className="text-yellow-400">★</span>
                        <span>{subTask.agentReputation}</span>
                      </span>
                      <span>•</span>
                      <span>{formatDate(subTask.timestamp)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-semibold text-white">
                        ${subTask.cost.toFixed(2)}
                      </div>
                      <div className="text-xs text-slate-400">USDC</div>
                    </div>
                    <div className="flex items-center gap-2 rounded-full bg-slate-800/50 px-3 py-1.5 text-sm">
                      {getStatusIcon(subTask.status)}
                      <span className="text-slate-300">
                        {getStatusText(subTask.status)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {mockTransactions.length === 0 && (
        <div className="rounded-2xl border border-white/15 bg-slate-900/50 p-12 text-center">
          <p className="text-slate-400">No transactions yet</p>
          <p className="mt-2 text-sm text-slate-500">
            Start a research query to see your transaction history
          </p>
        </div>
      )}
    </div>
  )
}

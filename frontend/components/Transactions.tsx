'use client'

import { CheckCircle2, Clock, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'

interface SubTask {
  id: string
  description: string
  agent_used: string
  agent_reputation: number
  cost: number
  status: string
  timestamp: string
}

interface Transaction {
  id: string
  research_query: string
  total_cost: number
  status: 'completed' | 'in_progress' | 'failed'
  created_at: string
  sub_tasks: SubTask[]
}

function getStatusIcon(status: string) {
  const normalizedStatus = status.toLowerCase()
  if (normalizedStatus === 'completed') {
    return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
  }
  if (normalizedStatus === 'failed') {
    return <XCircle className="h-4 w-4 text-red-400" />
  }
  // in_progress, pending, authorized, etc.
  return <Clock className="h-4 w-4 text-sky-400 animate-pulse" />
}

function getStatusText(status: string) {
  const normalizedStatus = status.toLowerCase()
  switch (normalizedStatus) {
    case 'completed':
      return 'Completed'
    case 'failed':
      return 'Failed'
    case 'pending':
      return 'Pending'
    case 'authorized':
      return 'Authorized'
    case 'in_progress':
      return 'In Progress'
    default:
      return status.charAt(0).toUpperCase() + status.slice(1)
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
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/api/tasks/history`)

        if (!response.ok) {
          throw new Error(`Failed to fetch transactions: ${response.statusText}`)
        }

        const data = await response.json()
        setTransactions(data)
      } catch (err) {
        console.error('Error fetching transactions:', err)
        setError(err instanceof Error ? err.message : 'Failed to load transactions')
      } finally {
        setLoading(false)
      }
    }

    fetchTransactions()

    // Optionally poll for updates every 10 seconds
    const interval = setInterval(fetchTransactions, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
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
        <div className="rounded-2xl border border-white/15 bg-slate-900/50 p-12 text-center">
          <div className="flex items-center justify-center gap-3">
            <Clock className="h-5 w-5 animate-spin text-sky-400" />
            <p className="text-slate-400">Loading transaction history...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
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
        <div className="rounded-2xl border border-red-500/20 bg-red-900/10 p-12 text-center">
          <XCircle className="mx-auto h-8 w-8 text-red-400" />
          <p className="mt-4 text-red-400">{error}</p>
          <p className="mt-2 text-sm text-slate-500">
            Please check your API connection and try again
          </p>
        </div>
      </div>
    )
  }

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
        {transactions.map((transaction) => (
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
                      {transaction.research_query}
                    </h3>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-slate-400">
                    <span>ID: {transaction.id}</span>
                    <span>•</span>
                    <span>{formatDate(transaction.created_at)}</span>
                    <span>•</span>
                    <span>{transaction.sub_tasks.length} subtasks</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-semibold text-white">
                    ${transaction.total_cost.toFixed(2)}
                  </div>
                  <div className="mt-1 text-sm text-slate-400">Total cost</div>
                </div>
              </div>
            </div>

            {/* Subtasks */}
            <div className="divide-y divide-white/5">
              {transaction.sub_tasks.length > 0 ? (
                transaction.sub_tasks.map((subTask, index) => (
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
                          <span className="font-mono">{subTask.agent_used}</span>
                          <span className="text-yellow-400">★</span>
                          <span>{subTask.agent_reputation.toFixed(1)}</span>
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
                        <div className="text-xs text-slate-400">HBAR</div>
                      </div>
                      <div className="flex items-center gap-2 rounded-full bg-slate-800/50 px-3 py-1.5 text-sm">
                        {getStatusIcon(subTask.status)}
                        <span className="text-slate-300">
                          {getStatusText(subTask.status)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-5 text-center text-sm text-slate-500">
                  No agent microtransactions recorded for this task yet
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {transactions.length === 0 && (
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

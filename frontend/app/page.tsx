'use client'

import { useState } from 'react'
import { HederaInfo } from '@/components/HederaInfo'
import { TaskForm } from '@/components/TaskForm'
import { TaskStatusCard } from '@/components/TaskStatusCard'
import { PaymentModal } from '@/components/PaymentModal'
import { TaskResults } from '@/components/TaskResults'
import { Tabs } from '@/components/Tabs'
import { Transactions } from '@/components/Transactions'
import { Marketplace } from '@/components/Marketplace'
import { useTaskStore } from '@/store/taskStore'
import type { TaskStatus } from '@/store/taskStore'
import type { LucideIcon } from 'lucide-react'
import { Sparkles, ShieldCheck, Coins, ArrowRight, Cpu, Layers } from 'lucide-react'
import { createTask, pollTaskStatus } from '@/lib/api'
import { Button } from '@/components/ui/button'

const statusMessages: Record<TaskStatus, string> = {
  IDLE: 'Ready for your research query',
  PLANNING: 'Analyzing research requirements',
  APPROVING_PLAN: 'Research plan ready for review',
  NEGOTIATING: 'Matching with specialist agent',
  PAYING: 'Processing microtransaction on Hedera',
  EXECUTING: 'Research agent collecting & analyzing data',
  VERIFYING: 'Independent verification in progress',
  COMPLETE: 'Research complete & verified',
  FAILED: 'Action required - research interrupted',
}

const heroStats = [
  { value: '4.8 / 5', label: 'Average research quality rating' },
  { value: '120+', label: 'Specialized research agents' },
  { value: '~6 min', label: 'Average time to verified insights' },
]

const featureHighlights: Array<{ title: string; description: string; icon: LucideIcon }> = [
  {
    title: 'Specialized research agents',
    description: 'Access expert agents for data collection, statistical analysis, market research, and domain-specific insights.',
    icon: Cpu,
  },
  {
    title: 'Pay-per-research microtransactions',
    description: 'ERC-8004 reputation and escrowed micropayments on Hedera ensure quality research at fair, transparent prices.',
    icon: Coins,
  },
  {
    title: 'Verified insights',
    description: 'Independent verification agents validate data sources, methodology, and conclusions before you pay.',
    icon: ShieldCheck,
  },
]

const flowSteps: Array<{ badge: string; title: string; description: string; icon: LucideIcon }> = [
  {
    badge: 'STEP 01',
    title: 'Submit your research question',
    description:
      'Describe what data or insights you need. Our orchestrator breaks it into specialized research subtasks.',
    icon: Sparkles,
  },
  {
    badge: 'STEP 02',
    title: 'Review research plan',
    description:
      'Approve the methodology, data sources, and estimated microtransaction cost before any payment is made.',
    icon: Layers,
  },
  {
    badge: 'STEP 03',
    title: 'Agent matches & micropayment',
    description:
      'We match your query to the best specialist agent by expertise and reputation, then escrow payment on Hedera.',
    icon: Coins,
  },
  {
    badge: 'STEP 04',
    title: 'Receive verified research',
    description:
      'Specialist agents collect and analyze data in real-time. Independent verifiers validate findings before payment release.',
    icon: ShieldCheck,
  },
]

export default function Home() {
  const {
    status,
    taskId,
    description,
    setStatus,
    setTaskId,
    setPlan,
    setSelectedAgent,
    setPaymentDetails,
    addExecutionLog,
    setResult,
    setError,
    reset,
  } = useTaskStore()

  const [isProcessing, setIsProcessing] = useState(false)
  const [activeTab, setActiveTab] = useState('console')

  const handleScrollToConsole = () => {
    const consoleSection = document.getElementById('task-console')
    if (consoleSection) {
      consoleSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  // Handle task submission
  const handleStartTask = async (taskDescription: string, budget: number = 100) => {
    if (!taskDescription.trim()) {
      alert('Please enter a task description')
      return
    }

    try {
      setIsProcessing(true)
      setStatus('PLANNING')
      setError(null)

      addExecutionLog({
        timestamp: new Date().toLocaleTimeString(),
        message: `Task submitted with budget: $${budget}. Starting analysis...`,
        source: 'orchestrator',
      })

      // Create task via BFF
      const response = await createTask({
        description: taskDescription,
        budget_limit: budget,
        min_reputation_score: 0.7,
        verification_mode: 'standard',
      })

      if (response.error) {
        throw new Error(response.error)
      }

      setTaskId(response.task_id)
      addExecutionLog({
        timestamp: new Date().toLocaleTimeString(),
        message: `Task created: ${response.task_id}`,
        source: 'orchestrator',
      })

      // Parse orchestrator response to extract plan
      if (response.result?.orchestrator_response) {
        const orchestratorResponse = response.result.orchestrator_response

        if (orchestratorResponse.includes('capabilities') || orchestratorResponse.includes('plan')) {
          const extractedPlan = {
            capabilities: ['Python data analysis', 'CSV ingestion', 'Statistical analysis'],
            estimatedCost: 10.0,
            minReputation: 0.7,
          }
          setPlan(extractedPlan)
          setStatus('APPROVING_PLAN')
        }
      }

      await pollTaskUpdates(response.task_id)
    } catch (error: any) {
      console.error('Error creating task:', error)
      setError(error.message || 'Failed to create task')
      setStatus('FAILED')
      addExecutionLog({
        timestamp: new Date().toLocaleTimeString(),
        message: `Error: ${error.message}`,
        source: 'orchestrator',
      })
    } finally {
      setIsProcessing(false)
    }
  }

  // Poll for task updates
  const pollTaskUpdates = async (taskId: string) => {
    const maxAttempts = 60 // 5 minutes with 5s intervals
    let attempts = 0

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setError('Task timeout - please check backend logs')
        setStatus('FAILED')
        return
      }

      try {
        const task = await pollTaskStatus(taskId)

        if (task.status === 'completed') {
          setStatus('COMPLETE')
          setResult({
            success: true,
            data: task.result,
            report: 'Task completed successfully',
          })
          return
        } else if (task.status === 'failed') {
          setStatus('FAILED')
          setResult({
            success: false,
            error: 'Task execution failed',
          })
          return
        } else if (task.status === 'in_progress' || task.status === 'assigned') {
          const storeStatus = useTaskStore.getState().status
          if (storeStatus !== 'EXECUTING' && storeStatus !== 'VERIFYING') {
            setStatus('EXECUTING')
            addExecutionLog({
              timestamp: new Date().toLocaleTimeString(),
              message: 'Task execution started',
              source: 'executor',
            })
          }
        }

        attempts++
        setTimeout(poll, 5000)
      } catch (error: any) {
        console.error('Error polling task:', error)
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000)
        } else {
          setError('Failed to get task status')
          setStatus('FAILED')
        }
      }
    }

    poll()
  }

  // Handle plan approval
  const handleApprovePlan = async () => {
    if (!taskId) return

    try {
      setStatus('NEGOTIATING')
      addExecutionLog({
        timestamp: new Date().toLocaleTimeString(),
        message: 'Finding suitable agent...',
        source: 'negotiator',
      })

      setTimeout(() => {
        const mockAgent = {
          agentId: 'databot_v3',
          name: 'DataBot_v3',
          description: 'AI agent specialized in data analysis',
          reputation: 4.8,
          price: 4.5,
          currency: 'USDC',
          capabilities: ['Python data analysis', 'CSV ingestion', 'Statistical analysis'],
        }

        setSelectedAgent(mockAgent)
        setPaymentDetails({
          paymentId: `payment_${Date.now()}`,
          amount: 4.5,
          currency: 'USDC',
          fromAccount: 'user_wallet',
          toAccount: mockAgent.agentId,
          agentName: mockAgent.name,
          description: `Task execution payment for ${mockAgent.name}`,
        })

        addExecutionLog({
          timestamp: new Date().toLocaleTimeString(),
          message: `Agent found: ${mockAgent.name} (${mockAgent.reputation} stars) for $${mockAgent.price}`,
          source: 'negotiator',
        })
      }, 2000)
    } catch (error: any) {
      console.error('Error approving plan:', error)
      setError(error.message || 'Failed to approve plan')
      setStatus('FAILED')
    }
  }

  const statusIndicatorClass =
    status === 'FAILED'
      ? 'bg-red-400'
      : status === 'COMPLETE'
        ? 'bg-emerald-400'
        : 'bg-sky-400 animate-pulse'

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="relative">
        <main className="mx-auto flex max-w-6xl flex-col gap-20 px-6 pb-24 pt-12 lg:pt-16">
          <header className="flex flex-col gap-12">
            <nav className="flex flex-wrap items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 via-indigo-500 to-purple-600 text-lg font-bold text-white shadow-lg shadow-sky-500/40">
                  PA
                </div>
                <div>
                  <p className="text-xl font-semibold text-white">ProvidAI</p>
                  <p className="text-sm text-slate-300">AI research assistant powered by specialized agents and microtransactions</p>
                </div>
              </div>
            </nav>

            <div className="w-full">
              <div id="task-console" className="relative">
                <div className="absolute inset-0 rounded-[28px] bg-gradient-to-br from-sky-500/15 via-transparent to-purple-600/20 blur-2xl" />
                <div className="relative overflow-hidden rounded-[28px] border border-white/20 bg-slate-900/75 p-6 shadow-[0_45px_90px_-50px_rgba(56,189,248,0.9)] backdrop-blur-xl">
                  <Tabs
                    activeTab={activeTab}
                    onTabChange={setActiveTab}
                    tabs={[
                      {
                        id: 'console',
                        label: 'Research Console',
                        content: (
                          <>
                            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                              <span className="text-xs uppercase tracking-[0.4em] text-slate-400">Live research status</span>
                              <span className="flex items-center gap-2 text-sm text-slate-300">
                                <span className={`inline-flex h-2.5 w-2.5 rounded-full ${statusIndicatorClass}`} />
                                {statusMessages[status]}
                              </span>
                            </div>

                            <div className="space-y-6">
                              <div className="rounded-2xl border border-white/15 bg-white/95 p-1 text-slate-900 shadow-[0_30px_80px_-45px_rgba(59,130,246,0.7)]">
                                {(status === 'IDLE' || status === 'FAILED') ? (
                                  <TaskForm onSubmit={handleStartTask} />
                                ) : (
                                  <TaskStatusCard />
                                )}
                              </div>

                              {status === 'APPROVING_PLAN' && (
                                <div className="rounded-2xl border border-sky-500/40 bg-sky-900/40 p-6 text-slate-100 shadow-[0_25px_60px_-35px_rgba(56,189,248,0.8)]">
                                  <h3 className="text-lg font-semibold text-white">Approve research plan</h3>
                                  <p className="mt-2 text-sm leading-relaxed text-slate-200">
                                    Review the methodology, data sources, and cost. We'll match you with the best research specialist.
                                  </p>
                                  <Button
                                    onClick={handleApprovePlan}
                                    className="mt-4 w-full bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 text-white shadow-lg shadow-sky-500/30 transition hover:opacity-90"
                                    disabled={isProcessing}
                                  >
                                    Approve & start research
                                  </Button>
                                </div>
                              )}

                              {(status === 'COMPLETE' || status === 'FAILED') && (
                                <div className="space-y-4">
                                  <div className="rounded-2xl border border-white/15 bg-white/95 p-1 text-slate-900 shadow-[0_30px_80px_-45px_rgba(59,130,246,0.7)]">
                                    <TaskResults />
                                  </div>
                                  <Button
                                    onClick={reset}
                                    variant="outline"
                                    className="w-full border-slate-200 bg-white/10 text-white transition hover:bg-white/20"
                                  >
                                    Start new research
                                  </Button>
                                </div>
                              )}

                              {description && (
                                <div className="rounded-2xl border border-white/15 bg-white/5 p-5 text-slate-200">
                                  <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Research query</div>
                                  <p className="mt-2 text-sm leading-relaxed text-slate-100">
                                    {description}
                                  </p>
                                </div>
                              )}
                            </div>

                            <PaymentModal />
                          </>
                        ),
                      },
                      {
                        id: 'transactions',
                        label: 'Transaction History',
                        content: <Transactions />,
                      },
                      {
                        id: 'marketplace',
                        label: 'Agent Marketplace',
                        content: <Marketplace />,
                      },
                    ]}
                  />
                </div>
              </div>
            </div>
          </header>

        </main>

        <footer className="border-t border-white/10 py-8 text-center text-sm text-slate-400">
          ProvidAI | Powered by Hedera, ERC-8004 reputation, and x402 settlement.
        </footer>
      </div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { HederaInfo } from '@/components/HederaInfo'
import { TaskForm } from '@/components/TaskForm'
import { TaskStatusCard } from '@/components/TaskStatusCard'
import { PaymentModal } from '@/components/PaymentModal'
import { TaskResults } from '@/components/TaskResults'
import { useTaskStore } from '@/store/taskStore'
import type { TaskStatus } from '@/store/taskStore'
import type { LucideIcon } from 'lucide-react'
import { Sparkles, ShieldCheck, Coins, ArrowRight, Cpu, Globe, Layers } from 'lucide-react'
import { createTask, pollTaskStatus } from '@/lib/api'
import { Button } from '@/components/ui/button'

const statusMessages: Record<TaskStatus, string> = {
  IDLE: 'Awaiting your next mission',
  PLANNING: 'Drafting orchestrator plan',
  APPROVING_PLAN: 'Plan ready for approval',
  NEGOTIATING: 'Pairing with the right agent',
  PAYING: 'Processing on Hedera testnet',
  EXECUTING: 'Agent is delivering',
  VERIFYING: 'Verifier is validating output',
  COMPLETE: 'Completed with verifier approval',
  FAILED: 'Action required - flow interrupted',
}

const heroStats = [
  { value: '4.8 / 5', label: 'Average agent rating (testnet)' },
  { value: '120+', label: 'Specialist agents curated' },
  { value: '~6 min', label: 'Median time to verified results' },
]

const featureHighlights: Array<{ title: string; description: string; icon: LucideIcon }> = [
  {
    title: 'Composable agent mesh',
    description: 'Blend orchestrators, executors, and verifiers into repeatable playbooks that stay audit-ready.',
    icon: Cpu,
  },
  {
    title: 'On-chain trust rails',
    description: 'ERC-8004 reputation and escrowed payments on Hedera keep incentives aligned from kickoff to delivery.',
    icon: ShieldCheck,
  },
  {
    title: 'Global intelligence layer',
    description: 'Source vetted specialists across data, growth, and ops with built-in negotiation and verification.',
    icon: Globe,
  },
]

const flowSteps: Array<{ badge: string; title: string; description: string; icon: LucideIcon }> = [
  {
    badge: 'STEP 01',
    title: 'Describe your objective',
    description:
      'Drop a business goal or dataset. Providence agents map the requirements and break it into verifiable subtasks.',
    icon: Sparkles,
  },
  {
    badge: 'STEP 02',
    title: 'Approve an orchestrated plan',
    description:
      'Review the automatically generated plan, capabilities, and projected spend before committing a single credit.',
    icon: Layers,
  },
  {
    badge: 'STEP 03',
    title: 'Select & fund the specialist',
    description:
      'Negotiator agents source the optimal specialist by reputation, cost, and fit, then escrow payment on Hedera.',
    icon: Coins,
  },
  {
    badge: 'STEP 04',
    title: 'Receive verified output',
    description:
      'Execution is monitored in real time and verified agents sign off before releasing funds back to the specialist.',
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
      <div className="pointer-events-none absolute inset-x-[-20%] top-[-30%] h-[520px] rounded-full bg-[radial-gradient(circle_at_top,_rgba(76,106,255,0.25),_rgba(15,23,42,0))]" />
      <div className="pointer-events-none absolute bottom-[-25%] left-1/2 h-[480px] w-[480px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,_rgba(12,74,110,0.4),_rgba(15,23,42,0))]" />

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
                  <p className="text-sm text-slate-300">Agent marketplace built on Hedera trust primitives</p>
                </div>
              </div>
            </nav>

            <div className="flex justify-center">
              <div id="task-console" className="relative">
                <div className="absolute inset-0 rounded-[28px] bg-gradient-to-br from-sky-500/15 via-transparent to-purple-600/20 blur-2xl" />
                <div className="relative overflow-hidden rounded-[28px] border border-white/20 bg-slate-900/75 p-6 shadow-[0_45px_90px_-50px_rgba(56,189,248,0.9)] backdrop-blur-xl">
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-6">
                    <span className="text-xs uppercase tracking-[0.4em] text-slate-400">Live agent console</span>
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
                        <h3 className="text-lg font-semibold text-white">Approve plan & activate agent</h3>
                        <p className="mt-2 text-sm leading-relaxed text-slate-200">
                          Review the proposed plan and confirm to let ProvidAI negotiate the best specialist for you.
                        </p>
                        <Button
                          onClick={handleApprovePlan}
                          className="mt-4 w-full bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 text-white shadow-lg shadow-sky-500/30 transition hover:opacity-90"
                          disabled={isProcessing}
                        >
                          Approve plan & find agent
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
                          Start new task
                        </Button>
                      </div>
                    )}

                    {description && (
                      <div className="rounded-2xl border border-white/15 bg-white/5 p-5 text-slate-200">
                        <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Current brief</div>
                        <p className="mt-2 text-sm leading-relaxed text-slate-100">
                          {description}
                        </p>
                      </div>
                    )}
                  </div>

                  <PaymentModal />
                </div>
              </div>
            </div>
          </header>

          <section className="space-y-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-3xl font-semibold text-white">Why teams choose ProvidAI</h2>
                <p className="mt-2 max-w-xl text-sm text-slate-300">
                  Bring orchestrated experts into your stack with auditability and compliance baked in from the first task.
                </p>
              </div>
              <span className="text-xs uppercase tracking-[0.3em] text-slate-400">
                Built for data, ops, and growth teams
              </span>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              {featureHighlights.map((feature) => (
                <div
                  key={feature.title}
                  className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-6 shadow-[0_35px_80px_-50px_rgba(125,211,252,0.5)] transition hover:-translate-y-1 hover:border-sky-400/60 hover:shadow-sky-500/40"
                >
                  <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500/20 via-indigo-500/30 to-purple-600/30 text-sky-100">
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-300">{feature.description}</p>
                  <div className="pointer-events-none absolute -right-12 top-1/2 h-32 w-32 -translate-y-1/2 rounded-full bg-sky-500/10 blur-3xl transition group-hover:scale-110" />
                </div>
              ))}
            </div>
          </section>

          <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-slate-900/80 via-slate-900/50 to-slate-900/20 p-8 shadow-[0_45px_90px_-50px_rgba(59,130,246,0.7)]">
            <div className="pointer-events-none absolute -left-16 top-10 h-48 w-48 rounded-full bg-sky-500/20 blur-3xl" />
            <div className="pointer-events-none absolute -right-20 bottom-10 h-56 w-56 rounded-full bg-purple-600/20 blur-3xl" />

            <div className="relative z-10 grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-start">
              <div className="space-y-4">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-slate-300">
                  Proven workflow
                </span>
                <h2 className="text-3xl font-semibold text-white">
                  From idea to verified result - all inside one orchestrated flow.
                </h2>
                <p className="text-sm text-slate-300">
                  We combine orchestrators, negotiators, executors, and verifiers so every run ships with the right
                  specialist, transparent economics, and provable quality.
                </p>
              </div>

              <div className="space-y-4">
                {flowSteps.map((step) => (
                  <div
                    key={step.title}
                    className="relative flex gap-4 rounded-2xl border border-white/15 bg-white/5 p-5 text-slate-200 backdrop-blur transition hover:border-sky-400/40 hover:bg-white/10"
                  >
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-950/40 text-sky-200">
                      <step.icon className="h-6 w-6" />
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-[0.3em] text-slate-400">{step.badge}</div>
                      <h3 className="text-lg font-semibold text-white">{step.title}</h3>
                      <p className="mt-1 text-sm text-slate-300">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-white/10 py-8 text-center text-sm text-slate-400">
          ProvidAI | Powered by Hedera, ERC-8004 reputation, and x402 settlement.
        </footer>
      </div>
    </div>
  )
}

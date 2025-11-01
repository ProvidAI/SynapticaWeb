'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTaskStore } from '@/store/taskStore'
import { Send, DollarSign } from 'lucide-react'

interface TaskFormProps {
  onSubmit: (description: string, budget: number) => void
}

export function TaskForm({ onSubmit }: TaskFormProps) {
  const [description, setDescription] = useState('')
  const [budget, setBudget] = useState('100')
  const { setDescription: setTaskDescription, status } = useTaskStore()

  const handleSubmit = () => {
    if (!description.trim()) {
      alert('Please enter a task description')
      return
    }

    const budgetValue = parseFloat(budget)
    if (isNaN(budgetValue) || budgetValue <= 0) {
      alert('Please enter a valid budget amount')
      return
    }

    setTaskDescription(description)
    onSubmit(description, budgetValue)
  }

  const isDisabled = status !== 'IDLE' && status !== 'FAILED'

  return (
    <Card className="relative overflow-hidden rounded-3xl border border-white/40 bg-white/95 shadow-[0_30px_80px_-45px_rgba(59,130,246,0.5)] transition">
      <div className="pointer-events-none absolute -left-16 top-[-40px] h-48 w-48 rounded-full bg-sky-200/45 blur-3xl" />
      <div className="pointer-events-none absolute -right-20 bottom-[-60px] h-56 w-56 rounded-full bg-indigo-200/40 blur-3xl" />
      <CardHeader className="relative z-10 space-y-4 pb-0">
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-sky-100 bg-sky-50/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.35em] text-sky-600">
          Task intake
        </span>
        <div className="space-y-2">
          <CardTitle className="text-3xl font-semibold text-slate-900">Create new task</CardTitle>
          <CardDescription className="text-base leading-relaxed text-slate-500">
            Describe the target outcome and any guardrails. ProvidAI will draft a plan before anything is executed.
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="relative z-10 space-y-6 pt-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm font-medium text-slate-600">
            <span>Task description</span>
            <span className="text-xs font-normal uppercase tracking-[0.35em] text-slate-400">Required</span>
          </div>
          <Textarea
            id="description"
            placeholder="Example: Audit the growth dashboard, highlight anomalous KPIs, and suggest next experiments."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isDisabled}
            rows={7}
            className="min-h-[150px] resize-none rounded-2xl border-slate-200/70 bg-white/90 px-4 py-3 text-slate-700 shadow-inner transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-300/40 disabled:opacity-60"
          />
          <p className="text-xs text-slate-400">
            Tip: include data sources, success criteria, and delivery format so the orchestrator can price the work accurately.
          </p>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm font-medium text-slate-600">
            <span className="flex items-center gap-2">
              <DollarSign className="h-4 w-4" />
              Budget limit (USD)
            </span>
            <span className="text-xs font-normal uppercase tracking-[0.35em] text-slate-400">Required</span>
          </div>
          <Input
            type="number"
            id="budget"
            placeholder="100"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            disabled={isDisabled}
            min="0.01"
            step="0.01"
            className="rounded-2xl border-slate-200/70 bg-white/90 px-4 py-3 text-slate-700 shadow-inner transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-300/40 disabled:opacity-60"
          />
          <p className="text-xs text-slate-400">
            Maximum amount to spend on this research task. Agents will be selected to fit within this budget.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200/60 pt-4 text-xs text-slate-400">
          <span>ProvidAI drafts a plan and cost estimate before you approve an agent.</span>
          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !description.trim()}
            className="w-full rounded-full bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 px-6 py-5 text-sm font-semibold shadow-lg shadow-sky-500/30 transition hover:opacity-90 disabled:cursor-not-allowed sm:w-auto sm:min-w-[160px]"
          >
            <Send className="mr-2 h-4 w-4" />
            Start task
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

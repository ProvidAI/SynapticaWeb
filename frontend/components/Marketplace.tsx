'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Search,
  ExternalLink,
  Mail,
  RefreshCcw,
  Tag,
  AlertCircle,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { AddAgentModal } from '@/components/AddAgentModal'
import {
  AgentRecord,
  AgentSubmissionResponse,
  fetchAgents,
} from '@/lib/api'
import { cn } from '@/lib/utils'


function formatPrice(pricing: AgentRecord['pricing']): string {
  const rate = pricing.rate?.toString() ?? '0'
  return `${rate} ${pricing.currency}${pricing.rate_type ? ` • ${pricing.rate_type.replace(/_/g, ' ')}` : ''}`
}

interface AgentCardProps {
  agent: AgentRecord
  highlight?: boolean
}

function AgentCard({ agent, highlight }: AgentCardProps) {
  return (
    <div
      className={cn(
        'relative flex flex-col gap-4 rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-[0_20px_60px_-40px_rgba(56,189,248,0.6)] transition hover:border-sky-500/50 hover:shadow-[0_25px_70px_-40px_rgba(56,189,248,0.8)]',
        highlight && 'border-emerald-400/60 shadow-[0_20px_60px_-35px_rgba(16,185,129,0.8)]'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
            <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 text-xs font-semibold uppercase tracking-[0.35em] text-emerald-300">
              {agent.status}
            </span>
          </div>
          <p className="mt-2 line-clamp-3 text-sm text-slate-300">{agent.description}</p>
        </div>
        {agent.logo_url && (
          <img
            src={agent.logo_url}
            alt={`${agent.name} logo`}
            className="h-12 w-12 rounded-full border border-white/20 object-cover"
          />
        )}
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        {agent.categories.length
          ? agent.categories.map((category) => (
              <span
                key={category}
                className="inline-flex items-center gap-1 rounded-full border border-white/20 px-3 py-1 text-slate-200"
              >
                <Tag className="h-3 w-3" />
                {category}
              </span>
            ))
          : (
            <span className="inline-flex items-center gap-1 rounded-full border border-white/20 px-3 py-1 text-slate-200">
              <Tag className="h-3 w-3" />
              General
            </span>
          )}
      </div>

      <div>
        <h4 className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
          Capabilities
        </h4>
        <ul className="mt-2 grid gap-1 text-sm text-slate-200">
          {agent.capabilities.slice(0, 4).map((capability) => (
            <li key={capability} className="flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />
              <span>{capability}</span>
            </li>
          ))}
          {agent.capabilities.length > 4 && (
            <li className="text-xs text-slate-400">
              + {agent.capabilities.length - 4} more
            </li>
          )}
        </ul>
      </div>

      <div className="grid gap-2 text-sm text-slate-300">
        <div>
          <span className="font-medium text-slate-100">Pricing: </span>
          {formatPrice(agent.pricing)}
        </div>
        {agent.contact_email && (
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-slate-400" />
            <a
              href={`mailto:${agent.contact_email}`}
              className="text-sky-400 hover:text-sky-200"
            >
              {agent.contact_email}
            </a>
          </div>
        )}
        {agent.metadata_gateway_url && (
          <div className="flex items-center gap-2">
            <ExternalLink className="h-4 w-4 text-slate-400" />
            <a
              href={agent.metadata_gateway_url}
              target="_blank"
              rel="noreferrer"
              className="text-sky-400 hover:text-sky-200"
            >
              Metadata
            </a>
          </div>
        )}
      </div>

      {agent.endpoint_url && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-xs text-slate-300">
          <p className="font-medium text-slate-100">Endpoint</p>
          <p className="mt-1 break-all text-[11px] text-slate-400">{agent.endpoint_url}</p>
        </div>
      )}
    </div>
  )
}

export function Marketplace() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [recentAgentId, setRecentAgentId] = useState<string | null>(null)

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    refetchOnWindowFocus: false,
  })

  const agents = data?.agents ?? []

  const categories = useMemo(() => {
    const unique = new Set<string>()
    agents.forEach((agent) => {
      agent.categories.forEach((category) => unique.add(category))
    })
    return ['All', ...Array.from(unique)]
  }, [agents])

  const filteredAgents = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    return agents.filter((agent) => {
      const matchesCategory =
        selectedCategory === 'All' ||
        agent.categories.includes(selectedCategory)

      if (!matchesCategory) {
        return false
      }

      if (!query) {
        return true
      }

      const haystack = [
        agent.name,
        agent.agent_id,
        agent.description ?? '',
        ...agent.capabilities,
        ...agent.categories,
      ]
        .join(' ')
        .toLowerCase()

      return haystack.includes(query)
    })
  }, [agents, searchQuery, selectedCategory])

  const handleAgentCreated = (agent: AgentSubmissionResponse) => {
    setRecentAgentId(agent.agent_id)
    setSearchQuery('')
    setSelectedCategory('All')
    queryClient.invalidateQueries({ queryKey: ['agents'] })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white">Agent Marketplace</h2>
          <p className="mt-1 text-sm text-slate-400">
            Discover specialist agents ready to plug into your workflows.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            className="flex items-center gap-2 rounded-full px-4 py-2 text-sm text-slate-200 hover:text-white"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? <Spinner size={16} /> : <RefreshCcw className="h-4 w-4" />}
            Refresh
          </Button>
          <AddAgentModal onSuccess={handleAgentCreated} />
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            className="w-full rounded-2xl border border-white/10 bg-slate-900/80 py-3 pl-12 pr-4 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/40"
            placeholder="Search agents by name, capability, or category..."
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {categories.map((category) => (
            <button
              key={category}
              className={cn(
                'rounded-full border border-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-slate-300 transition hover:border-sky-500/40 hover:text-white',
                selectedCategory === category && 'border-sky-500/60 bg-sky-500/10 text-white'
              )}
              onClick={() => setSelectedCategory(category)}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center rounded-3xl border border-white/10 bg-slate-950/70 py-16">
          <Spinner size={28} className="text-sky-400" />
        </div>
      ) : isError ? (
        <div className="flex items-center gap-3 rounded-3xl border border-rose-500/40 bg-rose-500/10 p-6 text-sm text-rose-200">
          <AlertCircle className="h-5 w-5" />
          <div>
            <p className="font-semibold">Failed to load agents.</p>
            <p className="text-rose-100">
              {(error as Error)?.message ?? 'Please try again later.'}
            </p>
          </div>
        </div>
      ) : filteredAgents.length === 0 ? (
        <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-10 text-center text-sm text-slate-300">
          No agents match your current filters.
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
          {filteredAgents.map((agent) => (
            <AgentCard
              key={agent.agent_id}
              agent={agent}
              highlight={recentAgentId === agent.agent_id}
            />
          ))}
        </div>
      )}
    </div>
  )
}

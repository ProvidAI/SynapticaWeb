'use client'

import { useEffect, useMemo, useState } from 'react'
import { Search, Star, TrendingUp, Database, BarChart3, Globe, FileText, MessageSquare, Code, Brain, Bot, ChevronDown } from 'lucide-react'
import { getAgents, type AgentSummary } from '@/lib/api'

type IconType = typeof Database

const typeToIcon: Record<string, IconType> = {
  data: Database,
  stats: BarChart3,
  nlp: MessageSquare,
  market: TrendingUp,
  report: FileText,
  ml: Brain,
  code: Code,
  web: Globe,
}

export function Marketplace() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [showAllTags, setShowAllTags] = useState<boolean>(false)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    getAgents()
      .then((data) => {
        if (mounted) setAgents(Array.isArray(data) ? data : [])
      })
      .catch((e) => {
        if (mounted) setError(e?.message || 'Failed to load agents')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const categories = useMemo(() => {
    const set = new Set<string>()
    agents.forEach((a) => a.capabilities?.forEach((c) => set.add(c)))
    return ['All', ...Array.from(set).sort()]
  }, [agents])

  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      const matchesSearch =
        searchQuery === '' ||
        agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.capabilities.some((c) => c.toLowerCase().includes(searchQuery.toLowerCase()))

      const matchesCategory = selectedCategory === 'All' || agent.capabilities.includes(selectedCategory)

      return matchesSearch && matchesCategory
    })
  }, [agents, searchQuery, selectedCategory])

  const handleSelectCategory = (category: string) => {
    setSelectedCategory(category)
    // Keep drawer open when browsing; close on selection if not "All"
    if (category !== 'All') setShowAllTags(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-white">Agent Marketplace</h2>
        <p className="mt-1 text-sm text-slate-400">
          Browse {agents.length} registered agents
        </p>
      </div>

      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search agents by name or capability..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-white/15 bg-slate-900/50 py-3 pl-12 pr-4 text-white placeholder-slate-400 backdrop-blur-sm transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/20"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowAllTags((v) => !v)}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-800/60 px-3 py-2 text-sm text-slate-200 ring-1 ring-white/10 transition hover:bg-slate-800"
            aria-expanded={showAllTags}
            aria-controls="all-tags-accordion"
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${showAllTags ? 'rotate-180' : ''}`} />
            All tags
            <span className="ml-1 rounded-md bg-slate-700/70 px-1.5 py-0.5 text-xs text-slate-300">
              {Math.max(categories.length - 1, 0)}
            </span>
          </button>
        </div>

        {showAllTags && (
          <div
            id="all-tags-accordion"
            className="rounded-xl border border-white/15 bg-slate-900/60 p-3 backdrop-blur-sm"
          >
            <div className="max-h-56 overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
                {categories
                  .filter((c) => c !== 'All')
                  .map((category) => (
                    <button
                      key={category}
                      onClick={() => handleSelectCategory(category)}
                      className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm transition ${
                        selectedCategory === category
                          ? 'bg-sky-500 text-white'
                          : 'bg-slate-800/50 text-slate-300 hover:bg-slate-800 hover:text-white'
                      }`}
                      title={category}
                    >
                      {category}
                    </button>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div className="rounded-2xl border border-white/15 bg-slate-900/50 p-6 text-center text-slate-400">
          Loading agents...
        </div>
      )}
      {error && !loading && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-6 text-center text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {!loading && !error && filteredAgents.map((agent) => {
          const mapped = agent.agent_type?.toLowerCase?.() || ''
          const IconComponent = typeToIcon[mapped] || (Bot as IconType)
          return (
            <div
              key={agent.agent_id}
              className="group overflow-hidden rounded-2xl border border-white/15 bg-slate-900/50 backdrop-blur-sm transition hover:border-sky-400/50 hover:bg-slate-900/70"
            >
              <div className="p-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500/20 via-indigo-500/20 to-purple-600/20 text-sky-400 ring-1 ring-white/10">
                    <IconComponent className="h-7 w-7" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                    <p className="text-sm text-sky-400">{agent.agent_type}</p>
                  </div>
                </div>

                <p className="mt-4 text-sm leading-relaxed text-slate-300">
                  {agent.description}
                </p>

                <div className="mt-4 flex flex-wrap gap-2">
                  {agent.capabilities.map((capability) => (
                    <span
                      key={capability}
                      className="rounded-lg bg-slate-800/50 px-2.5 py-1 text-xs text-slate-300"
                    >
                      {capability}
                    </span>
                  ))}
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                      <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      <span className="font-medium text-white">—</span>
                    </div>
                    <div className="text-slate-400">
                      —
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold text-white">
                      —
                    </div>
                    <div className="text-xs text-slate-400">per task</div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {!loading && !error && filteredAgents.length === 0 && (
        <div className="rounded-2xl border border-white/15 bg-slate-900/50 p-12 text-center">
          <p className="text-slate-400">No agents found matching your criteria</p>
          <p className="mt-2 text-sm text-slate-500">
            Try adjusting your search or filter settings
          </p>
        </div>
      )}
    </div>
  )
}

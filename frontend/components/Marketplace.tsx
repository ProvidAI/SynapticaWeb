'use client'

import { useState } from 'react'
import { Search, Star, TrendingUp, Database, BarChart3, Globe, FileText, MessageSquare, Code, Brain } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Agent {
  id: string
  name: string
  category: string
  description: string
  capabilities: string[]
  pricePerTask: number
  reputation: number
  totalTasks: number
  specialty: string
  icon: any
}

// Mock marketplace data
const mockAgents: Agent[] = [
  {
    id: 'agent_001',
    name: 'DataCollector_v2',
    category: 'Data Collection',
    description: 'High-performance web scraper and API integrator specialized in collecting structured data from multiple sources.',
    capabilities: ['Web Scraping', 'API Integration', 'Data Cleaning', 'CSV/JSON Export'],
    pricePerTask: 3.00,
    reputation: 4.9,
    totalTasks: 1247,
    specialty: 'E-commerce & Financial Data',
    icon: Database,
  },
  {
    id: 'agent_002',
    name: 'StatsAnalyzer_Pro',
    category: 'Statistical Analysis',
    description: 'Advanced statistical analysis agent with expertise in hypothesis testing, regression, and predictive modeling.',
    capabilities: ['Statistical Testing', 'Regression Analysis', 'Time Series', 'Correlation Studies'],
    pricePerTask: 4.50,
    reputation: 4.8,
    totalTasks: 892,
    specialty: 'Quantitative Research',
    icon: BarChart3,
  },
  {
    id: 'agent_003',
    name: 'SentimentAI_Pro',
    category: 'NLP & Sentiment',
    description: 'Natural language processing specialist for sentiment analysis, entity extraction, and text classification.',
    capabilities: ['Sentiment Analysis', 'Entity Recognition', 'Topic Modeling', 'Text Classification'],
    pricePerTask: 7.00,
    reputation: 4.9,
    totalTasks: 2156,
    specialty: 'Social Media & Reviews',
    icon: MessageSquare,
  },
  {
    id: 'agent_004',
    name: 'MarketIntel_v5',
    category: 'Market Research',
    description: 'Comprehensive market intelligence agent for competitive analysis, market sizing, and trend forecasting.',
    capabilities: ['Market Sizing', 'Competitive Analysis', 'Trend Forecasting', 'Industry Reports'],
    pricePerTask: 8.50,
    reputation: 4.7,
    totalTasks: 634,
    specialty: 'B2B & SaaS Markets',
    icon: TrendingUp,
  },
  {
    id: 'agent_005',
    name: 'ReportGen_v3',
    category: 'Report Generation',
    description: 'Automated report generation with data visualization, executive summaries, and actionable insights.',
    capabilities: ['PDF Reports', 'Data Visualization', 'Executive Summaries', 'Custom Templates'],
    pricePerTask: 5.00,
    reputation: 4.7,
    totalTasks: 1543,
    specialty: 'Business Intelligence',
    icon: FileText,
  },
  {
    id: 'agent_006',
    name: 'WebScraper_Elite',
    category: 'Data Collection',
    description: 'Enterprise-grade web scraping with JavaScript rendering, CAPTCHA handling, and proxy rotation.',
    capabilities: ['JS Rendering', 'CAPTCHA Bypass', 'Proxy Support', 'Rate Limiting'],
    pricePerTask: 2.75,
    reputation: 4.6,
    totalTasks: 987,
    specialty: 'Complex Web Sources',
    icon: Globe,
  },
  {
    id: 'agent_007',
    name: 'CodeAnalyzer_AI',
    category: 'Code Analysis',
    description: 'Source code analysis for quality metrics, security vulnerabilities, and technical debt assessment.',
    capabilities: ['Code Quality', 'Security Scan', 'Dependency Analysis', 'Technical Debt'],
    pricePerTask: 6.50,
    reputation: 4.8,
    totalTasks: 445,
    specialty: 'Software Engineering',
    icon: Code,
  },
  {
    id: 'agent_008',
    name: 'MLPredictor_v4',
    category: 'Machine Learning',
    description: 'Machine learning agent for predictive modeling, classification, and anomaly detection tasks.',
    capabilities: ['Predictive Models', 'Classification', 'Anomaly Detection', 'Feature Engineering'],
    pricePerTask: 9.00,
    reputation: 4.9,
    totalTasks: 723,
    specialty: 'Predictive Analytics',
    icon: Brain,
  },
  {
    id: 'agent_009',
    name: 'CompAnalyzer_v4',
    category: 'Competitive Intelligence',
    description: 'Deep competitive intelligence gathering with product comparison, pricing analysis, and strategic positioning.',
    capabilities: ['Product Comparison', 'Pricing Analysis', 'Feature Mapping', 'Strategic Insights'],
    pricePerTask: 6.00,
    reputation: 4.8,
    totalTasks: 558,
    specialty: 'Product Strategy',
    icon: TrendingUp,
  },
  {
    id: 'agent_010',
    name: 'SocialScraper_v5',
    category: 'Social Media',
    description: 'Multi-platform social media data collection including posts, comments, metrics, and engagement data.',
    capabilities: ['Multi-Platform', 'Engagement Metrics', 'Hashtag Tracking', 'Influencer Analysis'],
    pricePerTask: 4.00,
    reputation: 4.9,
    totalTasks: 1876,
    specialty: 'Social Listening',
    icon: MessageSquare,
  },
  {
    id: 'agent_011',
    name: 'InsightGen_v2',
    category: 'Data Visualization',
    description: 'Transform raw data into interactive dashboards, charts, and data stories for stakeholder presentations.',
    capabilities: ['Interactive Dashboards', 'Custom Charts', 'Data Stories', 'Export Formats'],
    pricePerTask: 4.00,
    reputation: 4.5,
    totalTasks: 967,
    specialty: 'Data Presentation',
    icon: BarChart3,
  },
  {
    id: 'agent_012',
    name: 'FinancialAnalyzer_Pro',
    category: 'Financial Analysis',
    description: 'Financial data analysis including P&L modeling, ratio analysis, and investment research.',
    capabilities: ['Financial Modeling', 'Ratio Analysis', 'Valuation', 'Risk Assessment'],
    pricePerTask: 8.00,
    reputation: 4.9,
    totalTasks: 412,
    specialty: 'Corporate Finance',
    icon: TrendingUp,
  },
]

const categories = ['All', 'Data Collection', 'Statistical Analysis', 'NLP & Sentiment', 'Market Research', 'Report Generation', 'Machine Learning']

export function Marketplace() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')

  const filteredAgents = mockAgents.filter((agent) => {
    const matchesSearch =
      searchQuery === '' ||
      agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      agent.specialty.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesCategory = selectedCategory === 'All' || agent.category === selectedCategory

    return matchesSearch && matchesCategory
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold text-white">Agent Marketplace</h2>
        <p className="mt-1 text-sm text-slate-400">
          Browse {mockAgents.length} specialized research agents ready to assist with your queries
        </p>
      </div>

      {/* Search and Filter */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search agents by name, capability, or specialty..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-white/15 bg-slate-900/50 py-3 pl-12 pr-4 text-white placeholder-slate-400 backdrop-blur-sm transition focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/20"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                selectedCategory === category
                  ? 'bg-sky-500 text-white'
                  : 'bg-slate-800/50 text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {filteredAgents.map((agent) => {
          const IconComponent = agent.icon
          return (
            <div
              key={agent.id}
              className="group overflow-hidden rounded-2xl border border-white/15 bg-slate-900/50 backdrop-blur-sm transition hover:border-sky-400/50 hover:bg-slate-900/70"
            >
              <div className="p-6">
                {/* Agent Header */}
                <div className="flex items-start gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500/20 via-indigo-500/20 to-purple-600/20 text-sky-400 ring-1 ring-white/10">
                    <IconComponent className="h-7 w-7" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                    <p className="text-sm text-sky-400">{agent.category}</p>
                  </div>
                </div>

                {/* Description */}
                <p className="mt-4 text-sm leading-relaxed text-slate-300">
                  {agent.description}
                </p>

                {/* Specialty */}
                <div className="mt-4">
                  <span className="inline-flex items-center rounded-full bg-purple-500/10 px-3 py-1 text-xs font-medium text-purple-400 ring-1 ring-purple-400/20">
                    {agent.specialty}
                  </span>
                </div>

                {/* Capabilities */}
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

                {/* Stats and Price */}
                <div className="mt-6 flex items-center justify-between border-t border-white/10 pt-4">
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1.5">
                      <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      <span className="font-medium text-white">{agent.reputation}</span>
                    </div>
                    <div className="text-slate-400">
                      {agent.totalTasks.toLocaleString()} tasks
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold text-white">
                      ${agent.pricePerTask.toFixed(2)}
                    </div>
                    <div className="text-xs text-slate-400">per task</div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Empty State */}
      {filteredAgents.length === 0 && (
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

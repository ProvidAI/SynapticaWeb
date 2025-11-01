'use client'

export function HederaInfo() {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
      <div className="flex flex-col">
        <div className="text-sm font-semibold text-purple-900">Hedera Testnet</div>
        <div className="text-xs text-purple-600">Powered by Hedera Hashgraph</div>
      </div>
    </div>
  )
}


interface TokenUsageBadgeProps {
  tokens?: number
  modelName?: string
}

export default function TokenUsageBadge({ tokens = 0, modelName }: TokenUsageBadgeProps) {
  if (tokens <= 0) return null
  return (
    <div className="mt-2 flex items-center gap-2 text-xs text-gray-500" aria-label="模型用量">
      <span>{tokens.toLocaleString()} tokens</span>
      {modelName && <span>· {modelName}</span>}
    </div>
  )
}

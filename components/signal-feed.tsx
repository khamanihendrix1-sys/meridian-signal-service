import { Radio, Zap } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/ui/feedback"
import { cn, formatRelativeTime } from "@/lib/utils"
import type { SignalLogResponse } from "@/lib/types"

export function SignalFeed({ logs }: { logs: SignalLogResponse[] }) {
  if (!logs.length) {
    return (
      <EmptyState
        title="No recent signal activity"
        description="Signal evaluations for the selected scope will appear here as they run."
      />
    )
  }

  return (
    <ul className="divide-y divide-border">
      {logs.map((log) => (
        <li key={log.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
          <div
            className={cn(
              "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full",
              log.fired
                ? "bg-accent/20 text-accent-foreground"
                : "bg-muted text-muted-foreground",
            )}
          >
            {log.fired ? (
              <Zap className="size-4" aria-hidden="true" />
            ) : (
              <Radio className="size-4" aria-hidden="true" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-foreground">{log.geography}</p>
              <Badge variant="muted">{log.geo_type}</Badge>
              {log.fired ? <Badge variant="accent">Fired</Badge> : null}
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Value {log.raw_value.toLocaleString()} · Confidence{" "}
              {(log.confidence * 100).toFixed(0)}%
            </p>
          </div>
          <time
            className="shrink-0 text-xs text-muted-foreground"
            dateTime={log.timestamp}
          >
            {formatRelativeTime(log.timestamp)}
          </time>
        </li>
      ))}
    </ul>
  )
}

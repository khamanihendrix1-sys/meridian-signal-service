import type * as React from "react"
import { AlertTriangle, Inbox, PlugZap, Search } from "lucide-react"
import { cn } from "@/lib/utils"

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  )
}

export function EmptyState({
  title,
  description,
  icon = "inbox",
}: {
  title: string
  description?: string
  icon?: "inbox" | "alert" | "plug" | "search"
}) {
  const Icon =
    icon === "alert"
      ? AlertTriangle
      : icon === "plug"
        ? PlugZap
        : icon === "search"
          ? Search
          : Inbox
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-card px-6 py-14 text-center">
      <div className="flex size-11 items-center justify-center rounded-full bg-muted">
        <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground text-balance">{title}</p>
        {description ? (
          <p className="mx-auto max-w-md text-sm text-muted-foreground text-pretty">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  )
}

export function NotConfiguredState() {
  return (
    <EmptyState
      icon="plug"
      title="Connect the Meridian API"
      description="Set the MERIDIAN_API_URL and MERIDIAN_API_TOKEN environment variables to a running Meridian Signal Service instance. Once configured, live listings, signals, and market data will appear here."
    />
  )
}

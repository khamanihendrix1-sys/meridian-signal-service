"use client"

import { useState } from "react"
import useSWR from "swr"
import { Radio, ChevronRight } from "lucide-react"
import { fetcher } from "@/lib/fetcher"
import type { ApiResult, SignalDefinitionResponse, SignalLogResponse } from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton, NotConfiguredState, EmptyState } from "@/components/ui/feedback"
import { SignalFeed } from "@/components/signal-feed"
import { cn } from "@/lib/utils"

const CATEGORY_VARIANT: Record<string, "primary" | "accent" | "muted" | "success"> = {
  PRICE: "primary",
  INVENTORY: "accent",
  VELOCITY: "success",
  ABSORPTION: "muted",
}

export function SignalsContent() {
  const [selected, setSelected] = useState<SignalDefinitionResponse | null>(null)

  const { data, isLoading } = useSWR<ApiResult<SignalDefinitionResponse[]>>(
    "/api/signals",
    fetcher,
  )

  if (isLoading) return <SignalsSkeleton />
  if (data && !data.configured) return <NotConfiguredState />
  if (!data || !data.ok || !data.data) {
    return (
      <EmptyState
        icon="alert"
        title="Couldn't load signals"
        description={data?.error ?? "The Meridian API did not return signal definitions."}
      />
    )
  }

  const definitions = data.data
  if (definitions.length === 0) {
    return <EmptyState title="No signal definitions" description="No signals are configured on this instance yet." />
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <div className="flex flex-col gap-3 lg:col-span-2">
        <h2 className="text-sm font-medium text-muted-foreground">
          Signal Definitions ({definitions.length})
        </h2>
        {definitions.map((def) => (
          <button
            key={def.id}
            onClick={() => setSelected(def)}
            className={cn(
              "flex items-center justify-between gap-3 rounded-lg border p-4 text-left transition-colors",
              selected?.id === def.id
                ? "border-primary bg-primary/5"
                : "border-border bg-card hover:border-primary/40 hover:bg-muted/40",
            )}
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-semibold text-foreground">{def.name}</span>
                <Badge variant={CATEGORY_VARIANT[def.category] ?? "muted"}>{def.category}</Badge>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                {def.description}
              </p>
              <p className="mt-1.5 text-xs text-muted-foreground/70">
                Refreshes {def.refresh_frequency}
              </p>
            </div>
            <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          </button>
        ))}
      </div>

      <div className="lg:col-span-3">
        {selected ? (
          <SignalLogPanel definition={selected} />
        ) : (
          <Card className="h-full">
            <CardContent className="flex h-full min-h-64 flex-col items-center justify-center text-center">
              <Radio className="size-8 text-muted-foreground/50" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-foreground">Select a signal</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Choose a definition to see its most recent evaluations.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

function SignalLogPanel({ definition }: { definition: SignalDefinitionResponse }) {
  const { data, isLoading } = useSWR<ApiResult<SignalLogResponse[]>>(
    `/api/signals/${definition.id}/logs`,
    fetcher,
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle>{definition.name} — Recent Evaluations</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : data && data.ok && data.data ? (
          <SignalFeed logs={data.data} />
        ) : (
          <EmptyState title="No evaluations" description={data?.error ?? undefined} />
        )}
      </CardContent>
    </Card>
  )
}

function SignalsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
      <div className="flex flex-col gap-3 lg:col-span-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-64 lg:col-span-3" />
    </div>
  )
}

import { cn } from "@/lib/utils"
import { formatNumber } from "@/lib/utils"
import type { ListingCounts } from "@/lib/types"

const ROWS: { key: keyof Omit<ListingCounts, "total" | "by_status">; label: string; color: string }[] =
  [
    { key: "active", label: "Active", color: "bg-chart-1" },
    { key: "pending", label: "Pending", color: "bg-chart-4" },
    { key: "sold", label: "Sold", color: "bg-chart-3" },
    { key: "expired", label: "Expired", color: "bg-chart-2" },
    { key: "withdrawn", label: "Withdrawn", color: "bg-chart-5" },
  ]

export function StatusBars({ counts }: { counts: ListingCounts }) {
  const max = Math.max(counts.active, counts.pending, counts.sold, counts.expired, counts.withdrawn, 1)

  return (
    <div className="flex flex-col gap-3">
      {ROWS.map((row) => {
        const value = counts[row.key]
        const pct = (value / max) * 100
        return (
          <div key={row.key} className="flex items-center gap-3">
            <span className="w-20 shrink-0 text-xs font-medium text-muted-foreground">
              {row.label}
            </span>
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
              <div
                className={cn("h-full rounded-full", row.color)}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-14 shrink-0 text-right text-xs font-medium tabular-nums text-foreground">
              {formatNumber(value)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

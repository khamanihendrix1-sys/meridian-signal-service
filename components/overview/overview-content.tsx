"use client"

import useSWR from "swr"
import { useSearchParams } from "next/navigation"
import { Building2, CheckCircle2, Zap, DollarSign } from "lucide-react"
import { fetcher } from "@/lib/fetcher"
import type { ApiResult, OverviewResponse } from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton, NotConfiguredState, EmptyState } from "@/components/ui/feedback"
import { KpiCard } from "@/components/kpi-card"
import { SignalFeed } from "@/components/signal-feed"
import { StatusBars } from "@/components/status-bars"
import { formatCurrency, formatNumber, formatPercent, formatDate } from "@/lib/utils"

export function OverviewContent() {
  const searchParams = useSearchParams()
  const geography = searchParams.get("geography") ?? ""
  const geoType = searchParams.get("geo_type") ?? ""

  const qs = new URLSearchParams()
  if (geography) qs.set("geography", geography)
  if (geoType) qs.set("geo_type", geoType)

  const { data, isLoading } = useSWR<ApiResult<OverviewResponse>>(
    `/api/overview${qs.toString() ? `?${qs.toString()}` : ""}`,
    fetcher,
    { refreshInterval: 60000 },
  )

  if (isLoading) return <OverviewSkeleton />
  if (data && !data.configured) return <NotConfiguredState />
  if (!data || !data.ok || !data.data) {
    return (
      <EmptyState
        icon="alert"
        title="Couldn't load the overview"
        description={data?.error ?? "The Meridian API did not return data. Verify the service is running and reachable."}
      />
    )
  }

  const overview = data.data
  const report = overview.latest_market_report

  return (
    <div className="flex flex-col gap-6">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Total Listings"
          value={formatNumber(overview.listings.total)}
          icon={Building2}
          hint={geography ? `in ${geography}` : "across all geographies"}
        />
        <KpiCard
          label="Active Listings"
          value={formatNumber(overview.listings.active)}
          icon={CheckCircle2}
          hint={`${overview.listings.sold} sold`}
        />
        <KpiCard
          label="Signals Fired"
          value={formatNumber(overview.signals.fired)}
          icon={Zap}
          hint={`of ${formatNumber(overview.signals.total_evaluations)} evaluations`}
        />
        <KpiCard
          label="Median Price"
          value={report ? formatCurrency(report.median_price) : "—"}
          icon={DollarSign}
          hint={report ? formatDate(report.report_date) : "select a geography"}
          trend={
            report
              ? {
                  value: formatPercent(report.mom_price_change),
                  direction:
                    report.mom_price_change > 0
                      ? "up"
                      : report.mom_price_change < 0
                        ? "down"
                        : "flat",
                }
              : undefined
          }
        />
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Listings by Status</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.listings.total > 0 ? (
              <StatusBars counts={overview.listings} />
            ) : (
              <EmptyState title="No listings found" />
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Recent Signal Activity</CardTitle>
            <Badge variant="primary">{overview.signals.definitions} definitions</Badge>
          </CardHeader>
          <CardContent>
            <SignalFeed logs={overview.recent_signals} />
          </CardContent>
        </Card>
      </section>

      {report ? (
        <section>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>
                Latest Market Report — {report.geography} ({report.geo_type})
              </CardTitle>
              <span className="text-xs text-muted-foreground">
                {formatDate(report.report_date)}
              </span>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <Metric label="Median Price" value={formatCurrency(report.median_price)} />
                <Metric label="Avg Days on Market" value={formatNumber(Math.round(report.avg_days_on_market))} />
                <Metric label="Months of Inventory" value={report.months_of_inventory.toFixed(1)} />
                <Metric label="YoY Price Change" value={formatPercent(report.yoy_price_change)} />
                <Metric label="Active Listings" value={formatNumber(report.active_listings)} />
                <Metric label="Sold (30d)" value={formatNumber(report.sold_last_30d)} />
                <Metric label="Absorption Rate" value={formatPercent(report.absorption_rate)} />
                <Metric label="List/Sold Ratio" value={formatPercent(report.list_to_sold_ratio)} />
              </div>
            </CardContent>
          </Card>
        </section>
      ) : null}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-secondary/40 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-foreground">{value}</p>
    </div>
  )
}

function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Skeleton className="h-64 lg:col-span-1" />
        <Skeleton className="h-64 lg:col-span-2" />
      </div>
    </div>
  )
}

"use client"

import { useMemo } from "react"
import useSWR from "swr"
import { useSearchParams } from "next/navigation"
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { fetcher } from "@/lib/fetcher"
import type { ApiResult, MarketReportResponse } from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton, NotConfiguredState, EmptyState } from "@/components/ui/feedback"
import { formatCurrency, formatNumber, formatDate } from "@/lib/utils"

export function MarketReportsContent() {
  const searchParams = useSearchParams()
  const geography = searchParams.get("geography") ?? ""
  const geoType = searchParams.get("geo_type") ?? ""

  const qs = new URLSearchParams()
  if (geography) qs.set("geography", geography)
  if (geoType) qs.set("geo_type", geoType)
  qs.set("limit", "24")

  const shouldFetch = Boolean(geography && geoType)

  const { data, isLoading } = useSWR<ApiResult<MarketReportResponse[]>>(
    shouldFetch ? `/api/market-reports?${qs.toString()}` : null,
    fetcher,
  )

  const series = useMemo(() => {
    const reports = data?.data ?? []
    return [...reports]
      .sort((a, b) => a.report_date.localeCompare(b.report_date))
      .map((r) => ({
        date: formatDate(r.report_date),
        median: Number(r.median_price),
        dom: Math.round(r.avg_days_on_market),
        inventory: Number(r.months_of_inventory.toFixed(1)),
        absorption: Number((r.absorption_rate * 100).toFixed(1)),
      }))
  }, [data])

  if (!shouldFetch) {
    return (
      <EmptyState
        icon="search"
        title="Choose a geography"
        description="Market reports are geography-specific. Set a geography and type in the header filter to view trends."
      />
    )
  }

  if (isLoading) return <ReportsSkeleton />
  if (data && !data.configured) return <NotConfiguredState />
  if (!data || !data.ok || !data.data || data.data.length === 0) {
    return (
      <EmptyState
        icon="alert"
        title="No market reports"
        description={data?.error ?? `No reports found for ${geography}.`}
      />
    )
  }

  const latest = [...data.data].sort((a, b) => b.report_date.localeCompare(a.report_date))[0]

  return (
    <div className="flex flex-col gap-6">
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Metric label="Median Price" value={formatCurrency(latest.median_price)} />
        <Metric label="Avg Days on Market" value={formatNumber(Math.round(latest.avg_days_on_market))} />
        <Metric label="Months of Inventory" value={latest.months_of_inventory.toFixed(1)} />
        <Metric label="Active Listings" value={formatNumber(latest.active_listings)} />
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="Median Price Trend">
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={series} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
              <YAxis
                tick={{ fontSize: 11 }}
                stroke="var(--color-muted-foreground)"
                tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
                width={48}
              />
              <Tooltip content={<ChartTooltip formatter={(v) => formatCurrency(v)} />} />
              <Area
                type="monotone"
                dataKey="median"
                stroke="var(--color-chart-1)"
                strokeWidth={2}
                fill="url(#priceFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Avg Days on Market">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={series} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" width={36} />
              <Tooltip content={<ChartTooltip formatter={(v) => `${v} days`} />} />
              <Line
                type="monotone"
                dataKey="dom"
                stroke="var(--color-chart-2)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Months of Inventory">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={series} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" width={36} />
              <Tooltip content={<ChartTooltip formatter={(v) => `${v} mo`} />} />
              <Bar dataKey="inventory" fill="var(--color-chart-3)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Absorption Rate (%)">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={series} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-muted-foreground)" width={36} />
              <Tooltip content={<ChartTooltip formatter={(v) => `${v}%`} />} />
              <Line
                type="monotone"
                dataKey="absorption"
                stroke="var(--color-chart-4)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function ChartTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
  formatter: (v: number) => string
}) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-popover-foreground">{label}</p>
      <p className="text-muted-foreground">{formatter(payload[0].value)}</p>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-semibold tabular-nums text-foreground">{value}</p>
      </CardContent>
    </Card>
  )
}

function ReportsSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-72" />
        ))}
      </div>
    </div>
  )
}

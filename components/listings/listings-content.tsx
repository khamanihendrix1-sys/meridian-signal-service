"use client"

import { useState } from "react"
import useSWRInfinite from "swr/infinite"
import { useSearchParams } from "next/navigation"
import { Building2 } from "lucide-react"
import { fetcher } from "@/lib/fetcher"
import type { ApiResult, ListingResponse, ListingStatus, PropertyType } from "@/lib/types"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton, NotConfiguredState, EmptyState } from "@/components/ui/feedback"
import { formatCurrency, formatNumber, formatDate } from "@/lib/utils"

const STATUS_OPTIONS: ListingStatus[] = ["ACTIVE", "PENDING", "SOLD", "EXPIRED", "WITHDRAWN"]
const PROPERTY_OPTIONS: PropertyType[] = ["SFR", "CONDO", "TOWNHOUSE", "MULTIFAMILY", "LAND"]

const STATUS_VARIANT: Record<string, "success" | "primary" | "muted" | "accent"> = {
  ACTIVE: "success",
  PENDING: "accent",
  SOLD: "primary",
  EXPIRED: "muted",
  WITHDRAWN: "muted",
}

const PAGE_SIZE = 20

export function ListingsContent() {
  const searchParams = useSearchParams()
  const geography = searchParams.get("geography") ?? ""
  const geoType = searchParams.get("geo_type") ?? ""

  const [status, setStatus] = useState<string>("")
  const [propertyType, setPropertyType] = useState<string>("")
  const [maxPrice, setMaxPrice] = useState<string>("")

  const buildQuery = (cursor: string | null) => {
    const qs = new URLSearchParams()
    if (geography) qs.set("geography", geography)
    if (geoType) qs.set("geo_type", geoType)
    if (status) qs.set("status", status)
    if (propertyType) qs.append("property_types", propertyType)
    if (maxPrice) qs.set("max_price", maxPrice)
    qs.set("limit", String(PAGE_SIZE))
    if (cursor) qs.set("cursor", cursor)
    return `/api/listings?${qs.toString()}`
  }

  const { data, size, setSize, isLoading, isValidating } = useSWRInfinite<
    ApiResult<ListingResponse[]>
  >(
    (index, previous) => {
      if (previous && !previous.nextCursor) return null
      const cursor = index === 0 ? null : previous?.nextCursor ?? null
      return buildQuery(cursor)
    },
    fetcher,
    { revalidateFirstPage: false },
  )

  const first = data?.[0]
  if (isLoading) return <ListingsSkeleton />
  if (first && !first.configured) return <NotConfiguredState />
  if (first && !first.ok) {
    return (
      <EmptyState
        icon="alert"
        title="Couldn't load listings"
        description={first.error ?? "The Meridian API did not return listings."}
      />
    )
  }

  const listings = data?.flatMap((page) => page.data ?? []) ?? []
  const lastPage = data?.[data.length - 1]
  const hasMore = Boolean(lastPage?.nextCursor)

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end gap-3">
        <Filter label="Status" value={status} onChange={setStatus} options={STATUS_OPTIONS} />
        <Filter
          label="Property Type"
          value={propertyType}
          onChange={setPropertyType}
          options={PROPERTY_OPTIONS}
        />
        <div className="flex flex-col gap-1">
          <label htmlFor="max-price" className="text-xs font-medium text-muted-foreground">
            Max Price
          </label>
          <input
            id="max-price"
            type="number"
            inputMode="numeric"
            placeholder="Any"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className="h-9 w-32 rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        {geography ? (
          <Badge variant="muted">
            {geography} · {geoType || "geo"}
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">Tip: set a geography in the header filter.</span>
        )}
      </div>

      {listings.length === 0 ? (
        <EmptyState
          icon="search"
          title="No listings match"
          description="Try adjusting the filters or clearing the geography."
        />
      ) : (
        <>
          <Card className="overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Address</th>
                    <th className="px-4 py-3 font-medium">Type</th>
                    <th className="px-4 py-3 font-medium">Beds/Baths</th>
                    <th className="px-4 py-3 text-right font-medium">List Price</th>
                    <th className="px-4 py-3 text-right font-medium">DOM</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Listed</th>
                  </tr>
                </thead>
                <tbody>
                  {listings.map((l) => (
                    <tr
                      key={l.id}
                      className="border-b border-border last:border-0 hover:bg-muted/40"
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-foreground">{l.address}</p>
                        <p className="text-xs text-muted-foreground">
                          {l.city}, {l.state} {l.zip}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{l.property_type}</td>
                      <td className="px-4 py-3 tabular-nums text-muted-foreground">
                        {l.beds ?? "—"} / {l.baths ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right font-medium tabular-nums text-foreground">
                        {formatCurrency(l.list_price)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                        {formatNumber(l.days_on_market)}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={STATUS_VARIANT[l.status] ?? "muted"}>{l.status}</Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{formatDate(l.list_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="flex items-center justify-center">
            {hasMore ? (
              <button
                onClick={() => setSize(size + 1)}
                disabled={isValidating}
                className="rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-60"
              >
                {isValidating ? "Loading…" : "Load more"}
              </button>
            ) : (
              <p className="text-xs text-muted-foreground">
                Showing all {formatNumber(listings.length)} listings
              </p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function Filter({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
      >
        <option value="">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  )
}

function ListingsSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex gap-3">
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-32" />
      </div>
      <Skeleton className="h-96" />
    </div>
  )
}

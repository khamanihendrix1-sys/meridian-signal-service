import { NextResponse } from "next/server"
import { meridianFetch } from "@/lib/meridian"
import type { MarketReportResponse } from "@/lib/types"

export const dynamic = "force-dynamic"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const geography = searchParams.get("geography")
  const geoType = searchParams.get("geo_type")
  const limit = searchParams.get("limit") ?? "12"

  if (!geography || !geoType) {
    return NextResponse.json({
      ok: false,
      configured: true,
      data: null,
      error: "geography and geo_type are required.",
    })
  }

  const qs = new URLSearchParams({
    geography,
    geo_type: geoType,
    limit,
  })

  const result = await meridianFetch<MarketReportResponse[]>(
    `/v1/market-reports?${qs.toString()}`,
  )
  return NextResponse.json(result)
}

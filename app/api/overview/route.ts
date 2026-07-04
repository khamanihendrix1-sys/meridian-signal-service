import { NextResponse } from "next/server"
import { meridianFetch } from "@/lib/meridian"
import type { OverviewResponse } from "@/lib/types"

export const dynamic = "force-dynamic"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const qs = new URLSearchParams()
  const geography = searchParams.get("geography")
  const geoType = searchParams.get("geo_type")
  if (geography) qs.set("geography", geography)
  if (geoType) qs.set("geo_type", geoType)
  const suffix = qs.toString() ? `?${qs.toString()}` : ""

  const result = await meridianFetch<OverviewResponse>(`/v1/overview${suffix}`)
  return NextResponse.json(result)
}

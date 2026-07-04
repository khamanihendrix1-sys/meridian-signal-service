import { NextResponse } from "next/server"
import { meridianFetch } from "@/lib/meridian"
import type { ListingResponse } from "@/lib/types"

const PASS_THROUGH = [
  "geography",
  "geo_type",
  "property_types",
  "min_price",
  "max_price",
  "beds",
  "baths",
  "status",
  "limit",
  "cursor",
]

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const qs = new URLSearchParams()
  for (const key of PASS_THROUGH) {
    for (const value of searchParams.getAll(key)) {
      if (value) qs.append(key, value)
    }
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : ""

  const result = await meridianFetch<ListingResponse[]>(`/v1/listings${suffix}`)
  return NextResponse.json(result)
}

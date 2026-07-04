import { NextResponse } from "next/server"
import { meridianFetch } from "@/lib/meridian"
import type { SignalLogResponse } from "@/lib/types"

export const dynamic = "force-dynamic"

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params
  const { searchParams } = new URL(request.url)
  const qs = new URLSearchParams()
  const geography = searchParams.get("geography")
  const limit = searchParams.get("limit")
  if (geography) qs.set("geography", geography)
  if (limit) qs.set("limit", limit)
  const suffix = qs.toString() ? `?${qs.toString()}` : ""

  const result = await meridianFetch<SignalLogResponse[]>(
    `/v1/signals/${encodeURIComponent(id)}/logs${suffix}`,
  )
  return NextResponse.json(result)
}

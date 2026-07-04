import { NextResponse } from "next/server"
import { meridianFetch } from "@/lib/meridian"
import type { SignalDefinitionResponse } from "@/lib/types"

export async function GET() {
  const result = await meridianFetch<SignalDefinitionResponse[]>("/v1/signals")
  return NextResponse.json(result)
}

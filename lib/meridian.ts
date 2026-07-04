import "server-only"

import type { ApiResult } from "./types"

const BASE_URL = process.env.MERIDIAN_API_URL
const TOKEN = process.env.MERIDIAN_API_TOKEN

export function isConfigured(): boolean {
  return Boolean(BASE_URL)
}

/**
 * Server-side fetch against the Meridian Signal Service. The API URL and JWT
 * bearer token are read from environment variables and never exposed to the
 * browser. Returns a normalized {@link ApiResult} so route handlers can render
 * graceful "not configured" / error states.
 */
export async function meridianFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  if (!BASE_URL) {
    return {
      ok: false,
      configured: false,
      data: null,
      error: "MERIDIAN_API_URL is not set.",
    }
  }

  const url = `${BASE_URL.replace(/\/$/, "")}${path}`
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (TOKEN) {
    headers.Authorization = `Bearer ${TOKEN}`
  }

  try {
    const res = await fetch(url, {
      ...init,
      headers,
      // Always fetch fresh; the upstream service handles its own caching.
      cache: "no-store",
    })

    const text = await res.text()
    const body = text ? safeJsonParse(text) : null

    if (!res.ok) {
      const message =
        (body && typeof body === "object" && "message" in body
          ? String((body as Record<string, unknown>).message)
          : null) ?? `Upstream API returned ${res.status}`
      return { ok: false, configured: true, data: null, error: message }
    }

    return {
      ok: true,
      configured: true,
      data: body as T,
      error: null,
      nextCursor: res.headers.get("X-Next-Cursor"),
    }
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "Failed to reach the Meridian API."
    return { ok: false, configured: true, data: null, error: message }
  }
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

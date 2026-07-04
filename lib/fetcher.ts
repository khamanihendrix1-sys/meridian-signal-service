import type { ApiResult } from "./types"

export async function fetcher<T>(url: string): Promise<ApiResult<T>> {
  const res = await fetch(url)
  if (!res.ok) {
    return {
      ok: false,
      configured: true,
      data: null,
      error: `Request failed with ${res.status}`,
    }
  }
  return (await res.json()) as ApiResult<T>
}

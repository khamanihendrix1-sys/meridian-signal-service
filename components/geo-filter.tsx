"use client"

import { useRouter, useSearchParams, usePathname } from "next/navigation"
import { useState, useEffect } from "react"
import { MapPin } from "lucide-react"
import type { GeoType } from "@/lib/types"

const GEO_TYPES: GeoType[] = ["CITY", "ZIP", "COUNTY", "METRO", "NEIGHBORHOOD"]

export function GeoFilter() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [geography, setGeography] = useState(searchParams.get("geography") ?? "")
  const [geoType, setGeoType] = useState<GeoType>(
    (searchParams.get("geo_type") as GeoType) ?? "CITY",
  )

  useEffect(() => {
    setGeography(searchParams.get("geography") ?? "")
    setGeoType((searchParams.get("geo_type") as GeoType) ?? "CITY")
  }, [searchParams])

  function apply(nextGeography: string, nextGeoType: GeoType) {
    const params = new URLSearchParams(searchParams.toString())
    if (nextGeography.trim()) {
      params.set("geography", nextGeography.trim())
      params.set("geo_type", nextGeoType)
    } else {
      params.delete("geography")
      params.delete("geo_type")
    }
    params.delete("cursor")
    router.replace(`${pathname}?${params.toString()}`)
  }

  return (
    <form
      className="flex flex-wrap items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault()
        apply(geography, geoType)
      }}
    >
      <div className="flex items-center gap-2 rounded-md border border-input bg-card px-3 py-1.5">
        <MapPin className="size-4 text-muted-foreground" aria-hidden="true" />
        <input
          type="text"
          value={geography}
          onChange={(e) => setGeography(e.target.value)}
          placeholder="Geography (e.g. Austin)"
          aria-label="Geography"
          className="w-40 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>
      <select
        value={geoType}
        onChange={(e) => setGeoType(e.target.value as GeoType)}
        aria-label="Geography type"
        className="rounded-md border border-input bg-card px-3 py-1.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
      >
        {GEO_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <button
        type="submit"
        className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Apply
      </button>
    </form>
  )
}

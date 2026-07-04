// Types mirroring the Meridian Signal Service API schemas.

export type GeoType = "METRO" | "ZIP" | "COUNTY" | "NEIGHBORHOOD" | "CITY"

export type ListingStatus =
  | "ACTIVE"
  | "PENDING"
  | "SOLD"
  | "EXPIRED"
  | "WITHDRAWN"

export type PropertyType =
  | "SFR"
  | "CONDO"
  | "TOWNHOUSE"
  | "MULTIFAMILY"
  | "LAND"

export type SignalCategory = "PRICE" | "INVENTORY" | "VELOCITY" | "ABSORPTION"

export interface ListingResponse {
  id: string
  source: string
  source_id: string
  mls_number: string | null
  address: string
  unit: string | null
  city: string
  state: string
  zip: string
  county: string | null
  lat: number | null
  lon: number | null
  property_type: PropertyType
  beds: number | null
  baths: number | null
  living_sqft: number | null
  lot_sqft: number | null
  year_built: number | null
  list_price: string
  sold_price: string | null
  list_date: string
  sold_date: string | null
  status: ListingStatus
  days_on_market: number
  photos: string[]
  created_at: string
  updated_at: string
}

export interface SignalDefinitionResponse {
  id: string
  name: string
  category: SignalCategory
  description: string
  refresh_frequency: string
  output_schema: Record<string, unknown>
  created_at: string
}

export interface SignalLogResponse {
  id: string
  signal_id: string
  geography: string
  geo_type: GeoType
  timestamp: string
  raw_value: number
  computed_output: Record<string, unknown>
  confidence: number
  fired: boolean
  created_at: string
}

export interface MarketReportResponse {
  id: string
  geography: string
  geo_type: GeoType
  report_date: string
  median_price: string
  mean_price: string
  active_listings: number
  sold_last_30d: number
  avg_days_on_market: number
  months_of_inventory: number
  absorption_rate: number
  yoy_price_change: number
  mom_price_change: number
  list_to_sold_ratio: number
  raw_metrics: Record<string, unknown>
  created_at: string
}

export interface ListingCounts {
  total: number
  active: number
  pending: number
  sold: number
  expired: number
  withdrawn: number
  by_status: Record<string, number>
}

export interface SignalCounts {
  total_evaluations: number
  fired: number
  definitions: number
}

export interface OverviewResponse {
  geography: string | null
  geo_type: GeoType | null
  generated_at: string
  listings: ListingCounts
  signals: SignalCounts
  recent_signals: SignalLogResponse[]
  latest_market_report: MarketReportResponse | null
}

// Wrapper returned by the internal proxy routes so the UI can render a
// graceful state when the upstream API is not yet configured.
export interface ApiResult<T> {
  ok: boolean
  configured: boolean
  data: T | null
  error: string | null
  nextCursor?: string | null
}

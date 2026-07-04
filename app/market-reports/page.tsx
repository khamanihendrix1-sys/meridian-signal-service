import { Suspense } from "react"
import { AppShell } from "@/components/app-shell"
import { MarketReportsContent } from "@/components/market-reports/market-reports-content"

export default function MarketReportsPage() {
  return (
    <AppShell title="Market Reports" description="Historical market metrics and trends">
      <Suspense fallback={null}>
        <MarketReportsContent />
      </Suspense>
    </AppShell>
  )
}

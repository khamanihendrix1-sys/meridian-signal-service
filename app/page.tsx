import { Suspense } from "react"
import { AppShell } from "@/components/app-shell"
import { OverviewContent } from "@/components/overview/overview-content"

export default function OverviewPage() {
  return (
    <AppShell title="Overview" description="Market intelligence at a glance">
      <Suspense fallback={null}>
        <OverviewContent />
      </Suspense>
    </AppShell>
  )
}

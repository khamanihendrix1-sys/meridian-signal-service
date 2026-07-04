import { Suspense } from "react"
import { AppShell } from "@/components/app-shell"
import { SignalsContent } from "@/components/signals/signals-content"

export default function SignalsPage() {
  return (
    <AppShell title="Signals" description="Signal definitions and recent evaluations">
      <Suspense fallback={null}>
        <SignalsContent />
      </Suspense>
    </AppShell>
  )
}

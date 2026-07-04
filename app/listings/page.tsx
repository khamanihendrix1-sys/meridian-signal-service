import { Suspense } from "react"
import { AppShell } from "@/components/app-shell"
import { ListingsContent } from "@/components/listings/listings-content"

export default function ListingsPage() {
  return (
    <AppShell title="Listings" description="Browse and filter property inventory">
      <Suspense fallback={null}>
        <ListingsContent />
      </Suspense>
    </AppShell>
  )
}

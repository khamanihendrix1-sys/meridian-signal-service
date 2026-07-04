"use client"

import { Suspense, useState, type ReactNode } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Building2,
  Radio,
  LineChart,
  Compass,
  Menu,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { GeoFilter } from "@/components/geo-filter"

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/listings", label: "Listings", icon: Building2 },
  { href: "/signals", label: "Signals", icon: Radio },
  { href: "/market-reports", label: "Market Reports", icon: LineChart },
]

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()
  return (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href)
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-sidebar-primary/15 text-sidebar-primary"
                : "text-sidebar-foreground hover:bg-sidebar-accent",
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {label}
          </Link>
        )
      })}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <div className="flex size-8 items-center justify-center rounded-md bg-sidebar-primary text-primary-foreground">
        <Compass className="size-4.5" aria-hidden="true" />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-sidebar-foreground">Meridian</p>
        <p className="text-xs text-sidebar-foreground/60">Signal Service</p>
      </div>
    </div>
  )
}

export function AppShell({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: ReactNode
}) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col gap-6 bg-sidebar p-4 lg:flex">
        <Brand />
        <NavLinks />
        <div className="mt-auto rounded-md border border-sidebar-border bg-sidebar-accent/40 p-3">
          <p className="text-xs font-medium text-sidebar-foreground">Live data</p>
          <p className="mt-1 text-xs leading-relaxed text-sidebar-foreground/60">
            Metrics stream from your Meridian Signal Service instance.
          </p>
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-foreground/40"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col gap-6 bg-sidebar p-4">
            <div className="flex items-center justify-between">
              <Brand />
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close menu"
                className="rounded-md p-1 text-sidebar-foreground hover:bg-sidebar-accent"
              >
                <X className="size-5" />
              </button>
            </div>
            <NavLinks onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur">
          <div className="flex flex-col gap-3 px-4 py-3.5 md:flex-row md:items-center md:justify-between md:px-6">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
                className="rounded-md p-1.5 text-foreground hover:bg-muted lg:hidden"
              >
                <Menu className="size-5" />
              </button>
              <div>
                <h1 className="text-lg font-semibold tracking-tight text-foreground text-balance">
                  {title}
                </h1>
                {description ? (
                  <p className="text-sm text-muted-foreground">{description}</p>
                ) : null}
              </div>
            </div>
            <Suspense fallback={null}>
              <GeoFilter />
            </Suspense>
          </div>
        </header>

        <main className="flex-1 px-4 py-6 md:px-6">{children}</main>
      </div>
    </div>
  )
}

import type * as React from "react"
import { cn } from "@/lib/utils"

type Variant = "default" | "primary" | "accent" | "success" | "muted" | "destructive"

const variants: Record<Variant, string> = {
  default: "bg-secondary text-secondary-foreground border-border",
  primary: "bg-primary/10 text-primary border-primary/20",
  accent: "bg-accent/20 text-accent-foreground border-accent/30",
  success: "bg-success/10 text-success border-success/20",
  muted: "bg-muted text-muted-foreground border-border",
  destructive: "bg-destructive/10 text-destructive border-destructive/20",
}

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  )
}

import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

// 2026-08 ground-up rework: TradingView-density sizing, Apple-grade motion.
// Sentence case, accent-filled primary, hairline secondary surfaces, a press
// scale micro-interaction, and a real 2px focus ring. All colors ride the
// theme tokens so every variant works in light and dark.
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap select-none",
    "font-medium rounded-lg",
    "transition-[background-color,border-color,color,box-shadow,transform]",
    "duration-150 ease-[cubic-bezier(.2,0,0,1)]",
    "active:scale-[0.98]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    "disabled:pointer-events-none disabled:opacity-50",
  ].join(" "),
  {
    variants: {
      variant: {
        default: [
          "bg-primary text-primary-foreground",
          "shadow-[var(--tv-shadow-1)]",
          "hover:bg-[var(--tv-accent-hover)] hover:shadow-[var(--tv-shadow-2)]",
        ].join(" "),
        destructive:
          "bg-destructive text-destructive-foreground shadow-[var(--tv-shadow-1)] hover:opacity-90",
        ghost:
          "bg-transparent text-[var(--tv-text-2)] hover:bg-secondary hover:text-[var(--tv-text-1)]",
        outline: [
          "bg-transparent border border-[var(--tv-border-strong)] text-[var(--tv-text-1)]",
          "hover:bg-secondary hover:border-[var(--tv-border-strong)]",
        ].join(" "),
        secondary:
          "bg-secondary text-[var(--tv-text-1)] hover:bg-[var(--tv-surface-2)]",
        link: "text-primary underline-offset-4 hover:underline bg-transparent",
      },
      size: {
        default: "h-9 px-4 text-[13px]",
        sm:      "h-8 px-3 text-xs rounded-md",
        lg:      "h-10 px-6 text-sm",
        icon:    "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }

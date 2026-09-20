import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full px-3 py-1 rounded-lg",
          "bg-[var(--tv-surface)] text-[var(--tv-text-1)]",
          "placeholder:text-muted-foreground",
          "border border-input",
          "text-sm tnum",
          "shadow-[var(--tv-shadow-1)]",
          "transition-[border-color,box-shadow] duration-150 ease-[cubic-bezier(.2,0,0,1)]",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          "focus-visible:outline-none focus-visible:border-[var(--tv-accent)]",
          "focus-visible:ring-2 focus-visible:ring-ring/25",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }

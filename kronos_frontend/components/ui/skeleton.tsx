import { cn } from "@/lib/utils"

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-[2px]", className)}
      style={{ background: "rgba(40,180,130,.08)" }}
      {...props}
    />
  )
}

export { Skeleton }

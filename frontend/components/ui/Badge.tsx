"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-gray-100 text-gray-800",
        success: "bg-green-100 text-green-800",
        warning: "bg-yellow-100 text-yellow-800",
        danger: "bg-red-100 text-red-800",
        info: "bg-blue-100 text-blue-800",
        outline: "border border-gray-300 text-gray-700",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

// Helpers for domain status values
export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, VariantProps<typeof badgeVariants>["variant"]> = {
    OPEN: "success",
    ACTIVE: "success",
    POSTED: "success",
    CLOSED: "default",
    BLOCKED: "danger",
    CANCELLED: "danger",
    PARTIALLY_CANCELLED: "warning",
    DRAFT: "warning",
    SUBMITTED: "info",
    DEACTIVATED: "danger",
  };
  return <Badge variant={map[status] ?? "default"}>{status}</Badge>;
}

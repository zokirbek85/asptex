"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold leading-none",
  {
    variants: {
      variant: {
        default:  "bg-muted text-foreground-muted",
        success:  "bg-success-light text-success",
        warning:  "bg-warning-light text-warning",
        danger:   "bg-danger-light text-danger",
        info:     "bg-primary-light text-primary",
        teal:     "bg-secondary-light text-secondary",
        outline:  "border border-border text-foreground-muted",
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

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, VariantProps<typeof badgeVariants>["variant"]> = {
    OPEN:                 "success",
    ACTIVE:               "success",
    POSTED:               "success",
    SUBMITTED:            "info",
    CLOSED:               "default",
    BLOCKED:              "danger",
    CANCELLED:            "danger",
    PARTIALLY_CANCELLED:  "warning",
    DRAFT:                "warning",
    DEACTIVATED:          "danger",
    APPROVED:             "success",
    PENDING:              "warning",
  };

  const labels: Record<string, string> = {
    OPEN:                "Ochiq",
    ACTIVE:              "Faol",
    POSTED:              "Qayd etildi",
    SUBMITTED:           "Yuborildi",
    CLOSED:              "Yopildi",
    BLOCKED:             "Bloklangan",
    CANCELLED:           "Bekor qilindi",
    PARTIALLY_CANCELLED: "Qisman bekor",
    DRAFT:               "Qoralama",
    DEACTIVATED:         "O'chirildi",
    APPROVED:            "Tasdiqlandi",
    PENDING:             "Kutilmoqda",
  };

  return (
    <Badge variant={map[status] ?? "default"}>
      {labels[status] ?? status}
    </Badge>
  );
}

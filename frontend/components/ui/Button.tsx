"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "@radix-ui/react-slot";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-1.5 rounded-[9px] text-[13px] font-semibold",
    "transition-all duration-150 active:scale-[0.98]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    "disabled:pointer-events-none disabled:opacity-50 select-none",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm",
        secondary:
          "bg-muted text-foreground hover:bg-muted/80 border border-border",
        outline:
          "border border-border bg-transparent text-foreground hover:bg-muted",
        danger:
          "bg-danger text-white hover:bg-danger/90 shadow-sm",
        ghost:
          "text-foreground-muted hover:bg-muted hover:text-foreground",
        success:
          "bg-success text-white hover:bg-success/90 shadow-sm",
        teal:
          "bg-secondary text-white hover:bg-secondary/90 shadow-sm",
      },
      size: {
        xs: "h-7 px-2.5 text-[12px] gap-1",
        sm: "h-8 px-3 text-[12px]",
        md: "h-9 px-4",
        lg: "h-10 px-5 text-[14px]",
        icon: "h-9 w-9 p-0",
        "icon-sm": "h-7 w-7 p-0",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {loading && <Loader2 size={14} className="animate-spin" />}
          {children}
        </>
      )}
    </Comp>
  );
}

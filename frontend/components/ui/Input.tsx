"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-[13px] font-medium text-foreground">
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            "asptex-input h-9 w-full rounded-[9px] border border-border bg-surface px-3 text-[13px]",
            "text-foreground placeholder:text-foreground-subtle",
            "transition-all duration-150",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-danger",
            className
          )}
          {...props}
        />
        {error && <p className="text-[12px] text-danger">{error}</p>}
        {hint && !error && <p className="text-[12px] text-foreground-subtle">{hint}</p>}
      </div>
    );
  }
);
Input.displayName = "Input";

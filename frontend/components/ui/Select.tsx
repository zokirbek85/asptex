"use client";

import * as RadixSelect from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

// Radix Select forbids value="". Sentinel translates "" → internal non-empty string.
const EMPTY_SENTINEL = "__empty__";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  label?: string;
  error?: string;
  disabled?: boolean;
  className?: string;
}

export function Select({
  value,
  onValueChange,
  options,
  placeholder = "Tanlang…",
  label,
  error,
  disabled,
  className,
}: SelectProps) {
  const toRadix = (v: string | undefined) => (v === "" ? EMPTY_SENTINEL : v);
  const fromRadix = (v: string) => (v === EMPTY_SENTINEL ? "" : v);

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-[13px] font-medium text-foreground">{label}</label>
      )}
      <RadixSelect.Root
        value={toRadix(value)}
        onValueChange={(v) => onValueChange?.(fromRadix(v))}
        disabled={disabled}
      >
        <RadixSelect.Trigger
          className={cn(
            "asptex-input inline-flex h-9 w-full items-center justify-between rounded-[9px]",
            "border border-border bg-surface px-3 text-[13px] text-foreground",
            "transition-all duration-150",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "data-[placeholder]:text-foreground-subtle",
            error && "border-danger",
            className
          )}
        >
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon>
            <ChevronDown size={14} className="text-foreground-subtle flex-shrink-0" />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>

        <RadixSelect.Portal>
          <RadixSelect.Content
            className={cn(
              "z-[200] min-w-[8rem] overflow-hidden rounded-xl border border-border",
              "bg-surface shadow-card-lg animate-fade-in"
            )}
            position="popper"
            sideOffset={4}
          >
            <RadixSelect.Viewport className="p-1">
              {options.map((opt) => (
                <RadixSelect.Item
                  key={opt.value}
                  value={toRadix(opt.value)!}
                  disabled={opt.disabled}
                  className={cn(
                    "relative flex cursor-pointer select-none items-center rounded-lg px-8 py-2 text-[13px] outline-none",
                    "text-foreground",
                    "data-[highlighted]:bg-primary-light data-[highlighted]:text-primary",
                    "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
                    "transition-colors"
                  )}
                >
                  <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator className="absolute left-2.5">
                    <Check size={12} />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
      {error && <p className="text-[12px] text-danger">{error}</p>}
    </div>
  );
}

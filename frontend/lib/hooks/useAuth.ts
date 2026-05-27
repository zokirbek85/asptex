"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuthStore } from "@/lib/stores/auth";

export function useRequireAuth() {
  const router = useRouter();
  const { isAuthenticated, hasCompany } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    } else if (!hasCompany()) {
      router.replace("/select-company");
    }
  }, [isAuthenticated, hasCompany, router]);

  return {
    isAuthenticated: isAuthenticated(),
    hasCompany: hasCompany(),
  };
}

export function useRole() {
  const { activeRole, isRole, isReadOnly } = useAuthStore();
  return { role: activeRole, isRole, isReadOnly: isReadOnly() };
}

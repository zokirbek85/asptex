"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Building2, ChevronRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/auth";
import type { UserRole } from "@/lib/types";
import { AsptexLogo } from "@/components/brand/AsptexLogo";
import { cn } from "@/lib/utils";

const ROLE_LABELS: Record<UserRole, { uz: string; ru: string }> = {
  ADMIN:           { uz: "Administrator",             ru: "Администратор" },
  DIRECTOR:        { uz: "Direktor",                  ru: "Директор" },
  DEPUTY_DIRECTOR: { uz: "Direktor muovini",          ru: "Зам. директора" },
  WH_RAW:          { uz: "Xom ashyo ombori",          ru: "Склад сырья" },
  WH_FINISHED:     { uz: "Tayyor mahsulot ombori",    ru: "Склад готовой продукции" },
  PRODUCTION:      { uz: "Ishlab chiqarish",          ru: "Производство" },
  ACCOUNTANT:      { uz: "Buxgalter",                 ru: "Бухгалтер" },
};

export default function SelectCompanyPage() {
  const router = useRouter();
  const { companies, user, setCompanyContext, language, clearAuth } = useAuthStore();
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) router.replace("/login");
  }, [user, router]);

  const handleSelectCompany = async (companyId: string, role: UserRole) => {
    setLoadingId(companyId);
    try {
      const response = await authApi.switchCompany(companyId);
      setCompanyContext(companyId, role, response.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Xato yuz berdi");
    } finally {
      setLoadingId(null);
    }
  };

  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-[400px] animate-fade-in">
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <AsptexLogo variant="full" size={34} />
        </div>

        <div className="glass-card rounded-xl p-6">
          <div className="mb-5 text-center">
            <h1 className="text-[17px] font-bold text-foreground">
              {t("Kompaniyani tanlang", "Выберите компанию")}
            </h1>
            <p className="mt-1 text-[13px] text-foreground-muted">{user?.full_name}</p>
          </div>

          <div className="space-y-2">
            {companies.map((company) => (
              <button
                key={company.id}
                onClick={() => handleSelectCompany(company.id, company.role)}
                disabled={!!loadingId}
                className={cn(
                  "group w-full flex items-center gap-3.5 rounded-xl border border-border p-3.5",
                  "hover:border-primary hover:bg-primary-light transition-all duration-150",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg",
                    "bg-primary-light text-primary group-hover:bg-primary group-hover:text-white",
                    "transition-colors"
                  )}
                >
                  <Building2 size={18} />
                </div>
                <div className="flex-1 text-left">
                  <p className="text-[14px] font-semibold text-foreground">{company.name}</p>
                  <p className="text-[12px] text-foreground-muted">
                    {ROLE_LABELS[company.role]?.[language] || company.role}
                  </p>
                </div>
                {loadingId === company.id ? (
                  <Loader2 size={16} className="text-primary animate-spin flex-shrink-0" />
                ) : (
                  <ChevronRight
                    size={16}
                    className="flex-shrink-0 text-foreground-subtle group-hover:text-primary transition-colors"
                  />
                )}
              </button>
            ))}
          </div>

          <button
            onClick={() => { clearAuth(); router.push("/login"); }}
            className="mt-4 w-full py-2 text-[12px] text-foreground-muted hover:text-foreground transition-colors"
          >
            {t("Boshqa akkaunt bilan kirish", "Войти с другим аккаунтом")}
          </button>
        </div>
      </div>
    </div>
  );
}

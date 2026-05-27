"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Building2, ChevronRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/auth";
import type { UserRole } from "@/lib/types";

const ROLE_LABELS: Record<UserRole, { uz: string; ru: string }> = {
  ADMIN: { uz: "Administrator", ru: "Администратор" },
  DIRECTOR: { uz: "Direktor", ru: "Директор" },
  DEPUTY_DIRECTOR: { uz: "Direktor muovini", ru: "Зам. директора" },
  WH_RAW: { uz: "Xom ashyo ombori", ru: "Склад сырья" },
  WH_FINISHED: { uz: "Tayyor mahsulot ombori", ru: "Склад готовой продукции" },
  PRODUCTION: { uz: "Ishlab chiqarish", ru: "Производство" },
  ACCOUNTANT: { uz: "Buxgalter", ru: "Бухгалтер" },
};

export default function SelectCompanyPage() {
  const router = useRouter();
  const { companies, user, setCompanyContext, language, clearAuth } = useAuthStore();
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      router.replace("/login");
    }
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

  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <div className="text-center mb-6">
            <h1 className="text-xl font-bold text-slate-900">
              {t("Kompaniyani tanlang", "Выберите компанию")}
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              {user?.full_name}
            </p>
          </div>

          <div className="space-y-3">
            {companies.map((company) => (
              <button
                key={company.id}
                onClick={() => handleSelectCompany(company.id, company.role)}
                disabled={!!loadingId}
                className="w-full flex items-center gap-4 p-4 border border-slate-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-all group disabled:opacity-50"
              >
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-blue-200">
                  <Building2 size={20} className="text-blue-600" />
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium text-slate-900">{company.name}</p>
                  <p className="text-sm text-slate-500">
                    {ROLE_LABELS[company.role]?.[language] || company.role}
                  </p>
                </div>
                {loadingId === company.id ? (
                  <Loader2 size={18} className="text-blue-600 animate-spin" />
                ) : (
                  <ChevronRight size={18} className="text-slate-400 group-hover:text-blue-600" />
                )}
              </button>
            ))}
          </div>

          <button
            onClick={() => { clearAuth(); router.push("/login"); }}
            className="w-full mt-4 text-sm text-slate-500 hover:text-slate-700 py-2"
          >
            {t("Chiqish", "Выйти")}
          </button>
        </div>
      </div>
    </div>
  );
}

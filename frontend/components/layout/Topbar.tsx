"use client";

import { useRouter } from "next/navigation";
import { Bell, ChevronDown, LogOut, User } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/auth";

const ROLE_LABELS: Record<string, { uz: string; ru: string }> = {
  ADMIN: { uz: "Administrator", ru: "Администратор" },
  DIRECTOR: { uz: "Direktor", ru: "Директор" },
  DEPUTY_DIRECTOR: { uz: "Direktor muovini", ru: "Зам. директора" },
  WH_RAW: { uz: "Xom ashyo ombori", ru: "Склад сырья" },
  WH_FINISHED: { uz: "Tayyor mahsulot", ru: "Склад готовой пр." },
  PRODUCTION: { uz: "Ishlab chiqarish", ru: "Производство" },
  ACCOUNTANT: { uz: "Buxgalter", ru: "Бухгалтер" },
};

export function Topbar() {
  const router = useRouter();
  const { user, companies, activeCompanyId, activeRole, language, setLanguage, clearAuth, refreshToken } = useAuthStore();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const activeCompany = companies.find((c) => c.id === activeCompanyId);

  const handleLogout = async () => {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {}
    clearAuth();
    router.push("/login");
    toast.success(language === "uz" ? "Tizimdan chiqildi" : "Вы вышли из системы");
  };

  const initials = user?.full_name
    ?.split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase() || "?";

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
      {/* Company name */}
      <div className="flex items-center gap-2">
        <span className="font-semibold text-slate-800">{activeCompany?.name}</span>
        {activeRole && (
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
            {ROLE_LABELS[activeRole]?.[language] || activeRole}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        {/* Language switcher */}
        <div className="flex gap-1">
          {(["uz", "ru"] as const).map((lang) => (
            <button
              key={lang}
              onClick={() => setLanguage(lang)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                language === lang
                  ? "bg-blue-600 text-white"
                  : "text-slate-500 hover:bg-slate-100"
              }`}
            >
              {lang.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Notifications */}
        <button className="relative p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg">
          <Bell size={18} />
          {/* Badge — Sprint 5 will wire up real alerts */}
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-semibold">{initials}</span>
            </div>
            <span className="text-sm font-medium text-slate-700 hidden md:block">
              {user?.full_name?.split(" ")[0]}
            </span>
            <ChevronDown size={14} className="text-slate-400 hidden md:block" />
          </button>

          {showUserMenu && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowUserMenu(false)}
              />
              <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-slate-200 rounded-xl shadow-lg z-20 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-100">
                  <p className="text-sm font-semibold text-slate-900">{user?.full_name}</p>
                  <p className="text-xs text-slate-500">{user?.username}</p>
                </div>
                <div className="p-2">
                  <button
                    onClick={() => { router.push("/select-company"); setShowUserMenu(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 rounded-lg"
                  >
                    <User size={15} />
                    {language === "uz" ? "Kompaniya almashtirish" : "Сменить компанию"}
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg"
                  >
                    <LogOut size={15} />
                    {language === "uz" ? "Chiqish" : "Выйти"}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

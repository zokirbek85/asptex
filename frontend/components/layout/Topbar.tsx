"use client";

import { useRouter } from "next/navigation";
import { Bell, Building2, ChevronDown, LogOut, Moon, Sun, User } from "lucide-react";
import { useState } from "react";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { authApi } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/stores/auth";
import { cn } from "@/lib/utils";

const ROLE_LABELS: Record<string, { uz: string; ru: string }> = {
  ADMIN:           { uz: "Administrator",     ru: "Администратор" },
  DIRECTOR:        { uz: "Direktor",           ru: "Директор" },
  DEPUTY_DIRECTOR: { uz: "Direktor muovini",   ru: "Зам. директора" },
  WH_RAW:          { uz: "Xom ashyo ombori",   ru: "Склад сырья" },
  WH_FINISHED:     { uz: "Tayyor mahsulot",    ru: "Готовая продукция" },
  PRODUCTION:      { uz: "Ishlab chiqarish",   ru: "Производство" },
  ACCOUNTANT:      { uz: "Buxgalter",          ru: "Бухгалтер" },
};

export function Topbar() {
  const router = useRouter();
  const { user, companies, activeCompanyId, activeRole, language, setLanguage, clearAuth, refreshToken } =
    useAuthStore();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const { theme, setTheme } = useTheme();

  const activeCompany = companies.find((c) => c.id === activeCompanyId);

  const handleLogout = async () => {
    setShowUserMenu(false);
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } catch {}
    clearAuth();
    router.push("/login");
    toast.success(language === "uz" ? "Tizimdan chiqildi" : "Вы вышли из системы");
  };

  const initials =
    user?.full_name
      ?.split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "?";

  return (
    <header
      className={cn(
        "flex h-[60px] flex-shrink-0 items-center justify-between px-5",
        "bg-surface border-b border-border"
      )}
    >
      {/* ── Left: company + role ─────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Building2 size={15} className="text-foreground-muted flex-shrink-0" />
          <span className="text-[14px] font-semibold text-foreground">
            {activeCompany?.name || "—"}
          </span>
        </div>
        {activeRole && (
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium",
              "bg-primary-light text-primary"
            )}
          >
            {ROLE_LABELS[activeRole]?.[language] || activeRole}
          </span>
        )}
      </div>

      {/* ── Right: actions ──────────────────────────────── */}
      <div className="flex items-center gap-1">
        {/* Language switcher */}
        <div className="flex items-center rounded-lg border border-border overflow-hidden mr-1">
          {(["uz", "ru"] as const).map((lang) => (
            <button
              key={lang}
              onClick={() => setLanguage(lang)}
              className={cn(
                "px-2.5 py-1 text-[11px] font-semibold transition-colors",
                language === lang
                  ? "bg-primary text-white"
                  : "text-foreground-muted hover:bg-muted hover:text-foreground"
              )}
            >
              {lang.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
            "text-foreground-muted hover:bg-muted hover:text-foreground"
          )}
          title={theme === "dark" ? "Switch to light" : "Switch to dark"}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Notifications */}
        <button
          className={cn(
            "relative flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
            "text-foreground-muted hover:bg-muted hover:text-foreground"
          )}
        >
          <Bell size={16} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-danger" />
        </button>

        {/* User menu */}
        <div className="relative ml-1">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={cn(
              "flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors",
              "hover:bg-muted"
            )}
          >
            <div
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full text-white text-[11px] font-bold",
                "bg-primary"
              )}
            >
              {initials}
            </div>
            <span className="hidden text-[13px] font-medium text-foreground md:block">
              {user?.full_name?.split(" ")[0]}
            </span>
            <ChevronDown size={13} className="hidden text-foreground-muted md:block" />
          </button>

          {showUserMenu && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setShowUserMenu(false)} />
              <div
                className={cn(
                  "absolute right-0 top-full mt-1.5 z-40 w-56 overflow-hidden",
                  "rounded-xl border border-border bg-surface shadow-card-lg animate-fade-in"
                )}
              >
                <div className="border-b border-border px-4 py-3">
                  <p className="text-[13px] font-semibold text-foreground">{user?.full_name}</p>
                  <p className="text-[11px] text-foreground-muted mt-0.5">{user?.username}</p>
                </div>
                <div className="p-1.5">
                  <button
                    onClick={() => { router.push("/select-company"); setShowUserMenu(false); }}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px]",
                      "text-foreground hover:bg-muted transition-colors"
                    )}
                  >
                    <User size={14} className="text-foreground-muted" />
                    {language === "uz" ? "Kompaniya almashtirish" : "Сменить компанию"}
                  </button>
                  <button
                    onClick={handleLogout}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px]",
                      "text-danger hover:bg-danger-light transition-colors"
                    )}
                  >
                    <LogOut size={14} />
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

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Box,
  Building2,
  ChevronRight,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Package,
  Scale,
  Ship,
  SlidersHorizontal,
  Users,
  Wheat,
  Layers,
  Trash2,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth";
import type { CompanyType, UserRole } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AsptexLogo } from "@/components/brand/AsptexLogo";

interface NavGroup {
  label?: { uz: string; ru: string };
  items: NavItem[];
  // Omit to show for every company type (e.g. shared Admin group).
  companyTypes?: CompanyType[];
}

interface NavItem {
  href: string;
  label: { uz: string; ru: string };
  icon: React.ReactNode;
  roles?: UserRole[];
  // Omit to show for every company type.
  companyTypes?: CompanyType[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    items: [
      {
        href: "/dashboard",
        label: { uz: "Boshqaruv paneli", ru: "Дашборд" },
        icon: <LayoutDashboard size={17} />,
        roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "ACCOUNTANT", "WH_RAW", "WH_FINISHED", "PRODUCTION"],
      },
    ],
  },
  {
    label: { uz: "Ombor", ru: "Склад" },
    companyTypes: ["YARN_SPINNING"],
    items: [
      {
        href: "/warehouse/daily-report",
        label: { uz: "Kunlik hisobot", ru: "Суточный отчёт" },
        icon: <ClipboardList size={17} />,
        roles: ["ADMIN", "DEPUTY_DIRECTOR", "WH_RAW", "WH_FINISHED", "PRODUCTION"],
      },
      {
        href: "/warehouse/stock",
        label: { uz: "Qoldiqlar", ru: "Остатки" },
        icon: <Box size={17} />,
        roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "WH_RAW", "WH_FINISHED", "ACCOUNTANT"],
      },
      {
        href: "/warehouse/shipments",
        label: { uz: "Jo'natmalar", ru: "Отгрузки" },
        icon: <Ship size={17} />,
        roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "WH_FINISHED", "ACCOUNTANT"],
      },
    ],
  },
  {
    label: { uz: "Katalog", ru: "Каталог" },
    items: [
      {
        href: "/master/lots",
        label: { uz: "Lotlar", ru: "Лоты" },
        icon: <FileText size={17} />,
        roles: ["ADMIN", "DEPUTY_DIRECTOR", "ACCOUNTANT"],
        companyTypes: ["YARN_SPINNING"],
      },
      {
        href: "/master/counterparties",
        label: { uz: "Kontragentlar", ru: "Контрагенты" },
        icon: <Users size={17} />,
        roles: ["ADMIN", "DEPUTY_DIRECTOR", "ACCOUNTANT"],
      },
      {
        href: "/master/contracts",
        label: { uz: "Shartnomalar", ru: "Договоры" },
        icon: <FileText size={17} />,
        roles: ["ADMIN", "DEPUTY_DIRECTOR", "ACCOUNTANT"],
      },
      {
        href: "/master/counts",
        label: { uz: "Count katalogi", ru: "Каталог каунтов" },
        icon: <Package size={17} />,
        roles: ["ADMIN", "DEPUTY_DIRECTOR"],
        companyTypes: ["YARN_SPINNING"],
      },
    ],
  },
  {
    label: { uz: "Tolling", ru: "Толлинг" },
    companyTypes: ["YARN_SPINNING"],
    items: [
      {
        href: "/tolling/active-lot",
        label: { uz: "Aktiv Lot", ru: "Активный лот" },
        icon: <Layers size={17} />,
        roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "ACCOUNTANT", "WH_FINISHED"],
      },
      {
        href: "/tolling/distributions",
        label: { uz: "Taqsimotlar", ru: "Распределения" },
        icon: <ClipboardList size={17} />,
        roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "ACCOUNTANT", "WH_FINISHED"],
      },
      {
        href: "/tolling/reports/lot-summary",
        label: { uz: "Lot xulosasi", ru: "Сводка лота" },
        icon: <BarChart3 size={17} />,
        roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "ACCOUNTANT", "WH_FINISHED"],
      },
    ],
  },
  {
    label: { uz: "Boshqaruv", ru: "Управление" },
    items: [
      {
        href: "/admin/opening-balance",
        label: { uz: "Boshlang'ich qoldiq", ru: "Нач. остаток" },
        icon: <Scale size={17} />,
        roles: ["ADMIN"],
      },
      {
        href: "/admin/adjustments",
        label: { uz: "Korrekturalar", ru: "Корректировки" },
        icon: <SlidersHorizontal size={17} />,
        roles: ["ADMIN"],
      },
      {
        href: "/admin/audit",
        label: { uz: "Audit jurnali", ru: "Журнал аудита" },
        icon: <BarChart3 size={17} />,
        roles: ["ADMIN"],
      },
      {
        href: "/admin/users",
        label: { uz: "Foydalanuvchilar", ru: "Пользователи" },
        icon: <Users size={17} />,
        roles: ["ADMIN"],
      },
      {
        href: "/admin/companies",
        label: { uz: "Kompaniyalar", ru: "Компании" },
        icon: <Building2 size={17} />,
        roles: ["ADMIN"],
      },
      {
        href: "/admin/warehouses",
        label: { uz: "Omborlar", ru: "Склады" },
        icon: <Wheat size={17} />,
        roles: ["ADMIN"],
      },
      {
        href: "/admin/data-reset",
        label: { uz: "Bazani tozalash", ru: "Очистка данных" },
        icon: <Trash2 size={17} />,
        roles: ["ADMIN"],
      },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { activeRole, activeCompanyId, companies, language } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const activeCompanyType = companies.find((c) => c.id === activeCompanyId)?.company_type;

  const matchesCompanyType = (companyTypes?: CompanyType[]) =>
    !companyTypes || (!!activeCompanyType && companyTypes.includes(activeCompanyType));

  const isVisible = (item: NavItem) =>
    (!item.roles || (activeRole && item.roles.includes(activeRole))) &&
    matchesCompanyType(item.companyTypes);

  return (
    <aside
      className={cn(
        "relative flex h-screen flex-col transition-all duration-200 ease-in-out flex-shrink-0",
        "bg-sidebar-bg border-r border-sidebar-border",
        collapsed ? "w-[64px]" : "w-[220px]"
      )}
    >
      {/* ── Logo ──────────────────────────────────────────── */}
      <div
        className={cn(
          "flex h-[60px] items-center border-b border-sidebar-border flex-shrink-0",
          collapsed ? "justify-center px-0" : "px-5"
        )}
      >
        {collapsed ? (
          <AsptexLogo variant="mark" size={30} onDark />
        ) : (
          <AsptexLogo variant="full" size={30} onDark />
        )}
      </div>

      {/* ── Navigation ────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto py-3">
        {NAV_GROUPS.map((group, gi) => {
          if (!matchesCompanyType(group.companyTypes)) return null;
          const visibleItems = group.items.filter(isVisible);
          if (visibleItems.length === 0) return null;

          return (
            <div key={gi} className={cn("mb-1", gi > 0 && "mt-2")}>
              {/* Group label */}
              {group.label && !collapsed && (
                <p className="mb-1 px-5 text-[10px] font-semibold uppercase tracking-widest text-sidebar-text opacity-50">
                  {group.label[language]}
                </p>
              )}
              {group.label && collapsed && (
                <div className="my-2 mx-3 h-px bg-sidebar-border opacity-50" />
              )}

              <ul className="space-y-0.5 px-2">
                {visibleItems.map((item) => {
                  const isActive =
                    item.href === "/dashboard"
                      ? pathname === "/dashboard"
                      : pathname.startsWith(item.href);

                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        title={collapsed ? item.label[language] : undefined}
                        className={cn(
                          "group flex items-center gap-3 rounded-[8px] px-3 py-2.5 text-[13px] font-medium transition-all duration-150",
                          isActive
                            ? "bg-sidebar-active text-sidebar-text-active shadow-sm nav-active"
                            : "text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active",
                          collapsed && "justify-center px-0 py-2.5 mx-auto w-10 h-10"
                        )}
                      >
                        <span className={cn("flex-shrink-0", !isActive && "opacity-80")}>
                          {item.icon}
                        </span>
                        {!collapsed && (
                          <span className="truncate">{item.label[language]}</span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </nav>

      {/* ── Collapse toggle ───────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-sidebar-border p-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-[8px] py-2 text-sidebar-text",
            "hover:bg-sidebar-hover hover:text-sidebar-text-active transition-colors text-[13px]",
            collapsed && "py-2"
          )}
        >
          <ChevronRight
            size={15}
            className={cn("transition-transform duration-200", !collapsed && "rotate-180")}
          />
          {!collapsed && (
            <span className="text-[12px]">
              {language === "uz" ? "Yig'ish" : "Свернуть"}
            </span>
          )}
        </button>
      </div>
    </aside>
  );
}

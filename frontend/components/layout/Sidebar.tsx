"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  BarChart3, Box, ChevronLeft, ClipboardList, FileText,
  LayoutDashboard, Package, Recycle, Settings, Ship, Users, Wheat,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth";
import type { UserRole } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: { uz: string; ru: string };
  icon: React.ReactNode;
  roles?: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    label: { uz: "Dashboard", ru: "Dashboard" },
    icon: <LayoutDashboard size={18} />,
    roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "ACCOUNTANT"],
  },
  {
    href: "/daily-report",
    label: { uz: "Kunlik hisobot", ru: "Суточный отчёт" },
    icon: <ClipboardList size={18} />,
    roles: ["ADMIN", "DEPUTY_DIRECTOR", "WH_RAW", "WH_FINISHED"],
  },
  {
    href: "/warehouses/finished-goods",
    label: { uz: "Tayyor mahsulot", ru: "Готовая продукция" },
    icon: <Box size={18} />,
    roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "WH_FINISHED", "ACCOUNTANT"],
  },
  {
    href: "/warehouses/raw-cotton",
    label: { uz: "Xom ashyo", ru: "Сырьё" },
    icon: <Wheat size={18} />,
    roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "WH_RAW", "ACCOUNTANT"],
  },
  {
    href: "/warehouses/waste",
    label: { uz: "Chiqindilar", ru: "Отходы" },
    icon: <Recycle size={18} />,
    roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "WH_RAW", "ACCOUNTANT"],
  },
  {
    href: "/warehouses/packaging",
    label: { uz: "Tara", ru: "Тара" },
    icon: <Package size={18} />,
  },
  {
    href: "/shipments",
    label: { uz: "Jo'natmalar", ru: "Отгрузки" },
    icon: <Ship size={18} />,
    roles: ["ADMIN", "DIRECTOR", "DEPUTY_DIRECTOR", "WH_FINISHED", "ACCOUNTANT"],
  },
  {
    href: "/master/lots",
    label: { uz: "Lotlar", ru: "Лоты" },
    icon: <FileText size={18} />,
    roles: ["ADMIN", "DEPUTY_DIRECTOR", "ACCOUNTANT"],
  },
  {
    href: "/master/counterparties",
    label: { uz: "Kontragentlar", ru: "Контрагенты" },
    icon: <Users size={18} />,
    roles: ["ADMIN", "DEPUTY_DIRECTOR", "ACCOUNTANT"],
  },
  {
    href: "/admin/users",
    label: { uz: "Boshqaruv", ru: "Управление" },
    icon: <Settings size={18} />,
    roles: ["ADMIN"],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { activeRole, language } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (activeRole && item.roles.includes(activeRole))
  );

  return (
    <aside
      className={cn(
        "h-screen bg-white border-r border-slate-200 flex flex-col transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-slate-200">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <span className="text-white font-bold text-sm">A</span>
        </div>
        {!collapsed && (
          <span className="font-bold text-slate-900 text-lg tracking-tight">ASPTEX</span>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-0.5 px-2">
          {visibleItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                    isActive
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  )}
                  title={collapsed ? item.label[language] : undefined}
                >
                  <span className="flex-shrink-0">{item.icon}</span>
                  {!collapsed && <span>{item.label[language]}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="p-3 border-t border-slate-200">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <ChevronLeft
            size={18}
            className={cn("transition-transform", collapsed && "rotate-180")}
          />
        </button>
      </div>
    </aside>
  );
}

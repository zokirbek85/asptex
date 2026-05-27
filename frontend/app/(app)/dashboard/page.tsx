"use client";

import { useAuthStore } from "@/lib/stores/auth";

export default function DashboardPage() {
  const { user, activeRole, language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">
          {t("Boshqaruv paneli", "Панель управления")}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          {t("Xush kelibsiz", "Добро пожаловать")}, {user?.full_name}
        </p>
      </div>

      {/* KPI Cards — Sprint 5 will fill these with real data */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: t("Tayyor mahsulot", "Готовая продукция"), value: "—", color: "bg-blue-50 border-blue-200 text-blue-700" },
          { label: t("Xom ashyo", "Сырьё"), value: "—", color: "bg-green-50 border-green-200 text-green-700" },
          { label: t("Bugungi jo'natmalar", "Отгрузки сегодня"), value: "—", color: "bg-amber-50 border-amber-200 text-amber-700" },
          { label: t("Ogohlantirishlar", "Оповещения"), value: "—", color: "bg-red-50 border-red-200 text-red-700" },
        ].map((card) => (
          <div key={card.label} className={`border rounded-xl p-5 ${card.color}`}>
            <p className="text-sm font-medium opacity-70">{card.label}</p>
            <p className="text-3xl font-bold mt-2">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400">
        <p className="text-sm">{t("Tizim sozlanmoqda...", "Система настраивается...")}</p>
        <p className="text-xs mt-1">Sprint 5 — Dashboard</p>
      </div>
    </div>
  );
}

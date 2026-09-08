"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Sprout, Package, TrendingUp, Landmark } from "lucide-react";

import { ginningDashboardApi } from "@/lib/api/ginningDashboard";
import { useAuthStore } from "@/lib/stores/auth";
import { cn } from "@/lib/utils";

function KpiCard({ label, value, sub, gradient, icon: Icon }: {
  label: string; value: string; sub?: string; gradient: string; icon: React.ElementType;
}) {
  return (
    <div className={cn("relative overflow-hidden rounded-xl p-5 text-white", gradient)}>
      <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-white/10" />
      <div className="relative flex items-start justify-between">
        <div>
          <p className="mb-2 text-[12px] font-medium text-white/75">{label}</p>
          <p className="text-[24px] font-bold leading-none tracking-tight">{value}</p>
          {sub && <p className="mt-1.5 text-[12px] text-white/65">{sub}</p>}
        </div>
        <div className="rounded-xl bg-white/15 p-2.5"><Icon size={18} className="text-white" /></div>
      </div>
    </div>
  );
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-2 shadow-card-md text-[12px]">
      <p className="mb-1 font-semibold text-foreground">{label}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-foreground-muted">{p.name}:</span>
          <span className="font-medium text-foreground">{Number(p.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export default function GinningDashboardPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);

  const { data: summary } = useQuery({
    queryKey: ["ginning-dashboard-summary"],
    queryFn: () => ginningDashboardApi.getSummary(),
  });
  const { data: trend } = useQuery({
    queryKey: ["ginning-receiving-trend"],
    queryFn: () => ginningDashboardApi.getReceivingTrend(30),
  });
  const { data: distribution } = useQuery({
    queryKey: ["ginning-output-distribution"],
    queryFn: () => ginningDashboardApi.getOutputDistribution(),
  });

  const fmt = (v: number | undefined) => Number(v ?? 0).toLocaleString("uz-UZ", { maximumFractionDigits: 0 });

  return (
    <div>
      <h1 className="mb-6 text-xl font-bold text-gray-900">{t("Ginning boshqaruv paneli", "Дашборд джинирования")}</h1>

      <div className="mb-6 grid grid-cols-4 gap-4">
        <KpiCard
          label={t("Qabul qilingan paxta", "Принято хлопка")}
          value={`${fmt(summary?.raw_cotton_received_kg)} kg`}
          sub={`${t("Mavjud", "Доступно")}: ${fmt(summary?.raw_cotton_available_kg)} kg`}
          gradient="kpi-gradient-blue" icon={Sprout}
        />
        <KpiCard
          label={t("Tola ishlab chiqarildi", "Произведено волокна")}
          value={`${fmt(summary?.fiber_produced_kg)} kg`}
          sub={`${t("Unum", "Выход")}: ${Number(summary?.fiber_yield_pct ?? 0).toFixed(1)}%`}
          gradient="kpi-gradient-teal" icon={Package}
        />
        <KpiCard
          label={t("Birja savdosi", "Биржевые продажи")}
          value={fmt(summary?.exchange_sales_value)}
          sub={`${fmt(summary?.exchange_sales_kg)} kg`}
          gradient="kpi-gradient-purple" icon={TrendingUp}
        />
        <KpiCard
          label={t("Fermer qarzdorligi", "Задолженность фермерам")}
          value={fmt(summary?.farmer_payable_total)}
          sub={`${t("To'langan", "Оплачено")}: ${fmt(summary?.farmer_paid_total)}`}
          gradient="kpi-gradient-amber" icon={Landmark}
        />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4">
        <div className="glass-card rounded-xl p-4">
          <p className="mb-3 text-[13px] font-semibold text-foreground">{t("Paxta qabuli (30 kun)", "Приём хлопка (30 дней)")}</p>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={trend ?? []} margin={{ left: -10, right: 4 }}>
              <defs>
                <linearGradient id="grad-receiving" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1565C0" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#1565C0" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="quantity_kg" name="kg" stroke="#1565C0" strokeWidth={2} fill="url(#grad-receiving)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card rounded-xl p-4">
          <p className="mb-3 text-[13px] font-semibold text-foreground">{t("Mahsulot taqsimoti", "Распределение продукции")}</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={distribution ?? []} margin={{ left: -10, right: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="value" name="kg" fill="#00A88E" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-[13px]">
        <div className="glass-card rounded-xl p-4">
          <p className="text-foreground-muted">{t("Ochiq buntlar", "Открытые бунты")}</p>
          <p className="text-[18px] font-bold">{summary?.open_bunts_count ?? 0}</p>
        </div>
        <div className="glass-card rounded-xl p-4">
          <p className="text-foreground-muted">{t("Qoralama buyurtmalar", "Черновики заказов")}</p>
          <p className="text-[18px] font-bold">{summary?.draft_production_orders_count ?? 0}</p>
        </div>
        <div className="glass-card rounded-xl p-4">
          <p className="text-foreground-muted">{t("Kompaniyalararo o'tkazma", "Межкорп. переводы")}</p>
          <p className="text-[18px] font-bold">{fmt(summary?.intercompany_transfers_kg)} kg</p>
        </div>
      </div>
    </div>
  );
}

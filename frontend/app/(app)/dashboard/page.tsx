"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle, ArrowRight, Box, ChevronDown, ChevronUp, Info, Package, Ship, TrendingUp, Warehouse,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";

import {
  dashboardApi,
  type DashboardAlert,
  type RecentShipment,
  type SlowStockItem,
  type StockByLot,
} from "@/lib/api/dashboard";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";
import type { ShipmentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── KPI Card ───────────────────────────────────────────────────────────────
function KpiCard({
  label, value, sub, gradient, icon: Icon, delta,
}: {
  label: string;
  value: string;
  sub?: string;
  gradient: string;
  icon: React.ElementType;
  delta?: string;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl p-5 text-white",
        gradient
      )}
    >
      {/* Background decoration */}
      <div className="absolute -right-4 -top-4 h-20 w-20 rounded-full bg-white/10" />
      <div className="absolute -right-1 bottom-2 h-10 w-10 rounded-full bg-white/5" />

      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-[12px] font-medium text-white/75 mb-2">{label}</p>
          <p className="text-[26px] font-bold leading-none tracking-tight">{value}</p>
          {sub && <p className="mt-1.5 text-[12px] text-white/65">{sub}</p>}
          {delta && (
            <div className="mt-2 flex items-center gap-1">
              <TrendingUp size={11} className="text-white/70" />
              <span className="text-[11px] text-white/70">{delta}</span>
            </div>
          )}
        </div>
        <div className="rounded-xl bg-white/15 p-2.5">
          <Icon size={18} className="text-white" />
        </div>
      </div>
    </div>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-2 shadow-card-md text-[12px]">
      <p className="font-semibold text-foreground mb-1">{label}</p>
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

// ── Section title ──────────────────────────────────────────────────────────
function SectionTitle({
  title,
  action,
  href,
}: {
  title: string;
  action?: string;
  href?: string;
}) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-[13px] font-semibold text-foreground">{title}</h2>
      {action && href && (
        <Link
          href={href}
          className="flex items-center gap-1 text-[12px] font-medium text-primary hover:underline"
        >
          {action}
          <ArrowRight size={12} />
        </Link>
      )}
    </div>
  );
}

// ── Card wrapper ───────────────────────────────────────────────────────────
function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "glass-card rounded-xl p-4",
        className
      )}
    >
      {children}
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Qoralama",
  SUBMITTED: "Yuborilgan",
};
const STATUS_COLOR: Record<string, string> = {
  DRAFT: "bg-yellow-100 text-yellow-700",
  SUBMITTED: "bg-blue-100 text-blue-700",
};

// ── Main dashboard ─────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { user, language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const [unclosedExpanded, setUnclosedExpanded] = useState(false);

  const { data: summary, isLoading: sumLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: dashboardApi.summary,
  });
  const { data: chartData } = useQuery({
    queryKey: ["dashboard-fg-chart"],
    queryFn: dashboardApi.fgChart,
  });
  const { data: lotStock } = useQuery({
    queryKey: ["dashboard-stock-by-lot"],
    queryFn: dashboardApi.stockByLot,
  });
  const { data: slowStock } = useQuery({
    queryKey: ["dashboard-slow-stock"],
    queryFn: dashboardApi.slowStock,
  });
  const { data: recentShipments } = useQuery({
    queryKey: ["dashboard-recent-shipments"],
    queryFn: dashboardApi.recentShipments,
  });
  const { data: alerts } = useQuery({
    queryKey: ["dashboard-alerts"],
    queryFn: dashboardApi.alerts,
    refetchInterval: 60_000,
  });

  const { data: unclosedReports } = useQuery({
    queryKey: ["dashboard-unclosed-reports"],
    queryFn: dashboardApi.unclosedReports,
    enabled: unclosedExpanded,
  });

  const chartSeries = chartData
    ? chartData.production.map((p, i) => ({
        date: p.date.slice(5),
        [t("Ishlab chiqarish", "Производство")]: Number(p.value),
        [t("Jo'natmalar", "Отгрузки")]: Number(chartData.shipments[i]?.value ?? 0),
      }))
    : [];

  const fmt = (n: number | undefined) =>
    n === undefined ? "—" : Number(n).toLocaleString("uz-UZ", { maximumFractionDigits: 0 });

  const lotColumns: ColumnDef<StockByLot>[] = [
    {
      accessorKey: "lot_number",
      header: "Lot",
      cell: ({ getValue }) => (
        <span className="font-mono text-[12px] font-semibold text-foreground">
          {getValue() as string}
        </span>
      ),
    },
    {
      accessorKey: "total_kg",
      header: t("Miqdor, kg", "Количество, кг"),
      cell: ({ getValue }) => (
        <span className="font-medium text-foreground">
          {Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 0 })}
        </span>
      ),
    },
    {
      accessorKey: "total_bags",
      header: t("Qoplar", "Мешки"),
    },
  ];

  const slowColumns: ColumnDef<SlowStockItem>[] = [
    {
      accessorKey: "identifier",
      header: t("Mahsulot", "Продукция"),
      cell: ({ getValue }) => (
        <span className="font-medium text-foreground">{getValue() as string}</span>
      ),
    },
    {
      accessorKey: "warehouse_type",
      header: t("Ombor", "Склад"),
      cell: ({ getValue }) => (
        <Badge variant="info">{getValue() as string}</Badge>
      ),
    },
    {
      accessorKey: "quantity_kg",
      header: "kg",
      cell: ({ getValue }) => Number(getValue()).toLocaleString(),
    },
    {
      accessorKey: "days_idle",
      header: t("Kun", "Дней"),
      cell: ({ getValue }) => (
        <Badge variant="warning">{getValue() as number} {t("kun", "д.")}</Badge>
      ),
    },
  ];

  const shipmentColumns: ColumnDef<RecentShipment>[] = [
    {
      accessorKey: "shipment_number",
      header: t("Raqam", "Номер"),
      cell: ({ getValue }) => (
        <span className="font-mono text-[12px] font-semibold text-primary">
          {getValue() as string}
        </span>
      ),
    },
    {
      accessorKey: "shipment_date",
      header: t("Sana", "Дата"),
      cell: ({ getValue }) => (
        <span className="text-foreground-muted">{formatDate(getValue() as string, language)}</span>
      ),
    },
    {
      accessorKey: "total_kg",
      header: "kg",
      cell: ({ getValue }) => (
        <span className="font-medium">{Number(getValue()).toLocaleString()}</span>
      ),
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => <StatusBadge status={getValue() as string} />,
    },
  ];

  const prodKey = t("Ishlab chiqarish", "Производство");
  const shipKey = t("Jo'natmalar", "Отгрузки");

  return (
    <div className="space-y-5 animate-fade-in">
      {/* ── Header ──────────────────────────────────────── */}
      <div>
        <h1 className="text-[20px] font-bold text-foreground">
          {t("Boshqaruv paneli", "Панель управления")}
        </h1>
        <p className="mt-0.5 text-[13px] text-foreground-muted">
          {t("Xush kelibsiz", "Добро пожаловать")}, {user?.full_name}
        </p>
      </div>

      {/* ── KPI Cards ───────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          label={t("Tayyor mahsulot", "Готовая продукция")}
          value={sumLoading ? "—" : fmt(summary?.finished_goods_kg)}
          sub="kg"
          gradient="kpi-gradient-blue"
          icon={Warehouse}
        />
        <KpiCard
          label={t("Paxta tolasi", "Хлопок-волокно")}
          value={sumLoading ? "—" : fmt(summary?.raw_cotton_kg)}
          sub="kg"
          gradient="kpi-gradient-teal"
          icon={Package}
        />
        <KpiCard
          label={t("Bu oy jo'natmalar", "Отгрузки за месяц")}
          value={sumLoading ? "—" : fmt(summary?.shipments_kg_this_month)}
          sub={`${summary?.shipments_this_month ?? "—"} ${t("ta", "шт.")}`}
          gradient="kpi-gradient-purple"
          icon={Ship}
        />
        <KpiCard
          label={t("Ogohlantirishlar", "Оповещения")}
          value={sumLoading ? "—" : String(alerts?.length ?? 0)}
          sub={t("Faol ogohlantirish", "Активных оповещений")}
          gradient={alerts?.length ? "kpi-gradient-amber" : "bg-gradient-to-br from-slate-500 to-slate-600"}
          icon={AlertTriangle}
        />
      </div>

      {/* ── Charts ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle title={t("Ishlab chiqarish vs Jo'natmalar (30 kun)", "Производство vs Отгрузки (30 дней)")} />
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartSeries} margin={{ left: -10, right: 4 }}>
              <defs>
                <linearGradient id="grad-prod" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1565C0" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#1565C0" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="grad-ship" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00A88E" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#00A88E" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey={prodKey} stroke="#1565C0" strokeWidth={2} fill="url(#grad-prod)" dot={false} />
              <Area type="monotone" dataKey={shipKey} stroke="#00A88E" strokeWidth={2} fill="url(#grad-ship)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <SectionTitle title={t("Lotlar bo'yicha qoldiq (top 10)", "Остатки по лотам (топ 10)")} />
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={lotStock?.slice(0, 10) ?? []} margin={{ left: -10, right: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="lot_number" tick={{ fontSize: 9, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "hsl(var(--foreground-subtle))" }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="total_kg" fill="#1565C0" radius={[4, 4, 0, 0]} name="kg" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* ── Tables ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle
            title={t("60+ kun harakatsiz", "Товары без движения 60+ дней")}
          />
          <DataTable
            data={slowStock ?? []}
            columns={slowColumns}
            isLoading={!slowStock}
            emptyText={t("Harakatsiz mahsulot yo'q", "Нет залежавшихся товаров")}
          />
        </Card>

        <Card>
          <SectionTitle
            title={t("Oxirgi jo'natmalar", "Последние отгрузки")}
            action={t("Barchasi", "Все")}
            href="/warehouse/shipments"
          />
          <DataTable
            data={recentShipments ?? []}
            columns={shipmentColumns}
            isLoading={!recentShipments}
            emptyText={t("Jo'natmalar yo'q", "Отгрузок нет")}
          />
        </Card>
      </div>

      {/* ── Alerts ──────────────────────────────────────── */}
      {alerts && alerts.length > 0 && (
        <Card>
          <SectionTitle title={t("Ogohlantirishlar", "Оповещения")} />
          <div className="space-y-2">
            {alerts.map((alert, idx) => {
              const isUnclosed = alert.alert_type === "UNCLOSED_REPORT";
              return (
                <div key={idx}>
                  <div
                    className={cn(
                      "flex items-start gap-3 rounded-lg px-3 py-2.5 text-[13px]",
                      isUnclosed ? "cursor-pointer select-none" : "",
                      alert.severity === "WARNING"
                        ? "bg-warning-light text-warning"
                        : "bg-primary-light text-primary"
                    )}
                    onClick={isUnclosed ? () => setUnclosedExpanded((v) => !v) : undefined}
                  >
                    {alert.severity === "WARNING" ? (
                      <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
                    ) : (
                      <Info size={14} className="mt-0.5 flex-shrink-0" />
                    )}
                    <span className="flex-1">{alert.message}</span>
                    {isUnclosed && (
                      unclosedExpanded
                        ? <ChevronUp size={14} className="mt-0.5 flex-shrink-0" />
                        : <ChevronDown size={14} className="mt-0.5 flex-shrink-0" />
                    )}
                  </div>

                  {isUnclosed && unclosedExpanded && (
                    <div className="mt-1 rounded-lg border border-slate-200 bg-white overflow-hidden">
                      {!unclosedReports ? (
                        <p className="px-4 py-3 text-[12px] text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</p>
                      ) : unclosedReports.length === 0 ? (
                        <p className="px-4 py-3 text-[12px] text-slate-400">{t("Yopilmagan hisobot yo'q", "Нет незакрытых отчётов")}</p>
                      ) : (
                        <table className="w-full text-[12px]">
                          <thead>
                            <tr className="border-b border-slate-100 text-left text-[11px] font-medium text-slate-500">
                              <th className="px-4 py-2">{t("Sana", "Дата")}</th>
                              <th className="px-4 py-2">{t("Ombor", "Склад")}</th>
                              <th className="px-4 py-2">{t("Holat", "Статус")}</th>
                              <th className="px-4 py-2"></th>
                            </tr>
                          </thead>
                          <tbody>
                            {unclosedReports.map((r) => (
                              <tr key={r.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                                <td className="px-4 py-2 font-mono font-semibold text-slate-700">
                                  {r.report_date}
                                </td>
                                <td className="px-4 py-2 text-slate-600">{r.warehouse_name}</td>
                                <td className="px-4 py-2">
                                  <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-semibold", STATUS_COLOR[r.status] ?? "bg-slate-100 text-slate-600")}>
                                    {STATUS_LABEL[r.status] ?? r.status}
                                  </span>
                                </td>
                                <td className="px-4 py-2 text-right">
                                  <Link
                                    href={`/warehouse/daily-report?warehouse_id=${r.warehouse_id}&date=${r.report_date}`}
                                    className="font-medium text-blue-600 hover:underline"
                                  >
                                    {t("Ochish →", "Открыть →")}
                                  </Link>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

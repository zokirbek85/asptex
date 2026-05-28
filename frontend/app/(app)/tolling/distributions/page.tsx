"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Plus, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

import { tollingApi, type TollingDistributionStatus } from "@/lib/api/tolling";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const STATUS_VARIANT: Record<TollingDistributionStatus, "warning" | "success"> = {
  DRAFT: "warning",
  CONFIRMED: "success",
};

const fmt3 = (v: number) => Number(v).toLocaleString("uz-UZ", { minimumFractionDigits: 3 });

export default function DistributionsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;

  const today = format(new Date(), "yyyy-MM-dd");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data: activeLot } = useQuery({
    queryKey: ["tolling-active-lot"],
    queryFn: () => tollingApi.getActiveLot(),
  });

  const { data: distData, isLoading } = useQuery({
    queryKey: ["tolling-distributions", activeLot?.id, dateFrom, dateTo],
    queryFn: () => tollingApi.listDistributions({
      tolling_lot_id: activeLot?.id,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page_size: 100,
    }),
    enabled: !!activeLot,
  });

  const dists = distData?.items ?? [];

  return (
    <div className="pb-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Taqsimotlar", "Распределения")}</h1>
        {activeLot && (
          <Link href="/tolling/distributions/new">
            <Button size="sm">
              <Plus size={14} /> {t("Yangi taqsimot", "Новое")}
            </Button>
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div className="w-40">
          <Input label={t("Dan", "С")} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="w-40">
          <Input label={t("Gacha", "По")} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        {activeLot && (
          <div className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-700">
            {t("Lot", "Лот")}: <strong>{activeLot.lot_number}</strong>
          </div>
        )}
      </div>

      {!activeLot ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
          {t("Aktiv lot yo'q", "Нет активного лота")} —{" "}
          <Link href="/tolling/active-lot" className="text-blue-600 hover:underline">
            {t("lot ochish", "открыть лот")}
          </Link>
        </div>
      ) : isLoading ? (
        <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>
      ) : dists.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
          {t("Taqsimotlar yo'q", "Распределений нет")}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs font-medium text-slate-500">
                <th className="px-4 py-3">{t("Sana", "Дата")}</th>
                <th className="px-4 py-3 text-right">{t("Tayyor mahsulot (kg)", "ГП (кг)")}</th>
                <th className="px-4 py-3 text-right">{t("Netto (kg)", "Нетто (кг)")}</th>
                <th className="px-4 py-3 text-right">{t("Hizmat haqi (kg)", "Услуга (кг)")}</th>
                <th className="px-4 py-3">{t("Holat", "Статус")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {dists.map((d) => (
                <tr key={d.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                  <td className="px-4 py-2.5 font-medium tabular-nums">{d.distribution_date}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{fmt3(d.daily_fg_kg_total)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-green-700">{fmt3(d.total_net_kg)}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">{fmt3(d.total_fee_kg)}</td>
                  <td className="px-4 py-2.5">
                    <Badge variant={STATUS_VARIANT[d.status]}>{d.status}</Badge>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <Link href={`/tolling/distributions/${d.id}`} className="inline-flex items-center gap-1 text-blue-600 hover:underline text-xs">
                      {t("Ko'rish", "Открыть")} <ChevronRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

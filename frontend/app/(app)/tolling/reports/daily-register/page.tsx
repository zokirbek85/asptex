"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { tollingApi } from "@/lib/api/tolling";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import Link from "next/link";

const fmt3 = (v: number) => Number(v).toLocaleString("uz-UZ", { minimumFractionDigits: 3 });

export default function DailyRegisterPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const sp = useSearchParams();
  const lotIdParam = sp.get("lot_id") ?? "";

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data: activeLot } = useQuery({
    queryKey: ["tolling-active-lot"],
    queryFn: () => tollingApi.getActiveLot(),
  });

  const resolvedLotId = lotIdParam || activeLot?.id || "";

  const { data: register, isLoading } = useQuery({
    queryKey: ["tolling-daily-register", resolvedLotId, dateFrom, dateTo],
    queryFn: () => tollingApi.getDailyRegister({
      tolling_lot_id: resolvedLotId || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  });

  const rows = register?.rows ?? [];

  // Collect unique owners from all lines
  const ownerNames = Array.from(new Set(
    rows.flatMap((r) => r.lines.filter((l) => l.line_type === "OWNER_NET").map((l) => l.counterparty_name ?? ""))
  )).filter(Boolean);

  return (
    <div className="pb-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Kunlik reestr", "Дневной реестр")}</h1>
        <Button
          variant="outline" size="sm"
          onClick={() => tollingApi.exportDailyRegister({
            tolling_lot_id: resolvedLotId || undefined,
            date_from: dateFrom || undefined,
            date_to: dateTo || undefined,
          })}
        >
          <Download size={14} /> Excel
        </Button>
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div className="w-40">
          <Input label={t("Dan", "С")} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </div>
        <div className="w-40">
          <Input label={t("Gacha", "По")} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </div>
        {activeLot && (
          <div className="text-sm text-slate-500">
            {t("Lot", "Лот")}: <strong>{activeLot.lot_number}</strong>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400">
          {t("Ma'lumot yo'q", "Нет данных")}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs font-medium text-slate-500">
                <th className="px-4 py-3">{t("Sana", "Дата")}</th>
                <th className="px-4 py-3 text-right">{t("Jami FG (kg)", "Итого ГП (кг)")}</th>
                {ownerNames.map((name) => (
                  <th key={name} className="px-4 py-3 text-right text-xs">{name}</th>
                ))}
                <th className="px-4 py-3 text-right">{t("Hizmat haqi (kg)", "Услуга (кг)")}</th>
                <th className="px-4 py-3">{t("Holat", "Статус")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const ownerNets: Record<string, number> = {};
                row.lines.forEach((ln) => {
                  if (ln.line_type === "OWNER_NET" && ln.counterparty_name) {
                    ownerNets[ln.counterparty_name] = Number(ln.net_kg);
                  }
                });
                return (
                  <tr key={row.distribution_id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-4 py-2.5 font-medium tabular-nums">{row.distribution_date}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{fmt3(Number(row.daily_fg_kg_total))}</td>
                    {ownerNames.map((name) => (
                      <td key={name} className="px-4 py-2.5 text-right tabular-nums text-green-700">
                        {ownerNets[name] != null ? fmt3(ownerNets[name]) : "—"}
                      </td>
                    ))}
                    <td className="px-4 py-2.5 text-right tabular-nums text-blue-600">{fmt3(Number(row.total_fee_kg))}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant={row.status === "CONFIRMED" ? "success" : "warning"}>{row.status}</Badge>
                    </td>
                    <td className="px-4 py-2.5">
                      <Link href={`/tolling/distributions/${row.distribution_id}`} className="text-xs text-blue-600 hover:underline">
                        {t("Ko'rish", "Открыть")}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t border-slate-200 bg-slate-50 font-semibold text-xs">
                <td className="px-4 py-2.5">{t("JAMI", "ИТОГО")}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {fmt3(rows.reduce((s, r) => s + Number(r.daily_fg_kg_total), 0))}
                </td>
                {ownerNames.map((name) => (
                  <td key={name} className="px-4 py-2.5 text-right tabular-nums text-green-700">
                    {fmt3(rows.reduce((s, r) => {
                      const ln = r.lines.find((l) => l.line_type === "OWNER_NET" && l.counterparty_name === name);
                      return s + (ln ? Number(ln.net_kg) : 0);
                    }, 0))}
                  </td>
                ))}
                <td className="px-4 py-2.5 text-right tabular-nums text-blue-600">
                  {fmt3(rows.reduce((s, r) => s + Number(r.total_fee_kg), 0))}
                </td>
                <td className="px-4 py-2.5"></td>
                <td className="px-4 py-2.5"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}

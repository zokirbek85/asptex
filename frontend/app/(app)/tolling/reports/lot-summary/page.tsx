"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { tollingApi } from "@/lib/api/tolling";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/Button";

const fmt3 = (v: number) => Number(v).toLocaleString("uz-UZ", { minimumFractionDigits: 3 });

export default function LotSummaryPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const sp = useSearchParams();
  const lotId = sp.get("lot_id") ?? "";

  const { data: activeLot } = useQuery({
    queryKey: ["tolling-active-lot"],
    queryFn: () => tollingApi.getActiveLot(),
    enabled: !lotId,
  });

  const resolvedLotId = lotId || activeLot?.id || "";

  const { data: summary, isLoading } = useQuery({
    queryKey: ["tolling-lot-summary", resolvedLotId],
    queryFn: () => tollingApi.getLotSummary(resolvedLotId),
    enabled: !!resolvedLotId,
  });

  return (
    <div className="pb-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Lot xulosasi", "Сводка лота")}</h1>
        {summary && (
          <Button variant="outline" size="sm" onClick={() => tollingApi.exportLotSummary(resolvedLotId)}>
            <Download size={14} /> Excel
          </Button>
        )}
      </div>

      {!resolvedLotId ? (
        <div className="p-8 text-center text-slate-400">{t("Lot tanlang", "Выберите лот")}</div>
      ) : isLoading ? (
        <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>
      ) : !summary ? (
        <div className="p-8 text-center text-slate-400">{t("Ma'lumot topilmadi", "Данные не найдены")}</div>
      ) : (
        <>
          <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4">
            <p className="font-bold text-lg font-mono">{summary.lot_number}</p>
            <p className="text-sm text-slate-500">
              {t("Ochilgan", "Открыт")}: {new Date(summary.opened_at).toLocaleDateString("ru-RU")}
              {summary.closed_at && ` — ${new Date(summary.closed_at).toLocaleDateString("ru-RU")}`}
            </p>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs font-medium text-slate-500">
                  <th className="px-4 py-3">{t("Kontragent", "Контрагент")}</th>
                  <th className="px-4 py-3 text-right">{t("Xom ashyo (kg)", "Сырьё (кг)")}</th>
                  <th className="px-4 py-3 text-right">{t("Ulush (%)", "Доля (%)")}</th>
                  <th className="px-4 py-3 text-right">{t("FG brutto (kg)", "ГП брутто (кг)")}</th>
                  <th className="px-4 py-3 text-right">{t("Hizmat haqi (kg)", "Услуга (кг)")}</th>
                  <th className="px-4 py-3 text-right">{t("Hizmat haqi (UZS)", "Услуга (UZS)")}</th>
                  <th className="px-4 py-3 text-right">{t("Hizmat haqi (USD)", "Услуга (USD)")}</th>
                  <th className="px-4 py-3 text-right">{t("Netto qabul (kg)", "Нетто (кг)")}</th>
                </tr>
              </thead>
              <tbody>
                {summary.rows.map((row) => (
                  <tr key={row.counterparty_id} className="border-b border-slate-50 hover:bg-slate-50/50">
                    <td className="px-4 py-2.5 font-medium">{row.counterparty_name}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{fmt3(Number(row.raw_kg_delivered))}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{Number(row.ownership_share_pct).toFixed(3)}%</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{fmt3(Number(row.total_gross_kg))}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-red-600">{fmt3(Number(row.total_fee_kg))}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{row.fee_amount_uzs != null ? Number(row.fee_amount_uzs).toLocaleString("uz-UZ", { minimumFractionDigits: 2 }) : "—"}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums">{row.fee_amount_usd != null ? Number(row.fee_amount_usd).toLocaleString("uz-UZ", { minimumFractionDigits: 4 }) : "—"}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-green-700">{fmt3(Number(row.total_net_kg))}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-slate-200 bg-slate-50 font-semibold">
                  <td className="px-4 py-2.5">{t("JAMI", "ИТОГО")}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {fmt3(summary.rows.reduce((s, r) => s + Number(r.raw_kg_delivered), 0))}
                  </td>
                  <td className="px-4 py-2.5"></td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{fmt3(Number(summary.total_fg_kg))}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-red-600">{fmt3(Number(summary.total_fee_kg))}</td>
                  <td className="px-4 py-2.5"></td>
                  <td className="px-4 py-2.5"></td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-green-700">{fmt3(Number(summary.total_net_kg))}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

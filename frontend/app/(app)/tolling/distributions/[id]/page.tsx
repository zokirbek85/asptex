"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { tollingApi } from "@/lib/api/tolling";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

const fmt3 = (v: number) => Number(v).toLocaleString("uz-UZ", { minimumFractionDigits: 3 });

export default function DistributionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { language, activeRole } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();
  const isAdmin = activeRole === "ADMIN";

  const { data: dist, isLoading } = useQuery({
    queryKey: ["tolling-dist", id],
    queryFn: () => tollingApi.getDistribution(id),
    enabled: !!id,
  });

  const confirmMut = useMutation({
    mutationFn: () => tollingApi.confirmDistribution(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-dist", id] }); toast.success(t("Tasdiqlandi", "Подтверждено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const unconfirmMut = useMutation({
    mutationFn: () => tollingApi.unconfirmDistribution(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-dist", id] }); toast.success(t("Bekor qilindi", "Отменено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) return <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>;
  if (!dist) return <div className="p-8 text-center text-red-400">{t("Topilmadi", "Не найдено")}</div>;

  return (
    <div className="pb-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {t("Taqsimot", "Распределение")} — {dist.distribution_date}
          </h1>
          <p className="text-sm text-slate-400">
            {t("Jami FG", "Итого ГП")}: {fmt3(Number(dist.daily_fg_kg_total))} kg
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={dist.status === "CONFIRMED" ? "success" : "warning"}>{dist.status}</Badge>
          {dist.status === "DRAFT" && (
            <Button size="sm" loading={confirmMut.isPending} onClick={() => confirmMut.mutate()}>
              {t("Tasdiqlash", "Подтвердить")}
            </Button>
          )}
          {dist.status === "CONFIRMED" && isAdmin && (
            <Button size="sm" variant="danger" loading={unconfirmMut.isPending} onClick={() => unconfirmMut.mutate()}>
              {t("Bekor qilish", "Отменить")}
            </Button>
          )}
        </div>
      </div>

      {/* Summary cards */}
      <div className="mb-5 grid grid-cols-3 gap-3">
        {[
          { label: t("Netto (egalarga)", "Нетто (владельцам)"), value: fmt3(Number(dist.total_net_kg)) + " kg", color: "text-green-700" },
          { label: t("Hizmat haqi (korxona)", "Услуга (предприятие)"), value: fmt3(Number(dist.total_fee_kg)) + " kg", color: "text-blue-700" },
          { label: t("Tekshiruv", "Проверка"), value: fmt3(Number(dist.total_kg_check)) + " kg", color: "text-slate-700" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-200 bg-white p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">{s.label}</p>
            <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Distribution lines */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden mb-5">
        <div className="border-b border-slate-100 px-4 py-3">
          <p className="text-sm font-semibold text-slate-700">{t("Taqsimot qatorlari", "Строки распределения")}</p>
        </div>
        {dist.lines.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-400">
            {dist.status === "DRAFT" ? t("Tasdiqlash uchun tugmani bosing", "Нажмите кнопку подтверждения") : t("Qatorlar yo'q", "Строк нет")}
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs font-medium text-slate-500">
                <th className="px-4 py-2">{t("Tur", "Тип")}</th>
                <th className="px-4 py-2">{t("Kontragent", "Контрагент")}</th>
                <th className="px-4 py-2 text-right">{t("Ulush %", "Доля %")}</th>
                <th className="px-4 py-2 text-right">{t("Brutto (kg)", "Брутто (кг)")}</th>
                <th className="px-4 py-2 text-right">{t("Hizmat (kg)", "Услуга (кг)")}</th>
                <th className="px-4 py-2 text-right">{t("Netto (kg)", "Нетто (кг)")}</th>
              </tr>
            </thead>
            <tbody>
              {dist.lines.map((ln, i) => (
                <tr key={i} className={`border-b border-slate-50 ${ln.line_type === "PROCESSOR_FEE" ? "bg-blue-50/40 font-medium" : ""}`}>
                  <td className="px-4 py-2">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ln.line_type === "OWNER_NET" ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"}`}>
                      {ln.line_type === "OWNER_NET" ? t("Egasi", "Владелец") : t("Hizmat haqi", "Услуга")}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {ln.line_type === "PROCESSOR_FEE" ? t("Korxona", "Предприятие") : (ln.counterparty_name ?? "—")}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    {ln.line_type === "PROCESSOR_FEE" ? "—" : `${Number(ln.ownership_share_pct).toFixed(3)}%`}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{fmt3(Number(ln.gross_kg))}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-red-600">{fmt3(Number(ln.fee_kg))}</td>
                  <td className="px-4 py-2 text-right tabular-nums font-semibold text-green-700">{fmt3(Number(ln.net_kg))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Raw intakes */}
      {dist.raw_intakes.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="text-sm font-semibold text-slate-700">{t("Xom ashyo qabuli", "Поступление сырья")}</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs font-medium text-slate-500">
                <th className="px-4 py-2">{t("Kontragent", "Контрагент")}</th>
                <th className="px-4 py-2 text-right">{t("Bugun qabul (kg)", "Принято сегодня (кг)")}</th>
              </tr>
            </thead>
            <tbody>
              {dist.raw_intakes.map((ri) => (
                <tr key={ri.id} className="border-b border-slate-50">
                  <td className="px-4 py-2">{ri.counterparty_name ?? ri.participant_id}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{fmt3(Number(ri.raw_kg_received_today))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dist.confirmed_at && (
        <p className="mt-3 text-xs text-slate-400">
          {t("Tasdiqlangan", "Подтверждено")}: {new Date(dist.confirmed_at).toLocaleString("ru-RU")}
        </p>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { format } from "date-fns";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { tollingApi, type TollingDistribution } from "@/lib/api/tolling";
import { dailyReportApi } from "@/lib/api/daily-report";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

const fmt3 = (v: number) => Number(v).toLocaleString("uz-UZ", { minimumFractionDigits: 3 });

export default function NewDistributionPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const router = useRouter();

  const today = format(new Date(), "yyyy-MM-dd");
  const [distribDate, setDistribDate] = useState(today);
  const [fgKg, setFgKg] = useState("");
  const [autoFilled, setAutoFilled] = useState(false);
  const [rawIntakes, setRawIntakes] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<TollingDistribution | null>(null);
  const [draftId, setDraftId] = useState<string | null>(null);

  const { data: fgTotalData } = useQuery({
    queryKey: ["fg-total", distribDate],
    queryFn: () => dailyReportApi.getFgTotal(distribDate),
    enabled: !!distribDate,
  });

  useEffect(() => {
    if (fgTotalData && fgTotalData.total_kg > 0) {
      setFgKg(String(fgTotalData.total_kg));
      setAutoFilled(true);
    } else {
      setAutoFilled(false);
    }
  }, [fgTotalData]);

  const { data: lot, isLoading: lotLoading } = useQuery({
    queryKey: ["tolling-active-lot"],
    queryFn: () => tollingApi.getActiveLot(),
  });

  const createMut = useMutation({
    mutationFn: async () => {
      const intakes = lot!.participants.map((p) => ({
        participant_id: p.id,
        raw_kg_received_today: parseFloat(rawIntakes[p.id] || "0") || 0,
      }));
      const dist = await tollingApi.createDistribution({
        tolling_lot_id: lot!.id,
        distribution_date: distribDate,
        daily_fg_kg_total: parseFloat(fgKg) || 0,
        raw_intakes: intakes,
      });
      return dist;
    },
    onSuccess: async (dist) => {
      setDraftId(dist.id);
      const prev = await tollingApi.previewDistribution(dist.id);
      setPreview(prev);
      toast.success(t("Hisoblandi", "Рассчитано"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const previewMut = useMutation({
    mutationFn: async () => {
      if (!draftId) {
        await createMut.mutateAsync();
        return;
      }
      await tollingApi.updateDistribution(draftId, {
        daily_fg_kg_total: parseFloat(fgKg) || 0,
        raw_intakes: lot!.participants.map((p) => ({
          participant_id: p.id,
          raw_kg_received_today: parseFloat(rawIntakes[p.id] || "0") || 0,
        })),
      });
      const prev = await tollingApi.previewDistribution(draftId);
      setPreview(prev);
      toast.success(t("Hisoblandi", "Рассчитано"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const confirmMut = useMutation({
    mutationFn: async () => {
      const id = draftId ?? (await createMut.mutateAsync()).id;
      return tollingApi.confirmDistribution(id);
    },
    onSuccess: () => {
      toast.success(t("Taqsimot tasdiqlandi", "Распределение подтверждено"));
      router.push("/tolling/distributions");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (lotLoading) return <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>;
  if (!lot) return (
    <div className="p-8 text-center text-slate-400">
      {t("Aktiv lot yo'q", "Нет активного лота")}
    </div>
  );

  const totalRaw = lot.participants.reduce((s, p) => s + p.raw_kg_delivered, 0);

  return (
    <div className="pb-10">
      <h1 className="mb-6 text-xl font-bold text-gray-900">
        {t("Yangi taqsimot", "Новое распределение")} — {lot.lot_number}
      </h1>

      <div className="grid gap-5 md:grid-cols-2">
        {/* Left: Inputs */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <h2 className="text-sm font-semibold text-slate-700">{t("Asosiy ma'lumotlar", "Основные данные")}</h2>
            <Input label={t("Sana *", "Дата *")} type="date" value={distribDate} onChange={(e) => setDistribDate(e.target.value)} />
            <div>
              <Input
                label={t("Kunlik tayyor mahsulot (kg) *", "Готовая продукция за день (кг) *")}
                type="number" step="0.001" min="0"
                value={fgKg}
                onChange={(e) => { setFgKg(e.target.value); setAutoFilled(false); }}
                hint={autoFilled ? t("✓ Kunlik hisobotdan avtomatik tortildi", "✓ Заполнено автоматически из отчёта") : undefined}
              />
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
            <h2 className="text-sm font-semibold text-slate-700">
              {t("Kunlik xom ashyo qabul", "Поступление сырья за день")}
            </h2>
            {lot.participants.length === 0 ? (
              <p className="text-sm text-slate-400">{t("Ishtirokchilar yo'q", "Участников нет")}</p>
            ) : (
              lot.participants.map((p) => (
                <div key={p.id} className="flex items-center gap-3">
                  <span className="flex-1 text-sm text-slate-700">{p.counterparty_name}</span>
                  <span className="text-xs text-slate-400 w-24 text-right">
                    {t("Jami", "Итого")}: {fmt3(p.raw_kg_delivered)}
                  </span>
                  <div className="w-36">
                    <Input
                      label=""
                      type="number" step="0.001" min="0"
                      placeholder="kg bugun"
                      value={rawIntakes[p.id] ?? ""}
                      onChange={(e) => setRawIntakes((r) => ({ ...r, [p.id]: e.target.value }))}
                    />
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              loading={previewMut.isPending || createMut.isPending}
              disabled={!fgKg || parseFloat(fgKg) <= 0 || totalRaw <= 0}
              onClick={() => previewMut.mutate()}
            >
              {t("Hisoblash (Preview)", "Рассчитать")}
            </Button>
            <Button
              loading={confirmMut.isPending}
              disabled={!preview}
              onClick={() => confirmMut.mutate()}
            >
              {t("Tasdiqlash", "Подтвердить")}
            </Button>
          </div>

          {totalRaw === 0 && (
            <p className="text-xs text-amber-600 bg-amber-50 rounded-lg p-2">
              {t(
                "Ishtirokchilarda xom ashyo (raw_kg_delivered) nol. Hisoblash uchun avval lot ishtirokchilariga xom ashyo kiriting.",
                "У участников нет сырья (raw_kg_delivered = 0). Сначала добавьте сырьё участникам лота."
              )}
            </p>
          )}
        </div>

        {/* Right: Preview result */}
        <div>
          {preview ? (
            <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-semibold text-slate-700">{t("Hisob natijasi", "Результат расчёта")}</p>
                <p className="text-xs text-slate-400">
                  {t("Jami", "Итого")}: {fmt3(Number(preview.daily_fg_kg_total))} kg →{" "}
                  {t("tekshiruv", "проверка")}: {fmt3(Number(preview.total_kg_check))} kg
                </p>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs font-medium text-slate-500">
                    <th className="px-3 py-2">{t("Kontragent", "Контрагент")}</th>
                    <th className="px-3 py-2 text-right">{t("Ulush", "Доля")}</th>
                    <th className="px-3 py-2 text-right">{t("Brutto", "Брутто")}</th>
                    <th className="px-3 py-2 text-right">{t("Hizmat", "Услуга")}</th>
                    <th className="px-3 py-2 text-right">{t("Netto", "Нетто")}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.lines.map((ln, i) => (
                    <tr key={i} className={`border-b border-slate-50 ${ln.line_type === "PROCESSOR_FEE" ? "bg-blue-50/50 font-medium" : ""}`}>
                      <td className="px-3 py-2 text-xs">
                        {ln.line_type === "PROCESSOR_FEE" ? t("Korxona (hizmat haqi)", "Предприятие (услуга)") : ln.counterparty_name}
                      </td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums">
                        {ln.line_type === "PROCESSOR_FEE" ? "—" : `${Number(ln.ownership_share_pct).toFixed(3)}%`}
                      </td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums">{fmt3(Number(ln.gross_kg))}</td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums text-red-600">{fmt3(Number(ln.fee_kg))}</td>
                      <td className="px-3 py-2 text-right text-xs tabular-nums text-green-700 font-semibold">{fmt3(Number(ln.net_kg))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-400 text-sm">
              {t("«Hisoblash» tugmasini bosing", "Нажмите «Рассчитать»")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X, CheckCircle, Pencil, Download } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

import { tollingApi, type TollingParticipant } from "@/lib/api/tolling";
import { counterpartyApi } from "@/lib/api/counterparty";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";

const fmt3 = (v: number) => Number(v).toLocaleString("uz-UZ", { minimumFractionDigits: 3 });
const fmtPct = (v: number) => Number(v).toFixed(3) + "%";

export default function ActiveLotPage() {
  const { language, activeRole } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();
  const isAdmin = activeRole === "ADMIN" || activeRole === "DEPUTY_DIRECTOR";

  // Create lot modal
  const [showCreate, setShowCreate] = useState(false);
  const [lotNotes, setLotNotes] = useState("");

  // Close lot modal
  const [showClose, setShowClose] = useState(false);
  const [closeReason, setCloseReason] = useState("");

  // Add participant modal
  const [showAddPart, setShowAddPart] = useState(false);
  const [partForm, setPartForm] = useState({ counterparty_id: "", fee_pct: "", fee_currency: "UZS", fee_rate_per_kg: "", raw_kg_delivered: "" });

  // Edit participant modal
  const [editPart, setEditPart] = useState<TollingParticipant | null>(null);
  const [editForm, setEditForm] = useState({ fee_pct: "", fee_rate_per_kg: "", raw_kg_delivered: "" });

  const { data: lot, isLoading } = useQuery({
    queryKey: ["tolling-active-lot"],
    queryFn: () => tollingApi.getActiveLot(),
  });

  const { data: cpData } = useQuery({
    queryKey: ["counterparties-active"],
    queryFn: () => counterpartyApi.list({ active_only: true, page_size: 200 }),
    enabled: showAddPart,
  });
  const cpOptions = (cpData?.items ?? []).map((c) => ({ value: c.id, label: c.name }));

  const createMut = useMutation({
    mutationFn: () => tollingApi.createLot({ notes: lotNotes || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-active-lot"] }); setShowCreate(false); setLotNotes(""); toast.success(t("Lot yaratildi", "Лот создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const closeMut = useMutation({
    mutationFn: () => tollingApi.closeLot(lot!.id, { close_reason: closeReason || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-active-lot"] }); setShowClose(false); setCloseReason(""); toast.success(t("Lot yopildi", "Лот закрыт")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const addPartMut = useMutation({
    mutationFn: () => tollingApi.addParticipant(lot!.id, {
      counterparty_id: partForm.counterparty_id,
      fee_pct: parseFloat(partForm.fee_pct) || 0,
      fee_currency: partForm.fee_currency,
      fee_rate_per_kg: partForm.fee_rate_per_kg ? parseFloat(partForm.fee_rate_per_kg) : null,
      raw_kg_delivered: partForm.raw_kg_delivered ? parseFloat(partForm.raw_kg_delivered) : 0,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-active-lot"] }); setShowAddPart(false); setPartForm({ counterparty_id: "", fee_pct: "", fee_currency: "UZS", fee_rate_per_kg: "", raw_kg_delivered: "" }); toast.success(t("Ishtirokchi qo'shildi", "Участник добавлен")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const editPartMut = useMutation({
    mutationFn: () => tollingApi.updateParticipant(lot!.id, editPart!.id, {
      fee_pct: editForm.fee_pct ? parseFloat(editForm.fee_pct) : undefined,
      fee_rate_per_kg: editForm.fee_rate_per_kg ? parseFloat(editForm.fee_rate_per_kg) : null,
      raw_kg_delivered: editForm.raw_kg_delivered ? parseFloat(editForm.raw_kg_delivered) : undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-active-lot"] }); setEditPart(null); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const removePartMut = useMutation({
    mutationFn: (pid: string) => tollingApi.removeParticipant(lot!.id, pid),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tolling-active-lot"] }); toast.success(t("O'chirildi", "Удалён")); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) {
    return <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>;
  }

  return (
    <div className="pb-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Aktiv Tolling Lot", "Активный Толлинг-лот")}</h1>
        {isAdmin && !lot && (
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus size={14} /> {t("Yangi lot", "Новый лот")}
          </Button>
        )}
      </div>

      {!lot ? (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-12 text-center">
          <p className="text-slate-400 mb-4">{t("Hozirda aktiv tolling lot yo'q", "Нет активного толлинг-лота")}</p>
          {isAdmin && (
            <Button onClick={() => setShowCreate(true)}>
              <Plus size={14} /> {t("Lot ochish", "Открыть лот")}
            </Button>
          )}
        </div>
      ) : (
        <>
          {/* Lot header */}
          <div className="mb-5 rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Link
                    href={`/master/lots/${lot.lot_id}`}
                    className="text-2xl font-bold font-mono text-slate-800 hover:text-blue-600 hover:underline"
                    title={t("Master lotga o'tish", "Перейти к мастер-лоту")}
                  >
                    {lot.lot_number}
                  </Link>
                  <Badge variant={lot.status === "OPEN" ? "success" : "default"}>{lot.status}</Badge>
                </div>
                <p className="text-sm text-slate-500">
                  {t("Ochilgan", "Открыт")}: {new Date(lot.opened_at).toLocaleDateString("ru-RU")}
                </p>
                {lot.notes && <p className="text-sm text-slate-400 mt-1">{lot.notes}</p>}
              </div>
              <div className="flex gap-2">
                <Link href="/tolling/distributions/new">
                  <Button size="sm" variant="outline">
                    <Plus size={14} /> {t("Yangi taqsimot", "Новое распределение")}
                  </Button>
                </Link>
                {isAdmin && lot.status === "OPEN" && (
                  <Button size="sm" variant="danger" onClick={() => setShowClose(true)}>
                    {t("Lotni yopish", "Закрыть лот")}
                  </Button>
                )}
              </div>
            </div>

            {/* Quick stats */}
            <div className="mt-4 grid grid-cols-3 gap-3">
              {[
                { label: t("Jami xom ashyo", "Всего сырья"), value: fmt3(lot.total_raw_kg) + " kg" },
                { label: t("Tasdiqlangan taqsimotlar", "Подтверждённых распределений"), value: lot.total_distributions },
                { label: t("Jami FG taqsimlandi", "Распределено FG"), value: fmt3(lot.total_fg_distributed_kg) + " kg" },
              ].map((stat) => (
                <div key={stat.label} className="rounded-lg bg-slate-50 p-3 text-center">
                  <p className="text-xs text-slate-500 mb-1">{stat.label}</p>
                  <p className="text-lg font-bold text-slate-800">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Participants */}
          <div className="rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <p className="text-sm font-semibold text-slate-700">
                {t("Ishtirokchilar", "Участники")} ({lot.participants.length})
              </p>
              {isAdmin && lot.status === "OPEN" && (
                <Button size="sm" variant="outline" onClick={() => setShowAddPart(true)}>
                  <Plus size={12} /> {t("Qo'shish", "Добавить")}
                </Button>
              )}
            </div>

            {lot.participants.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-400">
                {t("Ishtirokchilar yo'q", "Участников нет")}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-left text-xs font-medium text-slate-500">
                      <th className="px-4 py-2">{t("Kontragent", "Контрагент")}</th>
                      <th className="px-4 py-2 text-right">{t("Xom ashyo (kg)", "Сырьё (кг)")}</th>
                      <th className="px-4 py-2 text-right">{t("Ulush (%)", "Доля (%)")}</th>
                      <th className="px-4 py-2 text-right">{t("Hizmat haqi %", "Услуга %")}</th>
                      <th className="px-4 py-2">{t("Valyuta", "Валюта")}</th>
                      <th className="px-4 py-2 text-right">{t("Narx (kg)", "Цена/кг")}</th>
                      <th className="px-4 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {lot.participants.map((p) => {
                      const totalRaw = lot.participants.reduce((s, x) => s + x.raw_kg_delivered, 0);
                      const share = totalRaw > 0 ? (p.raw_kg_delivered / totalRaw * 100) : 0;
                      return (
                        <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50/50">
                          <td className="px-4 py-2 font-medium">{p.counterparty_name ?? p.counterparty_id}</td>
                          <td className="px-4 py-2 text-right tabular-nums">{fmt3(p.raw_kg_delivered)}</td>
                          <td className="px-4 py-2 text-right tabular-nums">{share.toFixed(3)}%</td>
                          <td className="px-4 py-2 text-right tabular-nums">{Number(p.fee_pct).toFixed(2)}%</td>
                          <td className="px-4 py-2">{p.fee_currency}</td>
                          <td className="px-4 py-2 text-right tabular-nums">
                            {p.fee_rate_per_kg != null ? Number(p.fee_rate_per_kg).toLocaleString() : "—"}
                          </td>
                          <td className="px-4 py-2 text-right">
                            {isAdmin && lot.status === "OPEN" && (
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  onClick={() => { setEditPart(p); setEditForm({ fee_pct: String(p.fee_pct), fee_rate_per_kg: String(p.fee_rate_per_kg ?? ""), raw_kg_delivered: String(p.raw_kg_delivered) }); }}
                                  className="rounded p-1 text-slate-400 hover:bg-blue-50 hover:text-blue-600"
                                >
                                  <Pencil size={13} />
                                </button>
                                <button
                                  onClick={() => { if (confirm(t("O'chirilsinmi?", "Удалить?"))) removePartMut.mutate(p.id); }}
                                  className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-500"
                                >
                                  <X size={13} />
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Reports shortcut */}
          <div className="mt-4 flex gap-2">
            <Link href={`/tolling/reports/lot-summary?lot_id=${lot.id}`}>
              <Button variant="outline" size="sm">
                <Download size={14} /> {t("Lot xulosasi", "Сводка лота")}
              </Button>
            </Link>
            <Link href={`/tolling/reports/daily-register?lot_id=${lot.id}`}>
              <Button variant="outline" size="sm">
                {t("Kunlik reestr", "Дневной реестр")}
              </Button>
            </Link>
          </div>
        </>
      )}

      {/* Create lot modal */}
      <Modal open={showCreate} onOpenChange={(v) => { if (!v) setShowCreate(false); }} title={t("Yangi tolling lot", "Новый толлинг-лот")}>
        <div className="flex flex-col gap-4">
          <Input label={t("Izoh (ixtiyoriy)", "Примечание (необязательно)")} value={lotNotes} onChange={(e) => setLotNotes(e.target.value)} />
          <ModalFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>{t("Bekor", "Отмена")}</Button>
            <Button loading={createMut.isPending} onClick={() => createMut.mutate()}>{t("Yaratish", "Создать")}</Button>
          </ModalFooter>
        </div>
      </Modal>

      {/* Close lot modal */}
      <Modal open={showClose} onOpenChange={(v) => { if (!v) setShowClose(false); }} title={t("Lotni yopish", "Закрыть лот")}>
        <div className="flex flex-col gap-4">
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg p-3">
            {t("Diqqat: lot yopilgandan keyin yangi taqsimot qo'shib bo'lmaydi.", "Внимание: после закрытия лота нельзя добавлять новые распределения.")}
          </p>
          <Input label={t("Sabab (ixtiyoriy)", "Причина (необязательно)")} value={closeReason} onChange={(e) => setCloseReason(e.target.value)} />
          <ModalFooter>
            <Button variant="outline" onClick={() => setShowClose(false)}>{t("Bekor", "Отмена")}</Button>
            <Button variant="danger" loading={closeMut.isPending} onClick={() => closeMut.mutate()}>{t("Yopish", "Закрыть")}</Button>
          </ModalFooter>
        </div>
      </Modal>

      {/* Add participant modal */}
      <Modal open={showAddPart} onOpenChange={(v) => { if (!v) setShowAddPart(false); }} title={t("Ishtirokchi qo'shish", "Добавить участника")}>
        <div className="flex flex-col gap-3">
          <Select
            label={t("Kontragent *", "Контрагент *")}
            value={partForm.counterparty_id}
            onValueChange={(v) => setPartForm((f) => ({ ...f, counterparty_id: v }))}
            options={cpOptions}
            placeholder={t("Tanlang...", "Выберите...")}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input label={t("Hizmat haqi % *", "Услуга % *")} type="number" step="0.01" min="0" max="100" value={partForm.fee_pct} onChange={(e) => setPartForm((f) => ({ ...f, fee_pct: e.target.value }))} />
            <Input label={t("Boshlang'ich xom ashyo (kg)", "Нач. сырьё (кг)")} type="number" step="0.001" min="0" value={partForm.raw_kg_delivered} onChange={(e) => setPartForm((f) => ({ ...f, raw_kg_delivered: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select label={t("Valyuta", "Валюта")} value={partForm.fee_currency} onValueChange={(v) => setPartForm((f) => ({ ...f, fee_currency: v }))} options={[{ value: "UZS", label: "UZS" }, { value: "USD", label: "USD" }]} />
            <Input label={t("Narx (1 kg uchun)", "Цена за 1 кг")} type="number" step="0.0001" min="0" value={partForm.fee_rate_per_kg} onChange={(e) => setPartForm((f) => ({ ...f, fee_rate_per_kg: e.target.value }))} />
          </div>
          <ModalFooter>
            <Button variant="outline" onClick={() => setShowAddPart(false)}>{t("Bekor", "Отмена")}</Button>
            <Button loading={addPartMut.isPending} disabled={!partForm.counterparty_id || !partForm.fee_pct} onClick={() => addPartMut.mutate()}>
              {t("Qo'shish", "Добавить")}
            </Button>
          </ModalFooter>
        </div>
      </Modal>

      {/* Edit participant modal */}
      <Modal open={!!editPart} onOpenChange={(v) => { if (!v) setEditPart(null); }} title={t("Ishtirokchini tahrirlash", "Редактировать участника")}>
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-slate-700">{editPart?.counterparty_name}</p>
          <div className="grid grid-cols-2 gap-3">
            <Input label={t("Hizmat haqi %", "Услуга %")} type="number" step="0.01" min="0" max="100" value={editForm.fee_pct} onChange={(e) => setEditForm((f) => ({ ...f, fee_pct: e.target.value }))} />
            <Input label={t("Xom ashyo (kg)", "Сырьё (кг)")} type="number" step="0.001" min="0" value={editForm.raw_kg_delivered} onChange={(e) => setEditForm((f) => ({ ...f, raw_kg_delivered: e.target.value }))} />
          </div>
          <Input label={t("Narx (1 kg uchun)", "Цена за 1 кг")} type="number" step="0.0001" min="0" value={editForm.fee_rate_per_kg} onChange={(e) => setEditForm((f) => ({ ...f, fee_rate_per_kg: e.target.value }))} />
          <ModalFooter>
            <Button variant="outline" onClick={() => setEditPart(null)}>{t("Bekor", "Отмена")}</Button>
            <Button loading={editPartMut.isPending} onClick={() => editPartMut.mutate()}>{t("Saqlash", "Сохранить")}</Button>
          </ModalFooter>
        </div>
      </Modal>
    </div>
  );
}

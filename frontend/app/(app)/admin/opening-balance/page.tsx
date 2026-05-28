"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Plus, Send, Trash2, CheckCircle } from "lucide-react";
import { toast } from "sonner";

import {
  openingBalanceApi,
  type OpeningBalanceLineCreate,
  type OpeningBalanceResponse,
} from "@/lib/api/opening-balance";
import { warehouseApi } from "@/lib/api/warehouse";
import { lotApi } from "@/lib/api/lot";
import { countApi } from "@/lib/api/count";
import { counterpartyApi } from "@/lib/api/counterparty";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Warehouse, WarehouseType } from "@/lib/types";

// ─── Constants ────────────────────────────────────────────────────────────────

const WASTE_TYPES = [
  { value: "ST_3", label: "ST-3" },
  { value: "ST_7_11", label: "ST-7-11" },
  { value: "ST_1", label: "ST-1" },
  { value: "ST_36", label: "ST-36" },
  { value: "ST_98", label: "ST-98" },
  { value: "MYCHKA", label: "Mychka" },
  { value: "ROVNITSA", label: "Rovnitsa" },
];

const PKG_TYPES = [
  { value: "BAG", label: "Qop (Bag)" },
  { value: "CONE", label: "Konus (Cone)" },
  { value: "PACKAGE", label: "Paket" },
  { value: "CORRUGATED_SHEET", label: "Gofrokarton" },
  { value: "PARAFFIN", label: "Parafin" },
  { value: "BOX", label: "Quti (Box)" },
];

type LineState = OpeningBalanceLineCreate & { _key: string };

function makeKey() {
  return Math.random().toString(36).slice(2);
}

function emptyLine(): LineState {
  return {
    _key: makeKey(),
    lot_id: null,
    count_id: null,
    owner_id: null,
    waste_type: null,
    pkg_item_type: null,
    quantity_kg: 0,
    quantity_bags: null,
    quantity_kip: null,
    quantity_units: null,
    notes: null,
  };
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function OpeningBalancePage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [selectedWarehouseId, setSelectedWarehouseId] = useState("");
  const [balanceDate, setBalanceDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [entry, setEntry] = useState<OpeningBalanceResponse | null>(null);
  const [lines, setLines] = useState<LineState[]>([emptyLine()]);
  const [isDirty, setIsDirty] = useState(false);

  // ── Data fetching ────────────────────────────────────────────────────────────

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-all"],
    queryFn: () => warehouseApi.list({ active_only: true, page_size: 200 }),
  });
  const warehouses = warehousesPage?.items ?? [];
  const selectedWarehouse = warehouses.find((w) => w.id === selectedWarehouseId);
  const wType: WarehouseType | null = selectedWarehouse?.warehouse_type ?? null;

  const { data: lotsPage } = useQuery({
    queryKey: ["lots-all"],
    queryFn: () => lotApi.list({ page_size: 200 }),
    enabled: wType === "FINISHED_GOODS" || wType === "RAW_COTTON",
  });
  const lots = lotsPage?.items ?? [];

  const { data: countsPage } = useQuery({
    queryKey: ["counts-all"],
    queryFn: () => countApi.list({ active_only: true, page_size: 200 }),
    enabled: wType === "FINISHED_GOODS" || wType === "RAW_COTTON",
  });
  const counts = countsPage?.items ?? [];

  const { data: ownersPage } = useQuery({
    queryKey: ["counterparties-tolling"],
    queryFn: () =>
      counterpartyApi.list({ active_only: true, counterparty_type: "TOLLING_OWNER", page_size: 200 }),
    enabled: wType === "FINISHED_GOODS" || wType === "RAW_COTTON",
  });
  const owners = ownersPage?.items ?? [];

  // ── Load existing entry ──────────────────────────────────────────────────────

  const { data: existingList, refetch: refetchList } = useQuery({
    queryKey: ["opening-balances", selectedWarehouseId, balanceDate],
    queryFn: () =>
      openingBalanceApi.list({ warehouse_id: selectedWarehouseId, page_size: 5 }),
    enabled: !!selectedWarehouseId,
  });

  useEffect(() => {
    if (!existingList) return;
    const found = existingList.items.find((e) => e.balance_date === balanceDate);
    if (found) {
      loadEntry(found);
    } else {
      setEntry(null);
      setLines([emptyLine()]);
      setIsDirty(false);
    }
  }, [existingList, balanceDate]);

  function loadEntry(e: OpeningBalanceResponse) {
    setEntry(e);
    if (e.lines.length > 0) {
      setLines(
        e.lines.map((l) => ({
          _key: l.id,
          lot_id: l.lot_id,
          count_id: l.count_id,
          owner_id: l.owner_id,
          waste_type: l.waste_type as any,
          pkg_item_type: l.pkg_item_type as any,
          quantity_kg: l.quantity_kg,
          quantity_bags: l.quantity_bags,
          quantity_kip: l.quantity_kip,
          quantity_units: l.quantity_units,
          notes: l.notes,
        }))
      );
    } else {
      setLines([emptyLine()]);
    }
    setIsDirty(false);
  }

  // ── Mutations ────────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: () =>
      openingBalanceApi.create({
        warehouse_id: selectedWarehouseId,
        balance_date: balanceDate,
      }),
    onSuccess: (created) => {
      loadEntry(created);
      qc.invalidateQueries({ queryKey: ["opening-balances"] });
    },
    onError: (e: any) => toast.error(e.message),
  });

  const saveLinesMutation = useMutation({
    mutationFn: async () => {
      let id = entry?.id;
      if (!id) {
        const created = await openingBalanceApi.create({
          warehouse_id: selectedWarehouseId,
          balance_date: balanceDate,
        });
        id = created.id;
        setEntry(created);
      }
      const payload = lines
        .filter((l) => Number(l.quantity_kg) > 0)
        .map(({ _key, ...rest }) => rest);
      return openingBalanceApi.updateLines(id!, payload);
    },
    onSuccess: (updated) => {
      loadEntry(updated);
      qc.invalidateQueries({ queryKey: ["opening-balances"] });
      toast.success(t("Saqlandi", "Сохранено"));
    },
    onError: (e: any) => toast.error(e.message),
  });

  const postMutation = useMutation({
    mutationFn: async () => {
      // Auto-save lines first
      let id = entry?.id;
      if (!id) {
        const created = await openingBalanceApi.create({
          warehouse_id: selectedWarehouseId,
          balance_date: balanceDate,
        });
        id = created.id;
      }
      const payload = lines
        .filter((l) => Number(l.quantity_kg) > 0)
        .map(({ _key, ...rest }) => rest);
      await openingBalanceApi.updateLines(id!, payload);
      return openingBalanceApi.post(id!);
    },
    onSuccess: (updated) => {
      loadEntry(updated);
      qc.invalidateQueries({ queryKey: ["opening-balances"] });
      toast.success(t("Muvaffaqiyatli joylashtirildi", "Успешно проведено"));
    },
    onError: (e: any) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => openingBalanceApi.delete(entry!.id),
    onSuccess: () => {
      setEntry(null);
      setLines([emptyLine()]);
      setIsDirty(false);
      qc.invalidateQueries({ queryKey: ["opening-balances"] });
      toast.success(t("O'chirildi", "Удалено"));
    },
    onError: (e: any) => toast.error(e.message),
  });

  // ── Line helpers ─────────────────────────────────────────────────────────────

  function updateLine(key: string, patch: Partial<LineState>) {
    setLines((prev) => prev.map((l) => (l._key === key ? { ...l, ...patch } : l)));
    setIsDirty(true);
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine()]);
    setIsDirty(true);
  }

  function removeLine(key: string) {
    setLines((prev) => prev.filter((l) => l._key !== key));
    setIsDirty(true);
  }

  const isPosted = entry?.status === "POSTED";
  const noWarehouse = !selectedWarehouseId;

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {t("Boshlang'ich qoldiq kiritish", "Ввод начального остатка")}
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">
            {t(
              "Ombor uchun tanlangan sana bo'yicha boshlang'ich qoldiqni kiriting",
              "Введите начальный остаток склада на выбранную дату"
            )}
          </p>
        </div>
        {entry && (
          <Badge variant={isPosted ? "success" : "warning"}>
            {isPosted ? t("Joylashtirilgan", "Проведено") : t("Qoralama", "Черновик")}
          </Badge>
        )}
      </div>

      {/* Warehouse + Date selector */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Select
            label={t("Ombor", "Склад")}
            value={selectedWarehouseId}
            onValueChange={(v) => {
              setSelectedWarehouseId(v);
              setEntry(null);
              setLines([emptyLine()]);
              setIsDirty(false);
            }}
            options={warehouses.map((w) => ({
              value: w.id,
              label: `${w.name} (${w.code})`,
            }))}
            placeholder={t("Ombor tanlang", "Выберите склад")}
          />
          <Input
            label={t("Sana", "Дата")}
            type="date"
            value={balanceDate}
            onChange={(e) => {
              setBalanceDate(e.target.value);
              setEntry(null);
              setLines([emptyLine()]);
              setIsDirty(false);
            }}
            disabled={noWarehouse}
          />
        </div>
      </div>

      {/* Lines table */}
      {selectedWarehouseId && (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">
              {t("Qoldiq satrlari", "Строки остатка")}
            </h2>
            {!isPosted && (
              <Button variant="ghost" size="sm" onClick={addLine}>
                <Plus size={14} /> {t("Satr qo'shish", "Добавить строку")}
              </Button>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-2.5">#</th>
                  {(wType === "FINISHED_GOODS" || wType === "RAW_COTTON") && (
                    <>
                      <th className="px-4 py-2.5">Lot</th>
                      <th className="px-4 py-2.5">Count</th>
                      <th className="px-4 py-2.5">{t("Egasi", "Владелец")}</th>
                    </>
                  )}
                  {wType === "WASTE" && <th className="px-4 py-2.5">{t("Chiqindi turi", "Тип отхода")}</th>}
                  {wType === "PACKAGING" && <th className="px-4 py-2.5">{t("Qadoq turi", "Тип упаковки")}</th>}
                  <th className="px-4 py-2.5">Qty (kg)</th>
                  {wType === "FINISHED_GOODS" && <th className="px-4 py-2.5">{t("Qoplar", "Мешки")}</th>}
                  {wType === "RAW_COTTON" && <th className="px-4 py-2.5">Qty (kip)</th>}
                  {wType === "PACKAGING" && <th className="px-4 py-2.5">{t("Dona", "Штук")}</th>}
                  <th className="px-4 py-2.5">{t("Izoh", "Примечание")}</th>
                  {!isPosted && <th className="px-4 py-2.5" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {lines.map((line, idx) => (
                  <tr key={line._key} className="hover:bg-slate-50/50">
                    <td className="px-4 py-2 text-slate-400 font-mono">{idx + 1}</td>

                    {(wType === "FINISHED_GOODS" || wType === "RAW_COTTON") && (
                      <>
                        <td className="px-2 py-1.5 min-w-[140px]">
                          <select
                            disabled={isPosted}
                            className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                            value={line.lot_id ?? ""}
                            onChange={(e) => updateLine(line._key, { lot_id: e.target.value || null })}
                          >
                            <option value="">—</option>
                            {lots.map((l) => (
                              <option key={l.id} value={l.id}>{l.lot_number}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-1.5 min-w-[120px]">
                          <select
                            disabled={isPosted}
                            className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                            value={line.count_id ?? ""}
                            onChange={(e) => updateLine(line._key, { count_id: e.target.value || null })}
                          >
                            <option value="">—</option>
                            {counts.map((c) => (
                              <option key={c.id} value={c.id}>{c.count_value}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-1.5 min-w-[140px]">
                          <select
                            disabled={isPosted}
                            className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                            value={line.owner_id ?? ""}
                            onChange={(e) => updateLine(line._key, { owner_id: e.target.value || null })}
                          >
                            <option value="">{t("O'z", "Своё")}</option>
                            {owners.map((o) => (
                              <option key={o.id} value={o.id}>{o.name}</option>
                            ))}
                          </select>
                        </td>
                      </>
                    )}

                    {wType === "WASTE" && (
                      <td className="px-2 py-1.5 min-w-[140px]">
                        <select
                          disabled={isPosted}
                          className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                          value={line.waste_type ?? ""}
                          onChange={(e) => updateLine(line._key, { waste_type: (e.target.value as any) || null })}
                        >
                          <option value="">— {t("Tanlang", "Выберите")}</option>
                          {WASTE_TYPES.map((wt) => (
                            <option key={wt.value} value={wt.value}>{wt.label}</option>
                          ))}
                        </select>
                      </td>
                    )}

                    {wType === "PACKAGING" && (
                      <td className="px-2 py-1.5 min-w-[160px]">
                        <select
                          disabled={isPosted}
                          className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                          value={line.pkg_item_type ?? ""}
                          onChange={(e) => updateLine(line._key, { pkg_item_type: (e.target.value as any) || null })}
                        >
                          <option value="">— {t("Tanlang", "Выберите")}</option>
                          {PKG_TYPES.map((pt) => (
                            <option key={pt.value} value={pt.value}>{pt.label}</option>
                          ))}
                        </select>
                      </td>
                    )}

                    {/* qty_kg */}
                    <td className="px-2 py-1.5 min-w-[110px]">
                      <input
                        type="number"
                        min={0}
                        step="0.001"
                        disabled={isPosted}
                        className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                        value={line.quantity_kg}
                        onChange={(e) => updateLine(line._key, { quantity_kg: parseFloat(e.target.value) || 0 })}
                      />
                    </td>

                    {wType === "FINISHED_GOODS" && (
                      <td className="px-2 py-1.5 min-w-[80px]">
                        <input
                          type="number"
                          min={0}
                          disabled={isPosted}
                          className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                          value={line.quantity_bags ?? ""}
                          onChange={(e) => updateLine(line._key, { quantity_bags: parseInt(e.target.value) || null })}
                        />
                      </td>
                    )}

                    {wType === "RAW_COTTON" && (
                      <td className="px-2 py-1.5 min-w-[100px]">
                        <input
                          type="number"
                          min={0}
                          step="0.001"
                          disabled={isPosted}
                          className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                          value={line.quantity_kip ?? ""}
                          onChange={(e) => updateLine(line._key, { quantity_kip: parseFloat(e.target.value) || null })}
                        />
                      </td>
                    )}

                    {wType === "PACKAGING" && (
                      <td className="px-2 py-1.5 min-w-[80px]">
                        <input
                          type="number"
                          min={0}
                          disabled={isPosted}
                          className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                          value={line.quantity_units ?? ""}
                          onChange={(e) => updateLine(line._key, { quantity_units: parseInt(e.target.value) || null })}
                        />
                      </td>
                    )}

                    {/* notes */}
                    <td className="px-2 py-1.5 min-w-[140px]">
                      <input
                        type="text"
                        disabled={isPosted}
                        className="asptex-input h-8 w-full rounded-lg border border-border bg-surface px-2 text-[13px] disabled:opacity-50"
                        value={line.notes ?? ""}
                        onChange={(e) => updateLine(line._key, { notes: e.target.value || null })}
                        placeholder={t("Izoh...", "Примечание...")}
                      />
                    </td>

                    {!isPosted && (
                      <td className="px-2 py-1.5">
                        <button
                          onClick={() => removeLine(line._key)}
                          disabled={lines.length === 1}
                          className="rounded p-1 text-slate-300 hover:bg-red-50 hover:text-red-500 disabled:opacity-30 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary */}
          <div className="border-t border-slate-100 px-5 py-3 flex items-center justify-between">
            <span className="text-[13px] text-slate-500">
              {t("Jami:", "Итого:")} {" "}
              <span className="font-semibold text-slate-700">
                {lines
                  .reduce((s, l) => s + (Number(l.quantity_kg) || 0), 0)
                  .toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg
              </span>
            </span>

            {!isPosted && (
              <div className="flex gap-2">
                {entry && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteMutation.mutate()}
                    disabled={deleteMutation.isPending}
                    className="text-red-500 hover:bg-red-50"
                  >
                    <Trash2 size={14} /> {t("O'chirish", "Удалить")}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => saveLinesMutation.mutate()}
                  disabled={saveLinesMutation.isPending}
                >
                  {t("Saqlash", "Сохранить")}
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => postMutation.mutate()}
                  disabled={postMutation.isPending || !lines.some((l) => Number(l.quantity_kg) > 0)}
                >
                  <Send size={14} /> {t("Joylashtirish", "Провести")}
                </Button>
              </div>
            )}

            {isPosted && (
              <div className="flex items-center gap-1.5 text-[13px] text-emerald-600">
                <CheckCircle size={15} />
                {t(
                  `${format(new Date(entry!.posted_at!), "dd.MM.yyyy HH:mm")} da joylashtirilgan`,
                  `Проведено ${format(new Date(entry!.posted_at!), "dd.MM.yyyy HH:mm")}`
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {!selectedWarehouseId && (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-slate-400">
          {t("Boshlash uchun ombor va sanani tanlang", "Выберите склад и дату для начала")}
        </div>
      )}
    </div>
  );
}

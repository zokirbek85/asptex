"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  Plus, Send, CheckCircle, RotateCcw, Trash2, Download,
  ChevronDown, ChevronUp, Package, Wheat, Recycle, Box,
} from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { dailyReportApi, type DailyReportLineCreate, type OpeningBalanceLine } from "@/lib/api/daily-report";
import { warehouseApi } from "@/lib/api/warehouse";
import { lotApi } from "@/lib/api/lot";
import { countApi } from "@/lib/api/count";
import { counterpartyApi } from "@/lib/api/counterparty";
import { exportApi } from "@/lib/api/export";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import type { Lot, ReportStatus, WarehouseType, Warehouse } from "@/lib/types";

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

const STATUS_VARIANT: Record<ReportStatus, "warning" | "info" | "success"> = {
  DRAFT: "warning",
  SUBMITTED: "info",
  CLOSED: "success",
};

const STATUS_LABEL: Record<ReportStatus, string> = {
  DRAFT: "Qoralama",
  SUBMITTED: "Yuborilgan",
  CLOSED: "Yopilgan",
};

const WH_ICON: Record<WarehouseType, React.ReactNode> = {
  FINISHED_GOODS: <Box size={16} />,
  RAW_COTTON: <Wheat size={16} />,
  WASTE: <Recycle size={16} />,
  PACKAGING: <Package size={16} />,
};

// ─── Line section config per warehouse type ────────────────────────────────

interface SectionConfig {
  category: string;
  label: string;
  color: string;
  direction: "in" | "out";
}

const SECTIONS: Record<WarehouseType, SectionConfig[]> = {
  FINISHED_GOODS: [
    { category: "PRODUCTION_INBOUND", label: "Ishlab chiqarish kirimi (+)", color: "green", direction: "in" },
    { category: "SALE_OUTBOUND",      label: "Sotish / jo'natma (−)",       color: "red",   direction: "out" },
  ],
  RAW_COTTON: [
    { category: "RECEIPT",           label: "Paxta qabul qilish (+)",      color: "green", direction: "in" },
    { category: "PRODUCTION_ISSUE",  label: "Ishlab chiqarishga berish (−)", color: "red",  direction: "out" },
  ],
  WASTE: [
    { category: "PRODUCTION_INBOUND", label: "Chiqindi kirim (+)",          color: "green", direction: "in" },
    { category: "SALE_OUTBOUND",      label: "Chiqindi sotish (−)",         color: "red",   direction: "out" },
  ],
  PACKAGING: [
    { category: "RECEIPT",           label: "Qadoqlash qabul (+)",          color: "green", direction: "in" },
    { category: "PACKAGING_ISSUE",   label: "Qadoqlash berish (−)",         color: "red",   direction: "out" },
  ],
};

// ─── Empty line factories ──────────────────────────────────────────────────

function emptyLine(category: string): DailyReportLineCreate {
  return {
    line_category: category as DailyReportLineCreate["line_category"],
    lot_id: null, count_id: null, owner_id: null,
    waste_type: null, buyer_id: null, pkg_item_type: null,
    quantity_kg: 0, quantity_bags: null, quantity_kip: null,
    quantity_units: null, notes: null,
  };
}

// ─── Line row components per warehouse type ────────────────────────────────

interface LineRowProps {
  line: DailyReportLineCreate;
  index: number;
  onChange: (idx: number, patch: Partial<DailyReportLineCreate>) => void;
  onRemove: (idx: number) => void;
  lots: { value: string; label: string }[];
  counts: { value: string; label: string }[];
  counterparties: { value: string; label: string }[];
  warehouseType: WarehouseType;
  showBuyer?: boolean;
}

function LineRow({
  line, index, onChange, onRemove,
  lots, counts, counterparties, warehouseType, showBuyer,
}: LineRowProps) {
  const patch = (p: Partial<DailyReportLineCreate>) => onChange(index, p);

  const commonQty = (
    <div className="w-32 shrink-0">
      <Input
        label="kg"
        type="number" step="0.001" min="0"
        value={line.quantity_kg || ""}
        onChange={(e) => patch({ quantity_kg: parseFloat(e.target.value) || 0 })}
      />
    </div>
  );

  const removeBtn = (
    <button
      type="button"
      onClick={() => onRemove(index)}
      className="mt-5 shrink-0 rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-500 transition-colors"
    >
      <Trash2 size={14} />
    </button>
  );

  if (warehouseType === "FINISHED_GOODS") {
    return (
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <div className="w-44 shrink-0">
          <Select
            label="Lot"
            value={line.lot_id ?? ""}
            onValueChange={(v) => patch({ lot_id: v || null })}
            options={lots}
            placeholder="Lot tanlang..."
          />
        </div>
        <div className="w-36 shrink-0">
          <Select
            label="Count"
            value={line.count_id ?? ""}
            onValueChange={(v) => patch({ count_id: v || null })}
            options={counts}
            placeholder="Count..."
          />
        </div>
        <div className="w-40 shrink-0">
          <Select
            label="Egasi (bo'sh = o'z)"
            value={line.owner_id ?? ""}
            onValueChange={(v) => patch({ owner_id: v || null })}
            options={[{ value: "", label: "O'z (own)" }, ...counterparties]}
          />
        </div>
        {commonQty}
        <div className="w-24 shrink-0">
          <Input
            label="Qoplar"
            type="number" min="0"
            value={line.quantity_bags ?? ""}
            onChange={(e) => patch({ quantity_bags: parseInt(e.target.value) || null })}
          />
        </div>
        <div className="min-w-0 flex-1">
          <Input
            label="Izoh"
            value={line.notes ?? ""}
            onChange={(e) => patch({ notes: e.target.value || null })}
          />
        </div>
        {removeBtn}
      </div>
    );
  }

  if (warehouseType === "RAW_COTTON" && line.line_category === "RECEIPT") {
    return (
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <div className="w-44 shrink-0">
          <Select
            label="Egasi (bo'sh = o'z)"
            value={line.owner_id ?? ""}
            onValueChange={(v) => patch({ owner_id: v || null })}
            options={[{ value: "", label: "O'z (own)" }, ...counterparties]}
          />
        </div>
        {commonQty}
        <div className="w-28 shrink-0">
          <Input
            label="Kip"
            type="number" step="0.001" min="0"
            value={line.quantity_kip ?? ""}
            onChange={(e) => patch({ quantity_kip: parseFloat(e.target.value) || null })}
          />
        </div>
        <div className="min-w-0 flex-1">
          <Input
            label="Izoh"
            value={line.notes ?? ""}
            onChange={(e) => patch({ notes: e.target.value || null })}
          />
        </div>
        {removeBtn}
      </div>
    );
  }

  if (warehouseType === "RAW_COTTON" && line.line_category === "PRODUCTION_ISSUE") {
    return (
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <div className="w-44 shrink-0">
          <Select
            label="Lot (tayyor mahsulot)"
            value={line.lot_id ?? ""}
            onValueChange={(v) => patch({ lot_id: v || null })}
            options={lots}
            placeholder="Lot tanlang..."
          />
        </div>
        <div className="w-44 shrink-0">
          <Select
            label="Egasi (bo'sh = o'z)"
            value={line.owner_id ?? ""}
            onValueChange={(v) => patch({ owner_id: v || null })}
            options={[{ value: "", label: "O'z (own)" }, ...counterparties]}
          />
        </div>
        {commonQty}
        <div className="min-w-0 flex-1">
          <Input
            label="Izoh"
            value={line.notes ?? ""}
            onChange={(e) => patch({ notes: e.target.value || null })}
          />
        </div>
        {removeBtn}
      </div>
    );
  }

  if (warehouseType === "WASTE") {
    return (
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
        <div className="w-40 shrink-0">
          <Select
            label="Chiqindi turi"
            value={line.waste_type ?? ""}
            onValueChange={(v) => patch({ waste_type: (v || null) as DailyReportLineCreate["waste_type"] })}
            options={WASTE_TYPES}
            placeholder="Tur tanlang..."
          />
        </div>
        {commonQty}
        {showBuyer && (
          <div className="w-44 shrink-0">
            <Select
              label="Xaridor"
              value={line.buyer_id ?? ""}
              onValueChange={(v) => patch({ buyer_id: v || null })}
              options={counterparties}
              placeholder="Xaridor tanlang..."
            />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <Input
            label="Izoh"
            value={line.notes ?? ""}
            onChange={(e) => patch({ notes: e.target.value || null })}
          />
        </div>
        {removeBtn}
      </div>
    );
  }

  // PACKAGING
  return (
    <div className="flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 bg-white p-3">
      <div className="w-44 shrink-0">
        <Select
          label="Qadoqlash turi"
          value={line.pkg_item_type ?? ""}
          onValueChange={(v) => patch({ pkg_item_type: (v || null) as DailyReportLineCreate["pkg_item_type"] })}
          options={PKG_TYPES}
          placeholder="Tur tanlang..."
        />
      </div>
      {commonQty}
      <div className="w-24 shrink-0">
        <Input
          label="Dona"
          type="number" min="0"
          value={line.quantity_units ?? ""}
          onChange={(e) => patch({ quantity_units: parseInt(e.target.value) || null })}
        />
      </div>
      <div className="min-w-0 flex-1">
        <Input
          label="Izoh"
          value={line.notes ?? ""}
          onChange={(e) => patch({ notes: e.target.value || null })}
        />
      </div>
      {removeBtn}
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────

export default function DailyReportPage() {
  const { language, activeRole } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();
  const isAdmin = activeRole === "ADMIN";
  const isManager = activeRole === "ADMIN" || activeRole === "DEPUTY_DIRECTOR";

  const today = format(new Date(), "yyyy-MM-dd");
  const [reportDate, setReportDate] = useState(today);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState("");
  const [lines, setLines] = useState<DailyReportLineCreate[]>([]);
  const [collapsedOB, setCollapsedOB] = useState(false);
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [reopenReason, setReopenReason] = useState("");

  // ── Master data queries ──────────────────────────────────────────────────

  const { data: warehousesData } = useQuery({
    queryKey: ["warehouses-dropdown"],
    queryFn: () => warehouseApi.list({ active_only: true, page_size: 200 }),
  });
  const warehouses: Warehouse[] = warehousesData?.items ?? [];
  const warehouseOptions = warehouses.map((w) => ({
    value: w.id,
    label: `${w.name} (${w.warehouse_type})`,
  }));

  const selectedWarehouse = warehouses.find((w) => w.id === selectedWarehouseId);
  const whType = selectedWarehouse?.warehouse_type as WarehouseType | undefined;

  const needsLots = whType === "FINISHED_GOODS" || whType === "RAW_COTTON";
  const needsCounts = whType === "FINISHED_GOODS";

  const { data: lotsData } = useQuery({
    queryKey: ["lots-open"],
    queryFn: () => lotApi.list({ status: "OPEN", page_size: 200 }),
    enabled: needsLots,
  });
  const lotOptions = (lotsData?.items ?? []).map((l: Lot) => ({
    value: l.id,
    label: l.lot_number,
  }));

  const { data: countsData } = useQuery({
    queryKey: ["counts-active"],
    queryFn: () => countApi.list({ active_only: true, page_size: 200 }),
    enabled: needsCounts,
  });
  const countOptions = (countsData?.items ?? []).map((c) => ({
    value: c.id,
    label: c.count_value,
  }));

  const { data: counterpartiesData } = useQuery({
    queryKey: ["counterparties-active"],
    queryFn: () => counterpartyApi.list({ active_only: true, page_size: 200 }),
    enabled: !!whType,
  });
  const cpOptions = (counterpartiesData?.items ?? []).map((c) => ({
    value: c.id,
    label: c.name,
  }));

  // ── Report query ─────────────────────────────────────────────────────────

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ["daily-report", selectedWarehouseId, reportDate],
    queryFn: () =>
      dailyReportApi.getOrCreate({
        warehouse_id: selectedWarehouseId,
        report_date: reportDate,
      }),
    enabled: !!selectedWarehouseId,
  });

  // Sync lines from existing DRAFT report when it loads
  useEffect(() => {
    if (report?.status === "DRAFT") {
      if (report.lines.length > 0) {
        setLines(
          report.lines.map((l) => ({
            line_category: l.line_category,
            lot_id: l.lot_id ?? null,
            count_id: l.count_id ?? null,
            owner_id: l.owner_id ?? null,
            waste_type: l.waste_type ?? null,
            buyer_id: l.buyer_id ?? null,
            pkg_item_type: l.pkg_item_type ?? null,
            quantity_kg: Number(l.quantity_kg),
            quantity_bags: l.quantity_bags ?? null,
            quantity_kip: l.quantity_kip ?? null,
            quantity_units: l.quantity_units ?? null,
            notes: l.notes ?? null,
          }))
        );
      } else {
        setLines([]);
      }
    }
  }, [report?.id, report?.status]);

  // Reset lines when warehouse or date changes
  useEffect(() => {
    setLines([]);
  }, [selectedWarehouseId, reportDate]);

  // ── Mutations ─────────────────────────────────────────────────────────────

  const saveDraftMut = useMutation({
    mutationFn: () => dailyReportApi.updateLines(report!.id, lines),
    onSuccess: () => toast.success(t("Qoralama saqlandi", "Черновик сохранён")),
    onError: (e: Error) => toast.error(e.message),
  });

  const submitMut = useMutation({
    mutationFn: () => dailyReportApi.submit(report!.id, lines),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-report"] });
      toast.success(t("Hisobot yuborildi", "Отчёт отправлен"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const closeMut = useMutation({
    mutationFn: () => dailyReportApi.close(report!.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-report"] });
      toast.success(t("Hisobot yopildi", "Отчёт закрыт"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const reopenMut = useMutation({
    mutationFn: () => dailyReportApi.reopen(report!.id, reopenReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-report"] });
      setShowReopenModal(false);
      setReopenReason("");
      toast.success(t("Qayta ochildi", "Переоткрыт"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // ── Line management ───────────────────────────────────────────────────────

  const addLine = (category: string) => {
    setLines((prev) => [...prev, emptyLine(category)]);
  };

  const updateLine = useCallback(
    (idx: number, patch: Partial<DailyReportLineCreate>) => {
      setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
    },
    []
  );

  const removeLine = useCallback((idx: number) => {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  // ── Opening balance columns ────────────────────────────────────────────

  const obColumns: ColumnDef<OpeningBalanceLine>[] = [
    ...(whType === "WASTE"
      ? [{ accessorKey: "waste_type" as const, header: "Tur", cell: ({ getValue }: any) => getValue() || "—" }]
      : whType === "PACKAGING"
      ? [{ accessorKey: "pkg_item_type" as const, header: "Tur", cell: ({ getValue }: any) => getValue() || "—" }]
      : whType === "RAW_COTTON"
      ? [{ accessorKey: "owner_name" as const, header: t("Egasi", "Владелец"), cell: ({ getValue }: any) => getValue() || t("O'z", "Своё") }]
      : [
          { accessorKey: "lot_number" as const, header: "Lot", cell: ({ getValue }: any) => <span className="font-mono font-semibold">{getValue() || "—"}</span> },
          { accessorKey: "count_value" as const, header: "Count", cell: ({ getValue }: any) => getValue() || "—" },
          { accessorKey: "owner_name" as const, header: t("Egasi", "Владелец"), cell: ({ getValue }: any) => getValue() || t("O'z", "Своё") },
        ]),
    {
      accessorKey: "quantity_kg",
      header: "kg",
      cell: ({ getValue }: any) => (
        <span className="font-medium tabular-nums">
          {Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}
        </span>
      ),
    },
    ...(whType === "FINISHED_GOODS"
      ? [{ accessorKey: "quantity_bags" as const, header: t("Qoplar", "Мешки"), cell: ({ getValue }: any) => getValue() ?? "—" }]
      : whType === "PACKAGING"
      ? [{ accessorKey: "quantity_units" as const, header: t("Dona", "Шт."), cell: ({ getValue }: any) => getValue() ?? "—" }]
      : []),
  ];

  // ── Read-only submitted lines columns ─────────────────────────────────────

  const readOnlyColumns: ColumnDef<any>[] = [
    { accessorKey: "line_number", header: "#", size: 40 },
    { accessorKey: "line_category", header: t("Kategoriya", "Категория") },
    ...(needsLots
      ? [
          { accessorKey: "lot_id", header: "Lot", cell: ({ row }: any) => <span className="font-mono text-xs">{row.original.lot_id?.slice(0, 8) ?? "—"}…</span> },
          { accessorKey: "owner_id", header: t("Egasi", "Владелец"), cell: ({ getValue }: any) => getValue() ? "tolling" : t("O'z", "Своё") },
        ]
      : whType === "WASTE"
      ? [{ accessorKey: "waste_type", header: "Tur" }]
      : [{ accessorKey: "pkg_item_type", header: "Tur" }]),
    {
      accessorKey: "quantity_kg",
      header: "kg",
      cell: ({ getValue }: any) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    { accessorKey: "quantity_bags", header: t("Qoplar", "Мешки"), cell: ({ getValue }: any) => getValue() ?? "—" },
    { accessorKey: "notes", header: t("Izoh", "Примечание"), cell: ({ getValue }: any) => getValue() || "—" },
  ];

  const isDraft = report?.status === "DRAFT";
  const sections = whType ? SECTIONS[whType] : [];

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="pb-10">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">
          {t("Kunlik ombor hisoboti", "Суточный складской отчёт")}
        </h1>
        {report && (
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_VARIANT[report.status]}>
              {STATUS_LABEL[report.status]}
            </Badge>
            <Button
              variant="outline" size="sm"
              onClick={() => exportApi.dailyReport(report.id)}
            >
              <Download size={14} /> Excel
            </Button>
          </div>
        )}
      </div>

      {/* Warehouse + Date selectors */}
      <div className="mb-5 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <div className="w-72">
          <Select
            label={t("Ombor *", "Склад *")}
            value={selectedWarehouseId}
            onValueChange={(v) => setSelectedWarehouseId(v)}
            options={warehouseOptions}
            placeholder={t("Ombor tanlang...", "Выберите склад...")}
          />
        </div>
        <div className="w-48">
          <Input
            label={t("Sana *", "Дата *")}
            type="date"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
          />
        </div>
        {selectedWarehouse && (
          <div className="flex items-center gap-1.5 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
            {WH_ICON[selectedWarehouse.warehouse_type as WarehouseType]}
            <span className="font-medium">{selectedWarehouse.warehouse_type}</span>
          </div>
        )}
      </div>

      {/* Empty state */}
      {!selectedWarehouseId && (
        <div className="rounded-xl border-2 border-dashed border-slate-200 p-12 text-center text-slate-400">
          <Box size={32} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">{t("Hisobotni boshlash uchun ombor tanlang", "Выберите склад для начала отчёта")}</p>
        </div>
      )}

      {selectedWarehouseId && reportLoading && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">
          {t("Yuklanmoqda...", "Загрузка...")}
        </div>
      )}

      {report && whType && (
        <>
          {/* ── Opening balance ── */}
          <div className="mb-5 rounded-xl border border-slate-200 bg-white">
            <button
              type="button"
              onClick={() => setCollapsedOB((v) => !v)}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div>
                <p className="text-sm font-semibold text-slate-700">
                  {t("Oldingi kun qoldig'i", "Остаток предыдущего дня")}
                </p>
                <p className="text-xs text-slate-400">
                  {t("Avtomatik hisoblab chiqiladi", "Вычисляется автоматически")} · {report.opening_balance.length} {t("qator", "строк")}
                </p>
              </div>
              {collapsedOB ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronUp size={16} className="text-slate-400" />}
            </button>
            {!collapsedOB && (
              <div className="border-t border-slate-100 p-4">
                {report.opening_balance.length === 0 ? (
                  <p className="text-center text-sm text-slate-400">
                    {t("Qoldiq yo'q (birinchi kun)", "Остатков нет (первый день)")}
                  </p>
                ) : (
                  <DataTable
                    data={report.opening_balance}
                    columns={obColumns}
                    isLoading={false}
                    emptyText="—"
                  />
                )}
              </div>
            )}
          </div>

          {/* ── Line entry (DRAFT only) ── */}
          {isDraft ? (
            <div className="space-y-4">
              {sections.map((section) => {
                const sectionLines = lines
                  .map((l, i) => ({ line: l, idx: i }))
                  .filter(({ line }) => line.line_category === section.category);

                const colorCls =
                  section.color === "green"
                    ? "border-green-200 bg-green-50"
                    : "border-red-200 bg-red-50";
                const headerCls =
                  section.color === "green"
                    ? "text-green-800 bg-green-100"
                    : "text-red-800 bg-red-100";
                const badgeCls =
                  section.color === "green"
                    ? "bg-green-600"
                    : "bg-red-600";

                return (
                  <div key={section.category} className={`rounded-xl border ${colorCls}`}>
                    {/* Section header */}
                    <div className={`flex items-center justify-between rounded-t-xl px-4 py-2.5 ${headerCls}`}>
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold text-white ${badgeCls}`}>
                          {sectionLines.length}
                        </span>
                        <span className="text-sm font-semibold">{section.label}</span>
                      </div>
                      <Button
                        type="button" size="sm" variant="outline"
                        className="h-7 text-xs"
                        onClick={() => addLine(section.category)}
                      >
                        <Plus size={12} /> {t("Qator qo'sh", "Добавить")}
                      </Button>
                    </div>

                    {/* Lines */}
                    <div className="space-y-2 p-3">
                      {sectionLines.length === 0 ? (
                        <div className="rounded-lg border border-dashed border-slate-300 py-4 text-center text-xs text-slate-400">
                          {t("Hali qator yo'q — «Qator qo'sh» tugmasini bosing", "Строк нет — нажмите «Добавить»")}
                        </div>
                      ) : (
                        sectionLines.map(({ line, idx }) => (
                          <LineRow
                            key={idx}
                            line={line}
                            index={idx}
                            onChange={updateLine}
                            onRemove={removeLine}
                            lots={lotOptions}
                            counts={countOptions}
                            counterparties={cpOptions}
                            warehouseType={whType}
                            showBuyer={section.direction === "out"}
                          />
                        ))
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Summary + actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
                <div className="text-sm text-slate-500">
                  {t("Jami qatorlar", "Всего строк")}: <strong>{lines.length}</strong>
                  {" · "}
                  {t("Jami kg", "Итого кг")}: <strong>{lines.reduce((s, l) => s + (l.quantity_kg || 0), 0).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}</strong>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline" size="sm"
                    loading={saveDraftMut.isPending}
                    onClick={() => saveDraftMut.mutate()}
                    disabled={lines.length === 0}
                  >
                    {t("Saqlash (qoralama)", "Сохранить черновик")}
                  </Button>
                  <Button
                    size="sm"
                    loading={submitMut.isPending}
                    onClick={() => submitMut.mutate()}
                    disabled={lines.length === 0}
                  >
                    <Send size={14} /> {t("Yuborish", "Отправить")}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            /* ── Read-only view (SUBMITTED / CLOSED) ── */
            <div className="rounded-xl border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-semibold text-slate-700">
                  {t("Hisobot qatorlari", "Строки отчёта")} ({report.lines.length})
                </p>
                {report.submitted_at && (
                  <p className="text-xs text-slate-400">
                    {t("Yuborilgan", "Отправлен")}: {new Date(report.submitted_at).toLocaleString("ru-RU")}
                  </p>
                )}
              </div>
              <div className="p-4">
                <DataTable
                  data={report.lines}
                  columns={readOnlyColumns}
                  isLoading={false}
                  emptyText={t("Qatorlar yo'q", "Строк нет")}
                />
              </div>

              {/* SUBMITTED/CLOSED actions */}
              <div className="flex gap-2 border-t border-slate-100 px-4 py-3">
                {report.status === "SUBMITTED" && isManager && (
                  <Button size="sm" loading={closeMut.isPending} onClick={() => closeMut.mutate()}>
                    <CheckCircle size={14} /> {t("Yopish (tasdiqlash)", "Закрыть (подтвердить)")}
                  </Button>
                )}
                {(report.status === "SUBMITTED" || report.status === "CLOSED") && isAdmin && (
                  <Button
                    variant="outline" size="sm"
                    onClick={() => { setShowReopenModal(true); setReopenReason(""); }}
                  >
                    <RotateCcw size={14} /> {t("Qayta ochish", "Переоткрыть")}
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Reopen count badge */}
          {(report.reopen_count ?? 0) > 0 && (
            <p className="mt-2 text-xs text-slate-400">
              {t("Qayta ochilganlar soni", "Переоткрывалось")}: {report.reopen_count}
            </p>
          )}
        </>
      )}

      {/* ── Reopen modal ──────────────────────────────────────────────────── */}
      <Modal
        open={showReopenModal}
        onOpenChange={(v) => { if (!v) setShowReopenModal(false); }}
        title={t("Hisobotni qayta ochish", "Переоткрыть отчёт")}
      >
        <div className="flex flex-col gap-4">
          <p className="text-sm text-amber-700 bg-amber-50 rounded-lg p-3">
            {t(
              "Diqqat: qayta ochish barcha tranzaksiyalarni bekor qiladi. Bu amal qaytarib bo'lmaydi.",
              "Внимание: переоткрытие отменит все транзакции. Это действие необратимо."
            )}
          </p>
          <Input
            label={t("Sabab (kamida 10 belgi) *", "Причина (не менее 10 символов) *")}
            value={reopenReason}
            onChange={(e) => setReopenReason(e.target.value)}
            placeholder={t("Qayta ochish sababi...", "Укажите причину...")}
          />
          <ModalFooter>
            <Button variant="outline" onClick={() => setShowReopenModal(false)}>
              {t("Bekor", "Отмена")}
            </Button>
            <Button
              variant="danger"
              loading={reopenMut.isPending}
              disabled={reopenReason.length < 10}
              onClick={() => reopenMut.mutate()}
            >
              {t("Qayta ochish", "Переоткрыть")}
            </Button>
          </ModalFooter>
        </div>
      </Modal>
    </div>
  );
}

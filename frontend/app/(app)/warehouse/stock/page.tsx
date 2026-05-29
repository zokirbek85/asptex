"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { stockApi, type FinishedGoodsStockItem, type RawCottonStockItem, type WasteStockItem, type PackagingStockItem } from "@/lib/api/stock";
import { warehouseApi } from "@/lib/api/warehouse";
import { exportApi } from "@/lib/api/export";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import type { WarehouseType } from "@/lib/types";

const TAB_FOR_TYPE: Record<WarehouseType, string> = {
  FINISHED_GOODS: "finished",
  RAW_COTTON: "raw",
  WASTE: "waste",
  PACKAGING: "packaging",
};

const TABS = [
  { id: "finished",  label: "Tayyor mahsulot", labelRu: "Готовая продукция" },
  { id: "raw",       label: "Paxta tolasi",    labelRu: "Хлопок-волокно"    },
  { id: "waste",     label: "Chiqindilar",     labelRu: "Отходы"            },
  { id: "packaging", label: "Qadoqlash",       labelRu: "Упаковка"          },
];

export default function StockPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const [tab, setTab] = useState("finished");
  const [warehouseId, setWarehouseId] = useState("");

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-all"],
    queryFn: () => warehouseApi.list({ active_only: true, page_size: 200 }),
  });
  const warehouses = warehousesPage?.items ?? [];
  const selectedWarehouse = warehouses.find((w) => w.id === warehouseId);

  // Auto-switch tab when warehouse type changes
  useEffect(() => {
    if (selectedWarehouse?.warehouse_type) {
      setTab(TAB_FOR_TYPE[selectedWarehouse.warehouse_type]);
    }
  }, [selectedWarehouse?.warehouse_type]);

  const { data: fgStock, isLoading: fgLoading } = useQuery({
    queryKey: ["stock-fg", warehouseId],
    queryFn: () => stockApi.finishedGoods({ warehouse_id: warehouseId }),
    enabled: !!warehouseId && tab === "finished",
  });

  const { data: rcStock, isLoading: rcLoading } = useQuery({
    queryKey: ["stock-rc", warehouseId],
    queryFn: () => stockApi.rawCotton({ warehouse_id: warehouseId }),
    enabled: !!warehouseId && tab === "raw",
  });

  const { data: wasteStock, isLoading: wasteLoading } = useQuery({
    queryKey: ["stock-waste", warehouseId],
    queryFn: () => stockApi.waste({ warehouse_id: warehouseId }),
    enabled: !!warehouseId && tab === "waste",
  });

  const { data: pkgStock, isLoading: pkgLoading } = useQuery({
    queryKey: ["stock-pkg", warehouseId],
    queryFn: () => stockApi.packaging({ warehouse_id: warehouseId }),
    enabled: !!warehouseId && tab === "packaging",
  });

  const fgColumns: ColumnDef<FinishedGoodsStockItem>[] = [
    { accessorKey: "lot_number", header: "Lot", cell: ({ getValue }) => <span className="font-mono font-semibold">{getValue() as string}</span> },
    {
      accessorKey: "lot_status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as string;
        return <Badge variant={s === "OPEN" ? "success" : s === "BLOCKED" ? "danger" : "default"}>{s}</Badge>;
      },
    },
    { accessorKey: "count_value", header: "Count",                cell: ({ getValue }) => getValue() || "—" },
    { accessorKey: "owner_name",  header: t("Egasi", "Владелец"), cell: ({ getValue }) => getValue() || t("O'z", "Своё") },
    { accessorKey: "quantity_kg", header: "Qty (kg)",             cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
    { accessorKey: "quantity_bags", header: t("Qoplar", "Мешки"), cell: ({ getValue }) => getValue() ?? "—" },
  ];

  const rcColumns: ColumnDef<RawCottonStockItem>[] = [
    { accessorKey: "lot_number",  header: "Lot",                  cell: ({ getValue }) => getValue() || "—" },
    { accessorKey: "count_value", header: "Count",                cell: ({ getValue }) => getValue() || "—" },
    { accessorKey: "owner_name",  header: t("Egasi", "Владелец"), cell: ({ getValue }) => getValue() || t("O'z", "Своё") },
    { accessorKey: "quantity_kg", header: "Qty (kg)",             cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
    { accessorKey: "quantity_kip", header: "Qty (kip)",           cell: ({ getValue }) => getValue() ? Number(getValue()).toLocaleString() : "—" },
  ];

  const wasteColumns: ColumnDef<WasteStockItem>[] = [
    { accessorKey: "display_name", header: t("Tur", "Тип") },
    { accessorKey: "quantity_kg",  header: "Qty (kg)", cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
  ];

  const pkgColumns: ColumnDef<PackagingStockItem>[] = [
    { accessorKey: "display_name", header: t("Tur", "Тип") },
    {
      id: "qty",
      header: t("Miqdor", "Количество"),
      cell: ({ row }) => {
        const item = row.original;
        if (item.unit_type === "kg") {
          return `${Number(item.quantity_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg`;
        }
        return item.quantity_units != null
          ? `${item.quantity_units} ${item.unit_type}`
          : "—";
      },
    },
  ];

  const warehouseTypeMap: Record<string, string> = {
    finished: "FINISHED_GOODS",
    raw:      "RAW_COTTON",
    waste:    "WASTE",
    packaging: "PACKAGING",
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Ombor qoldig'i", "Остатки склада")}</h1>
        <Button
          variant="outline" size="sm"
          onClick={() => exportApi.stockReport({ warehouse_type: warehouseTypeMap[tab], fmt: "xlsx" })}
        >
          <Download size={14} /> Excel
        </Button>
      </div>

      {/* Warehouse selector */}
      <div className="mb-4 w-72">
        <Select
          label={t("Ombor", "Склад")}
          value={warehouseId}
          onValueChange={setWarehouseId}
          options={warehouses.map((w) => ({
            value: w.id,
            label: `${w.name} (${w.code})`,
          }))}
          placeholder={t("Ombor tanlang", "Выберите склад")}
        />
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
        {TABS.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === tb.id
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {language === "uz" ? tb.label : tb.labelRu}
          </button>
        ))}
      </div>

      {!warehouseId && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-400">
          {t("Ombor tanlang", "Выберите склад")}
        </div>
      )}

      {warehouseId && tab === "finished" && (
        <DataTable data={fgStock ?? []} columns={fgColumns} isLoading={fgLoading} emptyText={t("Ma'lumot yo'q", "Нет данных")} />
      )}
      {warehouseId && tab === "raw" && (
        <DataTable data={rcStock ?? []} columns={rcColumns} isLoading={rcLoading} emptyText={t("Ma'lumot yo'q", "Нет данных")} />
      )}
      {warehouseId && tab === "waste" && (
        <DataTable data={wasteStock ?? []} columns={wasteColumns} isLoading={wasteLoading} emptyText={t("Ma'lumot yo'q", "Нет данных")} />
      )}
      {warehouseId && tab === "packaging" && (
        <DataTable data={pkgStock ?? []} columns={pkgColumns} isLoading={pkgLoading} emptyText={t("Ma'lumot yo'q", "Нет данных")} />
      )}
    </div>
  );
}

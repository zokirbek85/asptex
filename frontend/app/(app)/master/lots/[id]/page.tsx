"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Package } from "lucide-react";

import { lotApi } from "@/lib/api/lot";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import type { StockSummaryItem } from "@/lib/types";
import type { ColumnDef } from "@tanstack/react-table";
import { formatNumber, formatDate } from "@/lib/utils";

interface Props {
  params: Promise<{ id: string }>;
}

export default function LotDetailPage({ params }: Props) {
  const { id } = use(params);
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;

  const { data: lot, isLoading: lotLoading } = useQuery({
    queryKey: ["lot", id],
    queryFn: () => lotApi.get(id, false),
  });

  const { data: stock, isLoading: stockLoading } = useQuery({
    queryKey: ["lot-stock", id],
    queryFn: () => lotApi.getStock(id),
  });

  const stockVariant = (s: string) =>
    s === "OPEN" ? "success" : s === "BLOCKED" ? "danger" : "default";

  const columns: ColumnDef<StockSummaryItem>[] = [
    { accessorKey: "warehouse_name", header: t("Ombor", "Склад") },
    { accessorKey: "count_value", header: "Count" },
    { accessorKey: "owner_name", header: t("Egasi", "Собственник"), cell: ({ getValue }) => (getValue() as string | null) || t("O'z", "Свой") },
    {
      accessorKey: "total_kg",
      header: t("Qoldiq (kg)", "Остаток (кг)"),
      cell: ({ getValue }) => {
        const v = getValue() as number;
        return <span className={v < 0 ? "text-red-600 font-semibold" : ""}>{formatNumber(v)}</span>;
      },
    },
  ];

  if (lotLoading) return <div className="p-8 text-center text-gray-400">Loading…</div>;
  if (!lot) return <div className="p-8 text-center text-red-500">Not found</div>;

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/master/lots"><ArrowLeft size={16} /></Link>
        </Button>
        <div className="flex items-center gap-2">
          <Package size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900 font-mono">{lot.lot_number}</h1>
          <Badge variant={stockVariant(lot.status)}>{lot.status}</Badge>
          {lot.auto_closed && <Badge variant="warning">{t("Avtomatik yopildi", "Авто-закрыт")}</Badge>}
        </div>
      </div>

      {/* Meta */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        {[
          { label: t("Ochildi", "Открыт"), value: formatDate(lot.opened_at, language) },
          { label: t("Yopildi", "Закрыт"), value: lot.closed_at ? formatDate(lot.closed_at, language) : "—" },
          { label: t("Yil", "Год"), value: String(lot.year) },
          { label: t("Tartib raqami", "Порядковый номер"), value: String(lot.sequence_number) },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-sm font-semibold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      {lot.close_reason && (
        <div className="mb-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
          {t("Yopilish sababi", "Причина закрытия")}: {lot.close_reason}
        </div>
      )}

      {lot.notes && (
        <div className="mb-4 bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700">
          {lot.notes}
        </div>
      )}

      <h2 className="text-base font-semibold text-gray-900 mb-3">{t("Qoldiq holati", "Текущие остатки")}</h2>
      <DataTable
        data={stock ?? []}
        columns={columns}
        isLoading={stockLoading}
        emptyText={t("Qoldiq yo'q", "Остатков нет")}
      />
    </div>
  );
}

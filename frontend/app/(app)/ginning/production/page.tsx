"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Eye } from "lucide-react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { ginningProductionApi, type GinningProductionOrder, type GinningProductionStatus } from "@/lib/api/ginningProduction";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";

const STATUS_VARIANT: Record<GinningProductionStatus, "success" | "warning" | "danger"> = {
  DRAFT: "warning", COMPLETED: "success", CANCELLED: "danger",
};

export default function GinningProductionPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);

  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["ginning-production", page],
    queryFn: () => ginningProductionApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const columns: ColumnDef<GinningProductionOrder>[] = [
    {
      accessorKey: "production_number",
      header: t("№", "№"),
      cell: ({ row }) => (
        <Link href={`/ginning/production/${row.original.id}`} className="font-mono font-semibold text-blue-600 hover:underline">
          {row.original.production_number}
        </Link>
      ),
    },
    { accessorKey: "production_date", header: t("Sana", "Дата"), cell: ({ getValue }) => formatDate(getValue() as string, language) },
    {
      accessorKey: "total_input_kg",
      header: t("Kirish kg", "Вход кг"),
      cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    {
      accessorKey: "total_output_kg",
      header: t("Chiqish kg", "Выход кг"),
      cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    {
      accessorKey: "yield_pct",
      header: t("Unum %", "Выход %"),
      cell: ({ getValue }) => `${Number(getValue()).toFixed(2)}%`,
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as GinningProductionStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s}</Badge>;
      },
    },
    {
      id: "actions",
      size: 60,
      cell: ({ row }) => (
        <Button variant="ghost" size="icon" asChild>
          <Link href={`/ginning/production/${row.original.id}`}><Eye size={14} /></Link>
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Ishlab chiqarish buyurtmalari", "Заказы на производство")}</h1>
        <Button size="sm" asChild>
          <Link href="/ginning/production/new"><Plus size={15} /> {t("Yangi buyurtma", "Новый заказ")}</Link>
        </Button>
      </div>

      <DataTable
        data={data?.items ?? []}
        columns={columns}
        isLoading={isLoading}
        pageCount={data?.pages}
        pagination={{ pageIndex: page, pageSize: PAGE_SIZE }}
        onPaginationChange={(updater) => {
          const next = typeof updater === "function" ? updater({ pageIndex: page, pageSize: PAGE_SIZE }) : updater;
          setPage(next.pageIndex);
        }}
        emptyText={t("Buyurtmalar topilmadi", "Заказы не найдены")}
      />
    </div>
  );
}

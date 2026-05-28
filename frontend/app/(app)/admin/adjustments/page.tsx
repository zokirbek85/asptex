"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Eye, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { adjustmentApi, type AdjustmentCreate, type AdjustmentResponse } from "@/lib/api/adjustment";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";
import type { AdjustmentStatus } from "@/lib/types";

const createSchema = z.object({
  warehouse_id: z.string().uuid("Valid UUID required"),
  adjustment_date: z.string().min(1),
  reason: z.string().min(10, "Minimum 10 characters"),
});

type CreateForm = z.infer<typeof createSchema>;

const STATUS_VARIANT: Record<AdjustmentStatus, "warning" | "success"> = {
  DRAFT: "warning",
  POSTED: "success",
};

export default function AdjustmentsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["adjustments", page],
    queryFn: () => adjustmentApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["adjustment", detailId],
    queryFn: () => adjustmentApi.get(detailId!),
    enabled: !!detailId,
  });

  const form = useForm<CreateForm>({ resolver: zodResolver(createSchema) });

  const createMut = useMutation({
    mutationFn: (body: AdjustmentCreate) => adjustmentApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["adjustments"] });
      setShowCreate(false);
      form.reset();
      toast.success(t("Korrektura yaratildi", "Корректировка создана"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const postMut = useMutation({
    mutationFn: (id: string) => adjustmentApi.post(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["adjustments"] });
      qc.invalidateQueries({ queryKey: ["adjustment", detailId] });
      toast.success(t("Korrektura qo'llandi", "Корректировка применена"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<AdjustmentResponse>[] = [
    {
      accessorKey: "adjustment_number",
      header: t("Raqam", "Номер"),
      cell: ({ row }) => (
        <button
          className="font-mono font-semibold text-blue-600 hover:underline"
          onClick={() => setDetailId(row.original.id)}
        >
          {row.original.adjustment_number}
        </button>
      ),
    },
    {
      accessorKey: "adjustment_date",
      header: t("Sana", "Дата"),
      cell: ({ getValue }) => formatDate(getValue() as string, language),
    },
    {
      accessorKey: "reason",
      header: t("Sabab", "Причина"),
      cell: ({ getValue }) => <span className="line-clamp-1 text-xs">{getValue() as string}</span>,
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as AdjustmentStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s}</Badge>;
      },
    },
    {
      accessorKey: "lines",
      header: t("Qatorlar", "Строк"),
      cell: ({ getValue }) => (getValue() as unknown[]).length,
    },
    {
      id: "actions",
      size: 80,
      cell: ({ row }) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="icon" onClick={() => setDetailId(row.original.id)}>
            <Eye size={14} />
          </Button>
          {row.original.status === "DRAFT" && (
            <Button
              variant="ghost" size="icon"
              title={t("Qo'llash", "Применить")}
              onClick={() => postMut.mutate(row.original.id)}
              loading={postMut.isPending}
            >
              <CheckCircle size={14} className="text-green-600" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Inventarizatsiya korrekturalari", "Инвентарные корректировки")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi korrektura", "Новая корректировка")}
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
        emptyText={t("Korrekturalar topilmadi", "Корректировки не найдены")}
      />

      {/* Create Modal */}
      <Modal
        open={showCreate}
        onOpenChange={(v) => { if (!v) { setShowCreate(false); form.reset(); } }}
        title={t("Yangi korrektura", "Новая корректировка")}
      >
        <form onSubmit={form.handleSubmit((d) => createMut.mutate(d))} className="flex flex-col gap-4">
          <Input
            label={t("Ombor ID", "ID склада")}
            {...form.register("warehouse_id")}
            error={form.formState.errors.warehouse_id?.message}
          />
          <Input
            label={t("Sana", "Дата")}
            type="date"
            {...form.register("adjustment_date")}
            error={form.formState.errors.adjustment_date?.message}
          />
          <Input
            label={t("Sabab (min 10 belgi) *", "Причина (мин 10 симв.) *")}
            {...form.register("reason")}
            error={form.formState.errors.reason?.message}
          />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
              {t("Bekor", "Отмена")}
            </Button>
            <Button type="submit" loading={createMut.isPending}>{t("Yaratish", "Создать")}</Button>
          </ModalFooter>
        </form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        open={!!detailId}
        onOpenChange={(v) => { if (!v) setDetailId(null); }}
        title={detail ? `${detail.adjustment_number} — ${detail.status}` : ""}
      >
        {detailLoading && <p className="text-center text-slate-400 py-4">{t("Yuklanmoqda...", "Загрузка...")}</p>}
        {detail && (
          <div>
            <p className="mb-3 text-sm text-slate-500">{detail.reason}</p>
            <DataTable
              data={detail.lines}
              columns={[
                { accessorKey: "line_number", header: "#", size: 40 },
                { accessorKey: "waste_type", header: "Waste", cell: ({ getValue }) => getValue() || "—" },
                { accessorKey: "pkg_item_type", header: "Pkg", cell: ({ getValue }) => getValue() || "—" },
                { accessorKey: "quantity_kg_before", header: t("Oldin (kg)", "До (кг)"), cell: ({ getValue }) => Number(getValue()).toLocaleString() },
                { accessorKey: "quantity_kg_after", header: t("Keyin (kg)", "После (кг)"), cell: ({ getValue }) => Number(getValue()).toLocaleString() },
              ]}
              isLoading={false}
              emptyText="—"
            />
            {detail.status === "DRAFT" && (
              <div className="mt-4 flex justify-end">
                <Button
                  loading={postMut.isPending}
                  onClick={() => postMut.mutate(detail.id)}
                >
                  <CheckCircle size={14} /> {t("Qo'llash", "Применить")}
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

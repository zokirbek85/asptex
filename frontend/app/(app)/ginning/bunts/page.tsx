"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Eye, Lock, Unlock } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { ginningBuntApi, type GinningBunt, type BuntStatus } from "@/lib/api/ginningBunt";
import { warehouseApi } from "@/lib/api/warehouse";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const createSchema = z.object({
  warehouse_id: z.string().uuid("Ombor tanlang"),
  notes: z.string().optional().nullable(),
});
type CreateForm = z.infer<typeof createSchema>;

const STATUS_VARIANT: Record<BuntStatus, "success" | "default"> = {
  OPEN: "success",
  CLOSED: "default",
};

export default function GinningBuntsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["ginning-bunts", page],
    queryFn: () => ginningBuntApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-raw-cotton"],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "RAW_COTTON", page_size: 200 }),
    enabled: showCreate,
  });
  const warehouseOptions: SelectOption[] = (warehousesPage?.items ?? []).map((w) => ({
    value: w.id, label: `${w.name} (${w.code})`,
  }));

  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
  });

  const createMut = useMutation({
    mutationFn: ginningBuntApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ginning-bunts"] });
      setShowCreate(false);
      reset();
      toast.success(t("Bunt yaratildi", "Бунт создан"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const closeMut = useMutation({
    mutationFn: (id: string) => ginningBuntApi.close(id, t("Yopildi", "Закрыт")),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ginning-bunts"] }); toast.success(t("Bunt yopildi", "Бунт закрыт")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const reopenMut = useMutation({
    mutationFn: (id: string) => ginningBuntApi.reopen(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ginning-bunts"] }); toast.success(t("Bunt qayta ochildi", "Бунт снова открыт")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<GinningBunt>[] = [
    {
      accessorKey: "lot_number",
      header: t("Bunt raqami", "Номер бунта"),
      cell: ({ row }) => (
        <Link href={`/ginning/bunts/${row.original.id}`} className="font-mono font-semibold text-blue-600 hover:underline">
          {row.original.lot_number}
        </Link>
      ),
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      size: 100,
      cell: ({ getValue }) => {
        const s = getValue() as BuntStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s === "OPEN" ? t("Ochiq", "Открыт") : t("Yopiq", "Закрыт")}</Badge>;
      },
    },
    {
      accessorKey: "opened_at",
      header: t("Ochilgan sana", "Дата открытия"),
      cell: ({ getValue }) => formatDate(getValue() as string, language),
    },
    {
      accessorKey: "notes",
      header: t("Izoh", "Примечание"),
      cell: ({ getValue }) => (getValue() as string | null) || "—",
    },
    {
      id: "actions",
      size: 100,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/ginning/bunts/${row.original.id}`}><Eye size={14} /></Link>
          </Button>
          {row.original.status === "OPEN" ? (
            <Button variant="ghost" size="icon" onClick={() => closeMut.mutate(row.original.id)}>
              <Lock size={14} className="text-red-500" />
            </Button>
          ) : (
            <Button variant="ghost" size="icon" onClick={() => reopenMut.mutate(row.original.id)}>
              <Unlock size={14} className="text-green-500" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Buntlar (partiyalar)", "Бунты (партии)")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi bunt", "Новый бунт")}
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
        emptyText={t("Buntlar topilmadi", "Бунты не найдены")}
      />

      <Modal
        open={showCreate}
        onOpenChange={(v) => { setShowCreate(v); if (!v) reset(); }}
        title={t("Yangi bunt", "Новый бунт")}
      >
        <form onSubmit={handleSubmit((d) => createMut.mutate(d))} className="flex flex-col gap-4">
          <Controller
            control={control}
            name="warehouse_id"
            render={({ field }) => (
              <Select
                label={t("Xom ashyo ombori", "Склад сырья")}
                value={field.value}
                onValueChange={field.onChange}
                options={warehouseOptions}
                placeholder={t("Tanlang", "Выберите")}
                error={errors.warehouse_id?.message}
              />
            )}
          />
          <Input label={t("Izoh (ixtiyoriy)", "Примечание (необяз.)")} {...register("notes")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={createMut.isPending}>{t("Yaratish", "Создать")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

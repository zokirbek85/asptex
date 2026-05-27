"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Pencil, PowerOff, Power, Warehouse as WarehouseIcon } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { warehouseApi } from "@/lib/api/warehouse";
import type { Warehouse, WarehouseType } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";

const WAREHOUSE_TYPE_OPTIONS = [
  { value: "RAW_COTTON", label: "Xom ashyo / Сырьё" },
  { value: "FINISHED_GOODS", label: "Tayyor mahsulot / Готовая продукция" },
  { value: "WASTE", label: "Chiqindi / Отходы" },
  { value: "PACKAGING", label: "Qadoqlash / Упаковка" },
];

const schema = z.object({
  code: z.string().min(1).max(30),
  name: z.string().min(1).max(255),
  warehouse_type: z.enum(["RAW_COTTON", "FINISHED_GOODS", "WASTE", "PACKAGING"]),
  description: z.string().optional().nullable(),
  sort_order: z.coerce.number().int().min(0).max(9999).default(0),
});

type FormValues = z.infer<typeof schema>;

export default function WarehousesPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Warehouse | null>(null);

  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["warehouses", page],
    queryFn: () => warehouseApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { warehouse_type: "FINISHED_GOODS", sort_order: 0 },
  });

  const whType = watch("warehouse_type");

  const createMut = useMutation({
    mutationFn: warehouseApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["warehouses"] }); setModalOpen(false); reset(); toast.success(t("Ombor yaratildi", "Склад создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FormValues> }) => warehouseApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["warehouses"] }); setModalOpen(false); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? warehouseApi.deactivate(id) : warehouseApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["warehouses"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    reset({ code: "", name: "", warehouse_type: "FINISHED_GOODS", description: "", sort_order: 0 });
    setModalOpen(true);
  }

  function openEdit(wh: Warehouse) {
    setEditTarget(wh);
    reset({ name: wh.name, code: wh.code, warehouse_type: wh.warehouse_type, description: wh.description ?? "", sort_order: wh.sort_order });
    setModalOpen(true);
  }

  function onSubmit(values: FormValues) {
    if (editTarget) {
      updateMut.mutate({ id: editTarget.id, data: { name: values.name, description: values.description, sort_order: values.sort_order } });
    } else {
      createMut.mutate(values);
    }
  }

  const columns: ColumnDef<Warehouse>[] = [
    { accessorKey: "code", header: t("Kod", "Код"), size: 80 },
    { accessorKey: "name", header: t("Nomi", "Название"), cell: ({ getValue }) => <span className="font-medium">{getValue() as string}</span> },
    {
      accessorKey: "warehouse_type",
      header: t("Tur", "Тип"),
      cell: ({ getValue }) => {
        const opt = WAREHOUSE_TYPE_OPTIONS.find(o => o.value === getValue());
        return opt ? opt.label.split(" / ")[language === "uz" ? 0 : 1] : getValue() as string;
      },
    },
    {
      accessorKey: "is_active",
      header: t("Holat", "Статус"),
      size: 90,
      cell: ({ getValue }) => (
        <Badge variant={getValue() ? "success" : "danger"}>
          {getValue() ? t("Aktiv", "Активен") : t("Nofaol", "Неактивен")}
        </Badge>
      ),
    },
    {
      id: "actions",
      size: 90,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => openEdit(row.original)}>
            <Pencil size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => toggleMut.mutate({ id: row.original.id, active: row.original.is_active })}
          >
            {row.original.is_active ? <PowerOff size={14} className="text-red-500" /> : <Power size={14} className="text-green-500" />}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <WarehouseIcon size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">{t("Omborlar", "Склады")}</h1>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus size={15} />
          {t("Qo'shish", "Добавить")}
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
        emptyText={t("Omborlar topilmadi", "Склады не найдены")}
      />

      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) { setEditTarget(null); reset(); } }}
        title={editTarget ? t("Omborni tahrirlash", "Редактировать склад") : t("Yangi ombor", "Новый склад")}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            label={t("Kod *", "Код *")}
            {...register("code")}
            disabled={!!editTarget}
            error={errors.code?.message}
          />
          <Input label={t("Nomi *", "Название *")} {...register("name")} error={errors.name?.message} />
          {!editTarget && (
            <Select
              label={t("Tur *", "Тип *")}
              value={whType}
              onValueChange={(v) => setValue("warehouse_type", v as WarehouseType)}
              options={WAREHOUSE_TYPE_OPTIONS}
            />
          )}
          <Input label={t("Tavsif", "Описание")} {...register("description")} />
          <Input label={t("Tartib", "Порядок")} type="number" {...register("sort_order")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              {t("Bekor qilish", "Отмена")}
            </Button>
            <Button type="submit" loading={createMut.isPending || updateMut.isPending}>
              {editTarget ? t("Saqlash", "Сохранить") : t("Yaratish", "Создать")}
            </Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

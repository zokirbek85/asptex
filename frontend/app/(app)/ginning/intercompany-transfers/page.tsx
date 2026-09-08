"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Check, X } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { intercompanyTransferApi, type IntercompanyTransfer, type IntercompanyTransferStatus } from "@/lib/api/intercompanyTransfer";
import { warehouseApi } from "@/lib/api/warehouse";
import { companyApi } from "@/lib/api/company";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const PRODUCT_OPTIONS = ["FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER"] as const;

const createSchema = z.object({
  destination_company_id: z.string().uuid("Kompaniya tanlang"),
  source_warehouse_id: z.string().uuid("Ombor tanlang"),
  destination_warehouse_id: z.string().uuid("Ombor tanlang"),
  product_type: z.enum(PRODUCT_OPTIONS),
  transfer_date: z.string().min(1),
  unit_price: z.number().optional().nullable(),
  notes: z.string().optional().nullable(),
  lines: z.array(z.object({ quantity_kg: z.number().positive() })).min(1),
});
type CreateForm = z.infer<typeof createSchema>;

const STATUS_VARIANT: Record<IntercompanyTransferStatus, "success" | "warning" | "danger"> = {
  DRAFT: "warning", CONFIRMED: "success", CANCELLED: "danger",
};

export default function IntercompanyTransfersPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["intercompany-transfers", page],
    queryFn: () => intercompanyTransferApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: companiesPage } = useQuery({
    queryKey: ["companies-for-transfer"],
    queryFn: () => companyApi.list({ active_only: true, page_size: 200 }),
    enabled: showCreate,
  });
  const spinningCompanyOptions: SelectOption[] = (companiesPage?.items ?? [])
    .filter((c) => c.company_type === "YARN_SPINNING")
    .map((c) => ({ value: c.id, label: c.name }));

  const { data: sourceWarehousesPage } = useQuery({
    queryKey: ["warehouses-fg-source"],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "FINISHED_GOODS", page_size: 200 }),
    enabled: showCreate,
  });
  const sourceWarehouseOptions: SelectOption[] = (sourceWarehousesPage?.items ?? []).map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));

  const { register, handleSubmit, reset, control, watch, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { lines: [{ quantity_kg: 0 }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });
  const destCompanyId = watch("destination_company_id");

  const { data: destWarehousesPage } = useQuery({
    queryKey: ["warehouses-raw-cotton-dest", destCompanyId],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "RAW_COTTON", page_size: 200 }),
    enabled: !!destCompanyId,
  });
  const destWarehouseOptions: SelectOption[] = (destWarehousesPage?.items ?? []).map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));

  const createMut = useMutation({
    mutationFn: intercompanyTransferApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["intercompany-transfers"] });
      setShowCreate(false);
      reset({ lines: [{ quantity_kg: 0 }] });
      toast.success(t("O'tkazma yaratildi", "Перевод создан"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const confirmMut = useMutation({
    mutationFn: (id: string) => intercompanyTransferApi.confirm(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["intercompany-transfers"] }); toast.success(t("Tasdiqlandi", "Подтверждено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const cancelMut = useMutation({
    mutationFn: (id: string) => intercompanyTransferApi.cancel(id, t("Bekor qilindi", "Отменено пользователем")),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["intercompany-transfers"] }); toast.success(t("Bekor qilindi", "Отменено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<IntercompanyTransfer>[] = [
    { accessorKey: "transfer_number", header: "№", cell: ({ getValue }) => <span className="font-mono font-semibold">{getValue() as string}</span> },
    { accessorKey: "transfer_date", header: t("Sana", "Дата"), cell: ({ getValue }) => formatDate(getValue() as string, language) },
    { accessorKey: "destination_company_name", header: t("Qabul qiluvchi", "Получатель") },
    { accessorKey: "product_type", header: t("Mahsulot", "Продукт") },
    { accessorKey: "total_quantity_kg", header: t("Kg", "Кг"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as IntercompanyTransferStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s}</Badge>;
      },
    },
    {
      id: "actions",
      size: 90,
      cell: ({ row }) => row.original.status === "DRAFT" ? (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => confirmMut.mutate(row.original.id)} title={t("Tasdiqlash", "Подтвердить")}>
            <Check size={14} className="text-green-600" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => cancelMut.mutate(row.original.id)}>
            <X size={14} className="text-red-500" />
          </Button>
        </div>
      ) : row.original.status === "CONFIRMED" ? (
        <Button variant="ghost" size="icon" onClick={() => cancelMut.mutate(row.original.id)} title={t("Bekor qilish", "Отменить")}>
          <X size={14} className="text-red-500" />
        </Button>
      ) : null,
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Kompaniyalararo o'tkazmalar", "Межкорпоративные переводы")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi o'tkazma", "Новый перевод")}
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
        emptyText={t("O'tkazmalar topilmadi", "Переводы не найдены")}
      />

      <Modal open={showCreate} onOpenChange={(v) => { setShowCreate(v); if (!v) reset(); }} title={t("Yangi o'tkazma", "Новый перевод")} className="max-w-2xl">
        <form onSubmit={handleSubmit((d) => createMut.mutate(d))} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Controller
              control={control} name="destination_company_id"
              render={({ field }) => (
                <Select label={t("Qabul qiluvchi kompaniya", "Компания-получатель")} value={field.value} onValueChange={field.onChange}
                  options={spinningCompanyOptions} placeholder={t("Tanlang", "Выберите")} error={errors.destination_company_id?.message} />
              )}
            />
            <Input label={t("Sana", "Дата")} type="date" {...register("transfer_date")} error={errors.transfer_date?.message} />
            <Controller
              control={control} name="source_warehouse_id"
              render={({ field }) => (
                <Select label={t("Manba ombor (Fiber)", "Склад-источник (Fiber)")} value={field.value} onValueChange={field.onChange}
                  options={sourceWarehouseOptions} placeholder={t("Tanlang", "Выберите")} error={errors.source_warehouse_id?.message} />
              )}
            />
            <Controller
              control={control} name="destination_warehouse_id"
              render={({ field }) => (
                <Select label={t("Qabul ombor (Raw Cotton)", "Склад-получатель")} value={field.value} onValueChange={field.onChange}
                  options={destWarehouseOptions} placeholder={t("Tanlang", "Выберите")} disabled={!destCompanyId} error={errors.destination_warehouse_id?.message} />
              )}
            />
            <Controller
              control={control} name="product_type"
              render={({ field }) => (
                <Select label={t("Mahsulot turi", "Тип продукта")} value={field.value} onValueChange={field.onChange}
                  options={PRODUCT_OPTIONS.map((p) => ({ value: p, label: p }))} />
              )}
            />
            <Input label={t("Narx/kg (ixtiyoriy)", "Цена/кг (необяз.)")} type="number" step="0.01" {...register("unit_price", { valueAsNumber: true })} />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">{t("Miqdorlar", "Количества")}</span>
              <Button type="button" size="sm" variant="outline" onClick={() => append({ quantity_kg: 0 })}>
                <Plus size={12} /> {t("Qo'shish", "Добавить")}
              </Button>
            </div>
            {fields.map((field, idx) => (
              <div key={field.id} className="mb-2 flex items-center gap-2">
                <Input type="number" step="0.001" placeholder="Qty (kg)" {...register(`lines.${idx}.quantity_kg`, { valueAsNumber: true })} />
                {fields.length > 1 && (
                  <Button type="button" variant="ghost" size="icon" onClick={() => remove(idx)}><X size={14} /></Button>
                )}
              </div>
            ))}
          </div>

          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={createMut.isPending}>{t("Yaratish", "Создать")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

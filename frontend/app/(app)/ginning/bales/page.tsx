"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { ginningBaleApi, type GinningBale } from "@/lib/api/ginningBale";
import { ginningProductionApi } from "@/lib/api/ginningProduction";
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
  production_order_id: z.string().uuid("Buyurtma tanlang"),
  warehouse_id: z.string().uuid("Ombor tanlang"),
  gross_weight_kg: z.number().positive(),
  tare_weight_kg: z.number().min(0),
  grade: z.string().optional().nullable(),
  color: z.string().optional().nullable(),
  moisture_pct: z.number().optional().nullable(),
  micronaire: z.number().optional().nullable(),
  staple_length_mm: z.number().optional().nullable(),
  strength: z.number().optional().nullable(),
  trash_pct: z.number().optional().nullable(),
}).refine((d) => d.tare_weight_kg < d.gross_weight_kg, {
  message: "Tara brutto vazndan kichik bo'lishi kerak", path: ["tare_weight_kg"],
});
type CreateForm = z.infer<typeof createSchema>;

function BalesPageInner() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const prefillOrderId = searchParams.get("production_order_id") ?? undefined;

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(!!prefillOrderId);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["ginning-bales", page],
    queryFn: () => ginningBaleApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: ordersPage } = useQuery({
    queryKey: ["ginning-production-completed"],
    queryFn: () => ginningProductionApi.list({ status: "COMPLETED", page_size: 200 }),
    enabled: showCreate,
  });
  const orderOptions: SelectOption[] = (ordersPage?.items ?? []).map((o) => ({ value: o.id, label: o.production_number }));

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-finished-goods-bales"],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "FINISHED_GOODS", page_size: 200 }),
    enabled: showCreate,
  });
  const warehouseOptions: SelectOption[] = (warehousesPage?.items ?? []).map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));

  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { production_order_id: prefillOrderId, tare_weight_kg: 0 },
  });

  const createMut = useMutation({
    mutationFn: ginningBaleApi.create,
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["ginning-bales"] });
      reset({ production_order_id: prefillOrderId, tare_weight_kg: 0 });
      if (result.reconciliation_warning) {
        toast.warning(result.reconciliation_warning);
      } else {
        toast.success(t("Tuk yaratildi", "Кипа создана"));
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<GinningBale>[] = [
    { accessorKey: "bale_number", header: t("Tuk raqami", "Номер кипы"), cell: ({ getValue }) => <span className="font-mono font-semibold">{getValue() as string}</span> },
    { accessorKey: "production_number", header: t("Buyurtma", "Заказ") },
    { accessorKey: "production_date", header: t("Sana", "Дата"), cell: ({ getValue }) => formatDate(getValue() as string, language) },
    {
      accessorKey: "net_weight_kg",
      header: t("Sof kg", "Нетто кг"),
      cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    { accessorKey: "grade", header: t("Nav", "Сорт"), cell: ({ getValue }) => (getValue() as string | null) || "—" },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as string;
        return <Badge variant={s === "IN_STOCK" ? "success" : s === "SOLD" ? "info" : "default"}>{s}</Badge>;
      },
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Tuklar (Bales)", "Кипы")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi tuk", "Новая кипа")}
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
        emptyText={t("Tuklar topilmadi", "Кипы не найдены")}
      />

      <Modal open={showCreate} onOpenChange={(v) => { setShowCreate(v); if (!v) reset(); }} title={t("Yangi tuk", "Новая кипа")}>
        <form onSubmit={handleSubmit((d) => createMut.mutate(d))} className="flex flex-col gap-4">
          <Controller
            control={control} name="production_order_id"
            render={({ field }) => (
              <Select label={t("Ishlab chiqarish buyurtmasi", "Заказ на производство")} value={field.value} onValueChange={field.onChange}
                options={orderOptions} placeholder={t("Tanlang", "Выберите")} error={errors.production_order_id?.message} />
            )}
          />
          <Controller
            control={control} name="warehouse_id"
            render={({ field }) => (
              <Select label={t("Ombor", "Склад")} value={field.value} onValueChange={field.onChange}
                options={warehouseOptions} placeholder={t("Tanlang", "Выберите")} error={errors.warehouse_id?.message} />
            )}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input label={t("Brutto (kg)", "Брутто (кг)")} type="number" step="0.001" {...register("gross_weight_kg", { valueAsNumber: true })} error={errors.gross_weight_kg?.message} />
            <Input label={t("Tara (kg)", "Тара (кг)")} type="number" step="0.001" {...register("tare_weight_kg", { valueAsNumber: true })} error={errors.tare_weight_kg?.message} />
            <Input label={t("Nav", "Сорт")} {...register("grade")} />
            <Input label={t("Rang", "Цвет")} {...register("color")} />
            <Input label={t("Namlik %", "Влажность %")} type="number" step="0.01" {...register("moisture_pct", { valueAsNumber: true })} />
            <Input label="Micronaire" type="number" step="0.01" {...register("micronaire", { valueAsNumber: true })} />
            <Input label={t("Tola uzunligi (mm)", "Длина волокна (мм)")} type="number" step="0.01" {...register("staple_length_mm", { valueAsNumber: true })} />
            <Input label={t("Mustahkamlik", "Прочность")} type="number" step="0.01" {...register("strength", { valueAsNumber: true })} />
          </div>
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>{t("Yopish", "Закрыть")}</Button>
            <Button type="submit" loading={createMut.isPending}>{t("Yaratish", "Создать")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

export default function GinningBalesPage() {
  return (
    <Suspense fallback={null}>
      <BalesPageInner />
    </Suspense>
  );
}

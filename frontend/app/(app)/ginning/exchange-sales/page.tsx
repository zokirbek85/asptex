"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { exchangeSaleApi, type ExchangeSale, type ExchangeSaleStatus } from "@/lib/api/exchangeSale";
import { warehouseApi } from "@/lib/api/warehouse";
import { counterpartyApi } from "@/lib/api/counterparty";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const PRODUCT_OPTIONS = ["FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER"] as const;

const lineSchema = z.object({
  product_type: z.enum(PRODUCT_OPTIONS),
  quantity_kg: z.number().positive(),
  unit_price: z.number().positive(),
});

const createSchema = z.object({
  warehouse_id: z.string().uuid("Ombor tanlang"),
  sale_date: z.string().min(1),
  customer_id: z.string().uuid("Xaridor tanlang"),
  exchange_name: z.string().optional().nullable(),
  exchange_lot_number: z.string().optional().nullable(),
  commission_amount: z.number().optional().nullable(),
  broker_name: z.string().optional().nullable(),
  transport_cost: z.number().optional().nullable(),
  other_costs: z.number().optional().nullable(),
  notes: z.string().optional().nullable(),
  lines: z.array(lineSchema).min(1),
});
type CreateForm = z.infer<typeof createSchema>;

const STATUS_VARIANT: Record<ExchangeSaleStatus, "success" | "warning" | "danger"> = {
  ACTIVE: "success", PARTIALLY_CANCELLED: "warning", CANCELLED: "danger",
};

export default function ExchangeSalesPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["exchange-sales", page],
    queryFn: () => exchangeSaleApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-fg-exchange"],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "FINISHED_GOODS", page_size: 200 }),
    enabled: showCreate,
  });
  const warehouseOptions: SelectOption[] = (warehousesPage?.items ?? []).map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));

  const { data: customersPage } = useQuery({
    queryKey: ["counterparties-buyers-exchange"],
    queryFn: () => counterpartyApi.list({ active_only: true, counterparty_type: "BUYER", page_size: 200 }),
    enabled: showCreate,
  });
  const customerOptions: SelectOption[] = (customersPage?.items ?? []).map((c) => ({ value: c.id, label: c.name }));

  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { lines: [{ product_type: "FIBER", quantity_kg: 0, unit_price: 0 }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });

  const createMut = useMutation({
    mutationFn: exchangeSaleApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exchange-sales"] });
      setShowCreate(false);
      reset({ lines: [{ product_type: "FIBER", quantity_kg: 0, unit_price: 0 }] });
      toast.success(t("Savdo yaratildi", "Продажа создана"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<ExchangeSale>[] = [
    { accessorKey: "sale_number", header: "№", cell: ({ getValue }) => <span className="font-mono font-semibold">{getValue() as string}</span> },
    { accessorKey: "sale_date", header: t("Sana", "Дата"), cell: ({ getValue }) => formatDate(getValue() as string, language) },
    { accessorKey: "customer_name", header: t("Xaridor", "Покупатель") },
    { accessorKey: "total_kg", header: t("Jami kg", "Всего кг"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
    { accessorKey: "total_value", header: t("Summa", "Сумма"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ") },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as ExchangeSaleStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s}</Badge>;
      },
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Birja savdolari", "Биржевые продажи")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi savdo", "Новая продажа")}
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
        emptyText={t("Savdolar topilmadi", "Продажи не найдены")}
      />

      <Modal open={showCreate} onOpenChange={(v) => { setShowCreate(v); if (!v) reset(); }} title={t("Yangi birja savdosi", "Новая биржевая продажа")} className="max-w-2xl">
        <form onSubmit={handleSubmit((d) => createMut.mutate(d))} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Controller
              control={control} name="warehouse_id"
              render={({ field }) => (
                <Select label={t("Ombor", "Склад")} value={field.value} onValueChange={field.onChange}
                  options={warehouseOptions} placeholder={t("Tanlang", "Выберите")} error={errors.warehouse_id?.message} />
              )}
            />
            <Input label={t("Sana", "Дата")} type="date" {...register("sale_date")} error={errors.sale_date?.message} />
            <Controller
              control={control} name="customer_id"
              render={({ field }) => (
                <Select label={t("Xaridor", "Покупатель")} value={field.value} onValueChange={field.onChange}
                  options={customerOptions} placeholder={t("Tanlang", "Выберите")} error={errors.customer_id?.message} />
              )}
            />
            <Input label={t("Birja nomi", "Название биржи")} {...register("exchange_name")} />
            <Input label={t("Birja lot raqami", "Номер биржевого лота")} {...register("exchange_lot_number")} />
            <Input label={t("Broker", "Брокер")} {...register("broker_name")} />
            <Input label={t("Komissiya", "Комиссия")} type="number" step="0.01" {...register("commission_amount", { valueAsNumber: true })} />
            <Input label={t("Transport xarajati", "Транспортные расходы")} type="number" step="0.01" {...register("transport_cost", { valueAsNumber: true })} />
            <Input label={t("Boshqa xarajatlar", "Прочие расходы")} type="number" step="0.01" {...register("other_costs", { valueAsNumber: true })} />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">{t("Qatorlar", "Строки")}</span>
              <Button type="button" size="sm" variant="outline" onClick={() => append({ product_type: "FIBER", quantity_kg: 0, unit_price: 0 })}>
                <Plus size={12} /> {t("Qo'shish", "Добавить")}
              </Button>
            </div>
            {fields.map((field, idx) => (
              <div key={field.id} className="mb-2 grid grid-cols-[1fr_1fr_1fr_36px] gap-2 rounded-lg border border-slate-200 p-2">
                <Controller
                  control={control} name={`lines.${idx}.product_type`}
                  render={({ field: f }) => (
                    <Select label={t("Mahsulot", "Продукт")} value={f.value} onValueChange={f.onChange} options={PRODUCT_OPTIONS.map((p) => ({ value: p, label: p }))} />
                  )}
                />
                <Input label="Qty (kg)" type="number" step="0.001" {...register(`lines.${idx}.quantity_kg`, { valueAsNumber: true })} />
                <Input label={t("Narx/kg", "Цена/кг")} type="number" step="0.01" {...register(`lines.${idx}.unit_price`, { valueAsNumber: true })} />
                <div className="flex items-end">
                  {fields.length > 1 && <Button type="button" variant="ghost" size="icon" onClick={() => remove(idx)}><X size={14} /></Button>}
                </div>
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

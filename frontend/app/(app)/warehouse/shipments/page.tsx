"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Eye } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { shipmentApi, type ShipmentCreate, type ShipmentResponse } from "@/lib/api/shipment";
import { warehouseApi } from "@/lib/api/warehouse";
import { counterpartyApi } from "@/lib/api/counterparty";
import { contractApi } from "@/lib/api/contract";
import { stockApi } from "@/lib/api/stock";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";
import type { ShipmentStatus } from "@/lib/types";

const lineSchema = z.object({
  lot_id: z.string().uuid("Valid UUID required"),
  count_id: z.string().uuid("Valid UUID required"),
  owner_id: z.string().uuid("Valid UUID required"),
  quantity_kg: z.number().positive("Must be > 0"),
  quantity_bags: z.number().int().optional().nullable(),
  notes: z.string().optional().nullable(),
});

const createSchema = z.object({
  warehouse_id: z.string().uuid(),
  shipment_date: z.string().min(1),
  buyer_id: z.string().uuid(),
  contract_id: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
  lines: z.array(lineSchema).min(1, "At least one line required"),
});

type CreateForm = z.infer<typeof createSchema>;

const STATUS_VARIANT: Record<ShipmentStatus, "success" | "warning" | "danger" | "default"> = {
  ACTIVE: "success",
  PARTIALLY_CANCELLED: "warning",
  CANCELLED: "danger",
};

export default function ShipmentsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["shipments", page],
    queryFn: () => shipmentApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const form = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { lines: [{ lot_id: "", count_id: "", owner_id: "", quantity_kg: 0 }] },
  });
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "lines" });

  const warehouseId = form.watch("warehouse_id");
  const buyerId = form.watch("buyer_id");

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-fg"],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "FINISHED_GOODS", page_size: 200 }),
    enabled: showCreate,
  });
  const { data: buyersPage } = useQuery({
    queryKey: ["counterparties-all"],
    queryFn: () => counterpartyApi.list({ active_only: true, page_size: 200 }),
    enabled: showCreate,
  });
  const { data: contractsPage } = useQuery({
    queryKey: ["contracts-for-buyer", buyerId],
    queryFn: () => contractApi.list({ active_only: true, counterparty_id: buyerId, page_size: 200 }),
    enabled: showCreate && !!buyerId,
  });
  const { data: stockItems } = useQuery({
    queryKey: ["fg-stock-for-shipment", warehouseId],
    queryFn: () => stockApi.finishedGoods({ warehouse_id: warehouseId }),
    enabled: showCreate && !!warehouseId,
  });

  const warehouseOptions: SelectOption[] = (warehousesPage?.items ?? []).map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));
  const buyerOptions: SelectOption[] = (buyersPage?.items ?? []).map((c) => ({ value: c.id, label: c.name }));
  const contractOptions: SelectOption[] = [
    { value: "", label: t("Tanlanmagan", "Не выбран") },
    ...(contractsPage?.items ?? []).map((c) => ({ value: c.id, label: c.contract_number })),
  ];

  const lotOptions: SelectOption[] = useMemo(() => {
    const map = new Map<string, string>();
    (stockItems ?? []).forEach((i) => map.set(i.lot_id, i.lot_number));
    return Array.from(map, ([value, label]) => ({ value, label }));
  }, [stockItems]);

  const countOptionsForLot = (lotId: string): SelectOption[] => {
    const map = new Map<string, string>();
    (stockItems ?? []).forEach((i) => {
      if (i.lot_id === lotId && i.count_id && i.count_value) map.set(i.count_id, i.count_value);
    });
    return Array.from(map, ([value, label]) => ({ value, label }));
  };

  const ownerOptionsForLotCount = (lotId: string, countId: string): SelectOption[] => {
    const map = new Map<string, string>();
    (stockItems ?? []).forEach((i) => {
      if (i.lot_id === lotId && i.count_id === countId && i.owner_id && i.owner_name) map.set(i.owner_id, i.owner_name);
    });
    return Array.from(map, ([value, label]) => ({ value, label }));
  };

  const createMut = useMutation({
    mutationFn: (body: ShipmentCreate) => shipmentApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shipments"] });
      setShowCreate(false);
      form.reset();
      toast.success(t("Jo'natma yaratildi", "Отгрузка создана"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<ShipmentResponse>[] = [
    {
      accessorKey: "shipment_number",
      header: t("Raqam", "Номер"),
      cell: ({ row }) => (
        <Link href={`/warehouse/shipments/${row.original.id}`} className="font-mono font-semibold text-blue-600 hover:underline">
          {row.original.shipment_number}
        </Link>
      ),
    },
    {
      accessorKey: "shipment_date",
      header: t("Sana", "Дата"),
      cell: ({ getValue }) => formatDate(getValue() as string, language),
    },
    { accessorKey: "buyer_name", header: t("Xaridor", "Покупатель") },
    {
      accessorKey: "total_kg",
      header: t("Jami kg", "Всего кг"),
      cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    {
      accessorKey: "net_kg",
      header: t("Sof kg", "Нетто кг"),
      cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as ShipmentStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s}</Badge>;
      },
    },
    {
      id: "actions",
      size: 60,
      cell: ({ row }) => (
        <Button variant="ghost" size="icon" asChild>
          <Link href={`/warehouse/shipments/${row.original.id}`}><Eye size={14} /></Link>
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Jo'natmalar", "Отгрузки")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi jo'natma", "Новая отгрузка")}
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
        emptyText={t("Jo'natmalar topilmadi", "Отгрузки не найдены")}
      />

      {/* Create Modal */}
      <Modal
        open={showCreate}
        onOpenChange={(v) => { if (!v) { setShowCreate(false); form.reset(); } }}
        title={t("Yangi jo'natma", "Новая отгрузка")}
      >
        <form
          onSubmit={form.handleSubmit((d) => createMut.mutate(d as ShipmentCreate))}
          className="flex flex-col gap-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <Controller
              control={form.control}
              name="warehouse_id"
              render={({ field }) => (
                <Select
                  label={t("Ombor", "Склад")}
                  value={field.value}
                  onValueChange={(v) => {
                    field.onChange(v);
                    const lines = form.getValues("lines");
                    lines.forEach((_, idx) => {
                      form.setValue(`lines.${idx}.lot_id`, "");
                      form.setValue(`lines.${idx}.count_id`, "");
                      form.setValue(`lines.${idx}.owner_id`, "");
                    });
                  }}
                  options={warehouseOptions}
                  placeholder={t("Tanlang", "Выберите")}
                  error={form.formState.errors.warehouse_id?.message}
                />
              )}
            />
            <Input label={t("Sana", "Дата")} type="date" {...form.register("shipment_date")} error={form.formState.errors.shipment_date?.message} />
            <Controller
              control={form.control}
              name="buyer_id"
              render={({ field }) => (
                <Select
                  label={t("Xaridor", "Покупатель")}
                  value={field.value}
                  onValueChange={(v) => {
                    field.onChange(v);
                    form.setValue("contract_id", "");
                  }}
                  options={buyerOptions}
                  placeholder={t("Tanlang", "Выберите")}
                  error={form.formState.errors.buyer_id?.message}
                />
              )}
            />
            <Controller
              control={form.control}
              name="contract_id"
              render={({ field }) => (
                <Select
                  label={t("Shartnoma (ixtiyoriy)", "Договор (необяз.)")}
                  value={field.value ?? ""}
                  onValueChange={field.onChange}
                  options={contractOptions}
                  placeholder={t("Tanlang", "Выберите")}
                  disabled={!buyerId}
                />
              )}
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">{t("Qatorlar", "Строки")}</span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!warehouseId}
                onClick={() => append({ lot_id: "", count_id: "", owner_id: "", quantity_kg: 0 } as any)}
              >
                <Plus size={12} /> {t("Qo'shish", "Добавить")}
              </Button>
            </div>
            {!warehouseId && (
              <p className="mb-2 text-xs text-foreground-muted">{t("Avval omborni tanlang", "Сначала выберите склад")}</p>
            )}
            {fields.map((field, idx) => {
              const lotId = form.watch(`lines.${idx}.lot_id`);
              const countId = form.watch(`lines.${idx}.count_id`);
              return (
                <div key={field.id} className="mb-2 grid grid-cols-4 gap-2 rounded-lg border border-slate-200 p-2">
                  <Controller
                    control={form.control}
                    name={`lines.${idx}.lot_id`}
                    render={({ field: f }) => (
                      <Select
                        label="Lot"
                        value={f.value}
                        onValueChange={(v) => {
                          f.onChange(v);
                          form.setValue(`lines.${idx}.count_id`, "");
                          form.setValue(`lines.${idx}.owner_id`, "");
                        }}
                        options={lotOptions}
                        placeholder={t("Tanlang", "Выберите")}
                        disabled={!warehouseId}
                        error={form.formState.errors.lines?.[idx]?.lot_id?.message}
                      />
                    )}
                  />
                  <Controller
                    control={form.control}
                    name={`lines.${idx}.count_id`}
                    render={({ field: f }) => (
                      <Select
                        label="Count"
                        value={f.value}
                        onValueChange={(v) => {
                          f.onChange(v);
                          form.setValue(`lines.${idx}.owner_id`, "");
                        }}
                        options={countOptionsForLot(lotId)}
                        placeholder={t("Tanlang", "Выберите")}
                        disabled={!lotId}
                        error={form.formState.errors.lines?.[idx]?.count_id?.message}
                      />
                    )}
                  />
                  <Controller
                    control={form.control}
                    name={`lines.${idx}.owner_id`}
                    render={({ field: f }) => (
                      <Select
                        label={t("Egasi", "Владелец")}
                        value={f.value}
                        onValueChange={f.onChange}
                        options={ownerOptionsForLotCount(lotId, countId)}
                        placeholder={t("Tanlang", "Выберите")}
                        disabled={!countId}
                        error={form.formState.errors.lines?.[idx]?.owner_id?.message}
                      />
                    )}
                  />
                  <div className="flex items-end gap-1">
                    <Input label="Qty (kg)" type="number" step="0.001" {...form.register(`lines.${idx}.quantity_kg`, { valueAsNumber: true })} error={form.formState.errors.lines?.[idx]?.quantity_kg?.message} />
                    {fields.length > 1 && (
                      <Button type="button" variant="ghost" size="icon" onClick={() => remove(idx)}>
                        &times;
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
            {form.formState.errors.lines?.root && (
              <p className="text-xs text-red-500">{form.formState.errors.lines.root.message}</p>
            )}
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

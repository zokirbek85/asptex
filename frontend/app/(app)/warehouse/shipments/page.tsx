"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Eye } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { shipmentApi, type ShipmentCreate, type ShipmentResponse } from "@/lib/api/shipment";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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
            <Input label={t("Ombor ID", "ID склада")} {...form.register("warehouse_id")} error={form.formState.errors.warehouse_id?.message} />
            <Input label={t("Sana", "Дата")} type="date" {...form.register("shipment_date")} error={form.formState.errors.shipment_date?.message} />
            <Input label={t("Xaridor ID", "ID покупателя")} {...form.register("buyer_id")} error={form.formState.errors.buyer_id?.message} />
            <Input label={t("Shartnoma ID (ixtiyoriy)", "ID договора (необяз.)")} {...form.register("contract_id")} />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-semibold">{t("Qatorlar", "Строки")}</span>
              <Button type="button" size="sm" variant="outline" onClick={() => append({ lot_id: "", count_id: "", owner_id: "", quantity_kg: 0 } as any)}>
                <Plus size={12} /> {t("Qo'shish", "Добавить")}
              </Button>
            </div>
            {fields.map((field, idx) => (
              <div key={field.id} className="mb-2 grid grid-cols-4 gap-2 rounded-lg border border-slate-200 p-2">
                <Input label="Lot ID" {...form.register(`lines.${idx}.lot_id`)} error={form.formState.errors.lines?.[idx]?.lot_id?.message} />
                <Input label="Count ID" {...form.register(`lines.${idx}.count_id`)} error={form.formState.errors.lines?.[idx]?.count_id?.message} />
                <Input label="Owner ID" {...form.register(`lines.${idx}.owner_id`)} error={form.formState.errors.lines?.[idx]?.owner_id?.message} />
                <Input label="Qty (kg)" type="number" step="0.001" {...form.register(`lines.${idx}.quantity_kg`, { valueAsNumber: true })} error={form.formState.errors.lines?.[idx]?.quantity_kg?.message} />
              </div>
            ))}
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

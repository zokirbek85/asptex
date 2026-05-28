"use client";

import { use, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeft, XCircle } from "lucide-react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { shipmentApi, type ShipmentLineResponse, type ShipmentResponse } from "@/lib/api/shipment";
import { exportApi } from "@/lib/api/export";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";
import type { ShipmentStatus } from "@/lib/types";

const cancelSchema = z.object({
  quantity_kg: z.number().positive(),
  quantity_bags: z.number().int().optional().nullable(),
  reason: z.string().min(5, "Minimum 5 characters"),
});

type CancelForm = z.infer<typeof cancelSchema>;

const STATUS_VARIANT: Record<ShipmentStatus, "success" | "warning" | "danger" | "default"> = {
  ACTIVE: "success",
  PARTIALLY_CANCELLED: "warning",
  CANCELLED: "danger",
};

export default function ShipmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();
  const [cancelTarget, setCancelTarget] = useState<ShipmentLineResponse | null>(null);

  const { data: shipment, isLoading } = useQuery({
    queryKey: ["shipment", id],
    queryFn: () => shipmentApi.get(id),
  });

  const form = useForm<CancelForm>({ resolver: zodResolver(cancelSchema) });

  const cancelMut = useMutation({
    mutationFn: (data: CancelForm) =>
      shipmentApi.cancelLine(id, cancelTarget!.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shipment", id] });
      setCancelTarget(null);
      form.reset();
      toast.success(t("Bekor qilindi", "Отменено"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<ShipmentLineResponse>[] = [
    { accessorKey: "line_number", header: "#", size: 40 },
    { accessorKey: "lot_number", header: t("Lot", "Лот"), cell: ({ getValue }) => <span className="font-mono">{getValue() as string}</span> },
    { accessorKey: "count_value", header: t("Count", "Каунт") },
    { accessorKey: "owner_name", header: t("Egasi", "Владелец") },
    { accessorKey: "quantity_kg", header: t("Miqdor (kg)", "Кол-во"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
    { accessorKey: "net_kg", header: t("Sof (kg)", "Нетто"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }) },
    {
      accessorKey: "is_fully_cancelled",
      header: t("Holat", "Статус"),
      cell: ({ row }) => row.original.is_fully_cancelled ? (
        <Badge variant="danger">{t("Bekor", "Отменено")}</Badge>
      ) : row.original.cancelled_kg > 0 ? (
        <Badge variant="warning">{t("Qisman bekor", "Частично")}</Badge>
      ) : (
        <Badge variant="success">{t("Faol", "Активно")}</Badge>
      ),
    },
    {
      id: "actions",
      size: 60,
      cell: ({ row }) => !row.original.is_fully_cancelled ? (
        <Button
          variant="ghost" size="icon"
          title={t("Bekor qilish", "Отменить")}
          onClick={() => { setCancelTarget(row.original); form.reset(); }}
        >
          <XCircle size={14} className="text-red-500" />
        </Button>
      ) : null,
    },
  ];

  if (isLoading) {
    return <div className="p-8 text-center text-slate-400">{t("Yuklanmoqda...", "Загрузка...")}</div>;
  }

  if (!shipment) {
    return <div className="p-8 text-center text-slate-400">{t("Topilmadi", "Не найдено")}</div>;
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/warehouse/shipments"><ArrowLeft size={16} /></Link>
        </Button>
        <h1 className="text-xl font-bold text-gray-900 font-mono">{shipment.shipment_number}</h1>
        <Badge variant={STATUS_VARIANT[shipment.status]}>{shipment.status}</Badge>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 rounded-xl border border-slate-200 bg-white p-4 text-sm md:grid-cols-4">
        <div>
          <p className="text-xs text-slate-400">{t("Sana", "Дата")}</p>
          <p className="font-medium">{formatDate(shipment.shipment_date, language)}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">{t("Xaridor", "Покупатель")}</p>
          <p className="font-medium">{shipment.buyer_name}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">{t("Jami (kg)", "Итого (кг)")}</p>
          <p className="font-medium">{Number(shipment.total_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}</p>
        </div>
        <div>
          <p className="text-xs text-slate-400">{t("Sof (kg)", "Нетто (кг)")}</p>
          <p className="font-medium">{Number(shipment.net_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}</p>
        </div>
      </div>

      <div className="mb-3 flex justify-end">
        <Button variant="outline" size="sm" onClick={() => exportApi.dailyReport(shipment.id)}>
          {t("Excel yuklash", "Скачать Excel")}
        </Button>
      </div>

      <DataTable
        data={shipment.lines}
        columns={columns}
        isLoading={false}
        emptyText={t("Qatorlar yo'q", "Строк нет")}
      />

      {/* Cancel Modal */}
      <Modal
        open={!!cancelTarget}
        onOpenChange={(v) => { if (!v) { setCancelTarget(null); form.reset(); } }}
        title={cancelTarget ? `${t("Bekor qilish", "Отменить")}: ${cancelTarget.lot_number}` : ""}
      >
        <form onSubmit={form.handleSubmit((d) => cancelMut.mutate(d))} className="flex flex-col gap-4">
          <p className="text-sm text-slate-500">
            {t("Qolgan", "Остаток")}: <strong>{cancelTarget ? Number(cancelTarget.net_kg).toLocaleString() : 0} kg</strong>
          </p>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Qty (kg)"
              type="number"
              step="0.001"
              {...form.register("quantity_kg", { valueAsNumber: true })}
              error={form.formState.errors.quantity_kg?.message}
            />
            <Input
              label={t("Qoplar", "Мешки")}
              type="number"
              {...form.register("quantity_bags", { valueAsNumber: true })}
            />
          </div>
          <Input
            label={t("Sabab (min 5 belgi) *", "Причина (мин 5 симв.) *")}
            {...form.register("reason")}
            error={form.formState.errors.reason?.message}
          />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setCancelTarget(null)}>
              {t("Bekor", "Отмена")}
            </Button>
            <Button type="submit" variant="danger" loading={cancelMut.isPending}>
              {t("Bekor qilish", "Отменить")}
            </Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

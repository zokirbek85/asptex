"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Check, X } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { cottonReceivingApi, type CottonReceiving, type CottonReceivingCreate, type CottonReceivingStatus } from "@/lib/api/cottonReceiving";
import { ginningBuntApi } from "@/lib/api/ginningBunt";
import { counterpartyApi } from "@/lib/api/counterparty";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const createSchema = z.object({
  bunt_id: z.string().uuid("Bunt tanlang"),
  farmer_id: z.string().uuid("Fermer tanlang"),
  receiving_date: z.string().min(1),
  vehicle_number: z.string().optional().nullable(),
  driver_name: z.string().optional().nullable(),
  gross_weight_kg: z.number().positive("Brutto vazn > 0"),
  tare_weight_kg: z.number().min(0),
  moisture_pct: z.number().optional().nullable(),
  contamination_pct: z.number().optional().nullable(),
  grade: z.string().optional().nullable(),
  variety: z.string().optional().nullable(),
  sort: z.string().optional().nullable(),
  quality_class: z.string().optional().nullable(),
  unit_price: z.number().optional().nullable(),
  notes: z.string().optional().nullable(),
}).refine((d) => d.tare_weight_kg < d.gross_weight_kg, {
  message: "Tara brutto vazndan kichik bo'lishi kerak", path: ["tare_weight_kg"],
});
type CreateForm = z.infer<typeof createSchema>;

const STATUS_VARIANT: Record<CottonReceivingStatus, "success" | "warning" | "danger"> = {
  DRAFT: "warning", POSTED: "success", CANCELLED: "danger",
};

export default function CottonReceivingPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [showCreate, setShowCreate] = useState(false);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["cotton-receiving", page],
    queryFn: () => cottonReceivingApi.list({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: buntsPage } = useQuery({
    queryKey: ["ginning-bunts-open"],
    queryFn: () => ginningBuntApi.list({ status: "OPEN", page_size: 200 }),
    enabled: showCreate,
  });
  const buntOptions: SelectOption[] = (buntsPage?.items ?? []).map((b) => ({ value: b.id, label: b.lot_number }));

  const { data: farmersPage } = useQuery({
    queryKey: ["counterparties-farmers"],
    queryFn: () => counterpartyApi.list({ active_only: true, counterparty_type: "FARMER", page_size: 200 }),
    enabled: showCreate,
  });
  const farmerOptions: SelectOption[] = (farmersPage?.items ?? []).map((f) => ({ value: f.id, label: f.name }));

  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { tare_weight_kg: 0 },
  });

  const createMut = useMutation({
    mutationFn: cottonReceivingApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cotton-receiving"] });
      setShowCreate(false);
      reset();
      toast.success(t("Qabul yaratildi (qoralama)", "Приёмка создана (черновик)"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const postMut = useMutation({
    mutationFn: (id: string) => cottonReceivingApi.post(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cotton-receiving"] }); toast.success(t("Tasdiqlandi", "Проведено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const cancelMut = useMutation({
    mutationFn: (id: string) => cottonReceivingApi.cancel(id, t("Bekor qilindi", "Отменено пользователем")),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cotton-receiving"] }); toast.success(t("Bekor qilindi", "Отменено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const columns: ColumnDef<CottonReceiving>[] = [
    { accessorKey: "receiving_number", header: t("№", "№"), cell: ({ getValue }) => <span className="font-mono font-semibold">{getValue() as string}</span> },
    { accessorKey: "receiving_date", header: t("Sana", "Дата"), cell: ({ getValue }) => formatDate(getValue() as string, language) },
    { accessorKey: "bunt_lot_number", header: t("Bunt", "Бунт") },
    { accessorKey: "farmer_name", header: t("Fermer", "Фермер") },
    {
      accessorKey: "net_weight_kg",
      header: t("Sof kg", "Нетто кг"),
      cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ", { minimumFractionDigits: 3 }),
    },
    {
      accessorKey: "unit_price",
      header: t("Narx/kg", "Цена/кг"),
      cell: ({ getValue }) => {
        const v = getValue();
        return v !== null && v !== undefined ? Number(v).toLocaleString("uz-UZ") : "—";
      },
    },
    {
      accessorKey: "total_amount",
      header: t("Summa", "Сумма"),
      cell: ({ getValue }) => {
        const v = getValue();
        return v !== null && v !== undefined ? Number(v).toLocaleString("uz-UZ") : "—";
      },
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as CottonReceivingStatus;
        return <Badge variant={STATUS_VARIANT[s]}>{s}</Badge>;
      },
    },
    {
      id: "actions",
      size: 90,
      cell: ({ row }) => row.original.status === "DRAFT" ? (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => postMut.mutate(row.original.id)} title={t("Tasdiqlash", "Провести")}>
            <Check size={14} className="text-green-600" />
          </Button>
        </div>
      ) : row.original.status === "POSTED" ? (
        <Button variant="ghost" size="icon" onClick={() => cancelMut.mutate(row.original.id)} title={t("Bekor qilish", "Отменить")}>
          <X size={14} className="text-red-500" />
        </Button>
      ) : null,
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Paxta qabuli", "Приём хлопка")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("Yangi qabul", "Новая приёмка")}
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
        emptyText={t("Qabullar topilmadi", "Приёмки не найдены")}
      />

      <Modal
        open={showCreate}
        onOpenChange={(v) => { setShowCreate(v); if (!v) reset(); }}
        title={t("Yangi paxta qabuli", "Новая приёмка хлопка")}
        className="max-w-2xl"
      >
        <form onSubmit={handleSubmit((d) => createMut.mutate(d as CottonReceivingCreate))} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <Controller
              control={control} name="bunt_id"
              render={({ field }) => (
                <Select label={t("Bunt", "Бунт")} value={field.value} onValueChange={field.onChange}
                  options={buntOptions} placeholder={t("Tanlang", "Выберите")} error={errors.bunt_id?.message} />
              )}
            />
            <Controller
              control={control} name="farmer_id"
              render={({ field }) => (
                <Select label={t("Fermer", "Фермер")} value={field.value} onValueChange={field.onChange}
                  options={farmerOptions} placeholder={t("Tanlang", "Выберите")} error={errors.farmer_id?.message} />
              )}
            />
            <Input label={t("Sana", "Дата")} type="date" {...register("receiving_date")} error={errors.receiving_date?.message} />
            <Input label={t("Transport raqami", "Номер транспорта")} {...register("vehicle_number")} />
            <Input label={t("Haydovchi", "Водитель")} {...register("driver_name")} />
            <div />
            <Input label={t("Brutto vazn (kg)", "Вес брутто (кг)")} type="number" step="0.001" {...register("gross_weight_kg", { valueAsNumber: true })} error={errors.gross_weight_kg?.message} />
            <Input label={t("Tara (kg)", "Тара (кг)")} type="number" step="0.001" {...register("tare_weight_kg", { valueAsNumber: true })} error={errors.tare_weight_kg?.message} />
            <Input label={t("Namlik %", "Влажность %")} type="number" step="0.01" {...register("moisture_pct", { valueAsNumber: true })} />
            <Input label={t("Iflosligi %", "Загрязнённость %")} type="number" step="0.01" {...register("contamination_pct", { valueAsNumber: true })} />
            <Input label={t("Nav (grade)", "Сорт (grade)")} {...register("grade")} />
            <Input label={t("Xili (variety)", "Разновидность")} {...register("variety")} />
            <Input label={t("Sort", "Сортность")} {...register("sort")} />
            <Input label={t("Klass", "Класс")} {...register("quality_class")} />
            <Input
              label={t("Narx/kg (bo'sh qoldirilsa avtomatik hisoblanadi)", "Цена/кг (если пусто — рассчитается автоматически)")}
              type="number" step="0.01" {...register("unit_price", { valueAsNumber: true })}
            />
          </div>
          <Input label={t("Izoh", "Примечание")} {...register("notes")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={createMut.isPending}>{t("Yaratish", "Создать")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

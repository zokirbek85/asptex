"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Check, X } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { farmerSettlementApi, type FarmerBalance, type FarmerPayment } from "@/lib/api/farmerSettlement";
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
  farmer_id: z.string().uuid("Fermer tanlang"),
  payment_date: z.string().min(1),
  amount: z.number().positive(),
  payment_method: z.enum(["CASH", "BANK"]),
  reference_note: z.string().optional().nullable(),
});
type CreateForm = z.infer<typeof createSchema>;

export default function FarmerSettlementsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [showCreate, setShowCreate] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;

  const { data: balances, isLoading: balancesLoading } = useQuery({
    queryKey: ["farmer-balances"],
    queryFn: () => farmerSettlementApi.listBalances(),
  });

  const { data: payments } = useQuery({
    queryKey: ["farmer-payments", page],
    queryFn: () => farmerSettlementApi.listPayments({ page: page + 1, page_size: PAGE_SIZE }),
  });

  const { data: farmersPage } = useQuery({
    queryKey: ["counterparties-farmers-settlements"],
    queryFn: () => counterpartyApi.list({ active_only: true, counterparty_type: "FARMER", page_size: 200 }),
    enabled: showCreate,
  });
  const farmerOptions: SelectOption[] = (farmersPage?.items ?? []).map((f) => ({ value: f.id, label: f.name }));

  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { payment_method: "BANK" },
  });

  const createMut = useMutation({
    mutationFn: farmerSettlementApi.createPayment,
    onSuccess: (payment) => {
      qc.invalidateQueries({ queryKey: ["farmer-payments"] });
      toast.success(t("To'lov yaratildi (qoralama)", "Платёж создан (черновик)"));
      postMut.mutate(payment.id);
      setShowCreate(false);
      reset();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const postMut = useMutation({
    mutationFn: (id: string) => farmerSettlementApi.postPayment(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["farmer-payments"] });
      qc.invalidateQueries({ queryKey: ["farmer-balances"] });
      toast.success(t("To'lov provodka qilindi", "Платёж проведён"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const cancelMut = useMutation({
    mutationFn: (id: string) => farmerSettlementApi.cancelPayment(id, t("Bekor qilindi", "Отменено пользователем")),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["farmer-payments"] });
      qc.invalidateQueries({ queryKey: ["farmer-balances"] });
      toast.success(t("Bekor qilindi", "Отменено"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const balanceColumns: ColumnDef<FarmerBalance>[] = [
    { accessorKey: "farmer_name", header: t("Fermer", "Фермер") },
    {
      accessorKey: "balance",
      header: t("Qarzdorlik (kompaniyaga)", "Задолженность компании"),
      cell: ({ getValue }) => {
        const v = Number(getValue());
        return <span className={v > 0 ? "font-semibold text-danger" : "text-foreground-muted"}>{v.toLocaleString("uz-UZ")}</span>;
      },
    },
  ];

  const paymentColumns: ColumnDef<FarmerPayment>[] = [
    { accessorKey: "payment_number", header: "№", cell: ({ getValue }) => <span className="font-mono">{getValue() as string}</span> },
    { accessorKey: "payment_date", header: t("Sana", "Дата"), cell: ({ getValue }) => formatDate(getValue() as string, language) },
    { accessorKey: "farmer_name", header: t("Fermer", "Фермер") },
    { accessorKey: "amount", header: t("Summa", "Сумма"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ") },
    { accessorKey: "payment_method", header: t("Usul", "Способ") },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      cell: ({ getValue }) => {
        const s = getValue() as string;
        return <Badge variant={s === "POSTED" ? "success" : s === "CANCELLED" ? "danger" : "warning"}>{s}</Badge>;
      },
    },
    {
      id: "actions",
      size: 60,
      cell: ({ row }) => row.original.status === "POSTED" ? (
        <Button variant="ghost" size="icon" onClick={() => cancelMut.mutate(row.original.id)}><X size={14} className="text-red-500" /></Button>
      ) : null,
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Fermer hisob-kitobi", "Расчёты с фермерами")}</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> {t("To'lov qo'shish", "Добавить платёж")}
        </Button>
      </div>

      <div className="mb-8">
        <h2 className="mb-3 text-[14px] font-semibold">{t("Fermer balanslari", "Балансы фермеров")}</h2>
        <DataTable data={balances ?? []} columns={balanceColumns} isLoading={balancesLoading} emptyText={t("Fermerlar topilmadi", "Фермеры не найдены")} />
      </div>

      <div>
        <h2 className="mb-3 text-[14px] font-semibold">{t("To'lovlar tarixi", "История платежей")}</h2>
        <DataTable
          data={payments?.items ?? []}
          columns={paymentColumns}
          pageCount={payments?.pages}
          pagination={{ pageIndex: page, pageSize: PAGE_SIZE }}
          onPaginationChange={(updater) => {
            const next = typeof updater === "function" ? updater({ pageIndex: page, pageSize: PAGE_SIZE }) : updater;
            setPage(next.pageIndex);
          }}
          emptyText={t("To'lovlar topilmadi", "Платежи не найдены")}
        />
      </div>

      <Modal open={showCreate} onOpenChange={(v) => { setShowCreate(v); if (!v) reset(); }} title={t("Fermerga to'lov", "Платёж фермеру")}>
        <form onSubmit={handleSubmit((d) => createMut.mutate(d))} className="flex flex-col gap-4">
          <Controller
            control={control} name="farmer_id"
            render={({ field }) => (
              <Select label={t("Fermer", "Фермер")} value={field.value} onValueChange={field.onChange}
                options={farmerOptions} placeholder={t("Tanlang", "Выберите")} error={errors.farmer_id?.message} />
            )}
          />
          <Input label={t("Sana", "Дата")} type="date" {...register("payment_date")} error={errors.payment_date?.message} />
          <Input label={t("Summa", "Сумма")} type="number" step="0.01" {...register("amount", { valueAsNumber: true })} error={errors.amount?.message} />
          <Controller
            control={control} name="payment_method"
            render={({ field }) => (
              <Select label={t("To'lov usuli", "Способ оплаты")} value={field.value} onValueChange={field.onChange}
                options={[{ value: "CASH", label: t("Naqd", "Наличные") }, { value: "BANK", label: t("Bank", "Банк") }]} />
            )}
          />
          <Input label={t("Izoh", "Примечание")} {...register("reference_note")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={createMut.isPending}>{t("To'lash", "Оплатить")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

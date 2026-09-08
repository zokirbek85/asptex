"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { ginningCostingApi, type CostAllocationMethod, type GinningCostType, type ProductProfitability } from "@/lib/api/ginningCosting";
import { ginningProductionApi } from "@/lib/api/ginningProduction";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";

const COST_TYPES: GinningCostType[] = ["ELECTRICITY", "GAS", "LABOR", "DEPRECIATION", "MAINTENANCE", "PACKAGING", "OVERHEAD", "OTHER"];
const METHODS: CostAllocationMethod[] = ["QUANTITY", "SALES_VALUE"];

const costSchema = z.object({
  cost_type: z.enum(["ELECTRICITY", "GAS", "LABOR", "DEPRECIATION", "MAINTENANCE", "PACKAGING", "OVERHEAD", "OTHER"]),
  amount: z.number().positive(),
  notes: z.string().optional().nullable(),
});
type CostForm = z.infer<typeof costSchema>;

export default function GinningCostingPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const [orderId, setOrderId] = useState<string>("");
  const [method, setMethod] = useState<CostAllocationMethod>("QUANTITY");
  const [showAddCost, setShowAddCost] = useState(false);

  const { data: ordersPage } = useQuery({
    queryKey: ["ginning-production-completed-costing"],
    queryFn: () => ginningProductionApi.list({ status: "COMPLETED", page_size: 200 }),
  });
  const orderOptions: SelectOption[] = (ordersPage?.items ?? []).map((o) => ({ value: o.id, label: o.production_number }));

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["ginning-cost-summary", orderId, method],
    queryFn: () => ginningCostingApi.getSummary(orderId, method),
    enabled: !!orderId,
  });

  const { data: profitability } = useQuery({
    queryKey: ["ginning-profitability"],
    queryFn: () => ginningCostingApi.getProfitability(),
  });

  const { register, handleSubmit, reset, control, formState: { errors } } = useForm<CostForm>({
    resolver: zodResolver(costSchema),
  });

  const addCostMut = useMutation({
    mutationFn: (data: CostForm) => ginningCostingApi.addCost(orderId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ginning-cost-summary", orderId] });
      setShowAddCost(false);
      reset();
      toast.success(t("Xarajat qo'shildi", "Расход добавлен"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const profitColumns: ColumnDef<ProductProfitability>[] = [
    { accessorKey: "product_type", header: t("Mahsulot", "Продукт") },
    { accessorKey: "total_sales_value", header: t("Savdo summasi", "Сумма продаж"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ") },
    { accessorKey: "total_allocated_cost", header: t("Taqsimlangan tannarx", "Распределённая себестоимость"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ") },
    { accessorKey: "total_allocated_sales_expenses", header: t("Savdo xarajatlari", "Расходы на продажу"), cell: ({ getValue }) => Number(getValue()).toLocaleString("uz-UZ") },
    {
      accessorKey: "profit",
      header: t("Foyda", "Прибыль"),
      cell: ({ getValue }) => {
        const v = Number(getValue());
        return <span className={v >= 0 ? "font-semibold text-success" : "font-semibold text-danger"}>{v.toLocaleString("uz-UZ")}</span>;
      },
    },
  ];

  return (
    <div>
      <h1 className="mb-6 text-xl font-bold text-gray-900">{t("Tannarx va foydalilik", "Себестоимость и рентабельность")}</h1>

      <div className="mb-8 glass-card rounded-xl p-4">
        <div className="mb-4 grid grid-cols-2 gap-3">
          <Select
            label={t("Ishlab chiqarish buyurtmasi", "Заказ на производство")}
            value={orderId} onValueChange={setOrderId} options={orderOptions} placeholder={t("Tanlang", "Выберите")}
          />
          <Select
            label={t("Taqsimlash usuli", "Метод распределения")}
            value={method} onValueChange={(v) => setMethod(v as CostAllocationMethod)}
            options={METHODS.map((m) => ({ value: m, label: m }))}
          />
        </div>

        {summaryLoading && <p className="text-sm text-foreground-muted">{t("Yuklanmoqda...", "Загрузка...")}</p>}

        {summary && (
          <>
            <div className="mb-4 grid grid-cols-3 gap-3">
              <div className="rounded-lg border border-border p-3">
                <p className="text-[11px] text-foreground-muted">{t("Xom ashyo tannarxi", "Стоимость сырья")}</p>
                <p className="text-[16px] font-bold">{Number(summary.raw_material_cost).toLocaleString("uz-UZ")}</p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-[11px] text-foreground-muted">{t("Boshqa xarajatlar", "Прочие расходы")}</p>
                <p className="text-[16px] font-bold">{Number(summary.other_costs_total).toLocaleString("uz-UZ")}</p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-[11px] text-foreground-muted">{t("Jami tannarx", "Итого себестоимость")}</p>
                <p className="text-[16px] font-bold">{Number(summary.total_cost).toLocaleString("uz-UZ")}</p>
              </div>
            </div>

            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-semibold">{t("Qo'shimcha xarajatlar", "Дополнительные расходы")}</span>
              <Button type="button" size="sm" variant="outline" onClick={() => setShowAddCost(true)}>
                <Plus size={12} /> {t("Xarajat qo'shish", "Добавить расход")}
              </Button>
            </div>

            <div className="mb-4 overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-[13px]">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Mahsulot", "Продукт")}</th>
                    <th className="px-3 py-2 text-right font-medium text-foreground-muted">Kg</th>
                    <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Taqsimlangan tannarx", "Распред. себестоимость")}</th>
                    <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Tannarx/kg", "Себест./кг")}</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.allocations.map((a) => (
                    <tr key={a.output_id} className="border-t border-border">
                      <td className="px-3 py-2">{a.product_type}</td>
                      <td className="px-3 py-2 text-right font-mono">{Number(a.quantity_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}</td>
                      <td className="px-3 py-2 text-right font-mono">{Number(a.allocated_cost).toLocaleString("uz-UZ")}</td>
                      <td className="px-3 py-2 text-right font-mono">{Number(a.cost_per_kg).toLocaleString("uz-UZ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div>
        <h2 className="mb-3 text-[14px] font-semibold">{t("Mahsulot bo'yicha foydalilik", "Рентабельность по продуктам")}</h2>
        <DataTable data={profitability ?? []} columns={profitColumns} emptyText={t("Ma'lumot yo'q", "Нет данных")} />
      </div>

      <Modal open={showAddCost} onOpenChange={(v) => { setShowAddCost(v); if (!v) reset(); }} title={t("Xarajat qo'shish", "Добавить расход")}>
        <form onSubmit={handleSubmit((d) => addCostMut.mutate(d))} className="flex flex-col gap-4">
          <Controller
            control={control} name="cost_type"
            render={({ field }) => (
              <Select label={t("Xarajat turi", "Тип расхода")} value={field.value} onValueChange={field.onChange}
                options={COST_TYPES.map((c) => ({ value: c, label: c }))} error={errors.cost_type?.message} />
            )}
          />
          <Input label={t("Summa", "Сумма")} type="number" step="0.01" {...register("amount", { valueAsNumber: true })} error={errors.amount?.message} />
          <Input label={t("Izoh", "Примечание")} {...register("notes")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setShowAddCost(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={addCostMut.isPending}>{t("Qo'shish", "Добавить")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

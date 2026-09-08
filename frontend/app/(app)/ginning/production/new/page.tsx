"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Plus, Trash2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";

import { ginningProductionApi, type GinningProductionInputCreate, type GinningProductionOutputCreate, type GinningProductType } from "@/lib/api/ginningProduction";
import { ginningBuntApi } from "@/lib/api/ginningBunt";
import { warehouseApi } from "@/lib/api/warehouse";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, type SelectOption } from "@/components/ui/Select";
import Link from "next/link";

const PRODUCT_TYPES: GinningProductType[] = ["FIBER", "SEED", "LINT", "PUX", "ULYUK", "OTHER"];
const PRODUCT_LABELS: Record<GinningProductType, { uz: string; ru: string }> = {
  FIBER: { uz: "Tola (Fiber)", ru: "Волокно" },
  SEED: { uz: "Chigit (Seed)", ru: "Семена" },
  LINT: { uz: "Lint", ru: "Линт" },
  PUX: { uz: "Pux", ru: "Пух" },
  ULYUK: { uz: "Ulyuk", ru: "Улюк" },
  OTHER: { uz: "Boshqa", ru: "Другое" },
};

interface InputRow { bunt_id: string; quantity_kg: string; }
interface OutputRow { product_type: GinningProductType; warehouse_id: string; quantity_kg: string; }

export default function NewGinningProductionOrderPage() {
  const router = useRouter();
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);

  const [productionDate, setProductionDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [inputs, setInputs] = useState<InputRow[]>([{ bunt_id: "", quantity_kg: "" }]);
  const [outputs, setOutputs] = useState<OutputRow[]>([{ product_type: "FIBER", warehouse_id: "", quantity_kg: "" }]);

  const { data: buntsPage } = useQuery({
    queryKey: ["ginning-bunts-open-for-production"],
    queryFn: () => ginningBuntApi.list({ status: "OPEN", page_size: 200 }),
  });
  const buntOptions: SelectOption[] = (buntsPage?.items ?? []).map((b) => ({ value: b.id, label: b.lot_number }));

  const { data: warehousesPage } = useQuery({
    queryKey: ["warehouses-finished-goods-ginning"],
    queryFn: () => warehouseApi.list({ active_only: true, warehouse_type: "FINISHED_GOODS", page_size: 200 }),
  });
  const warehouseOptions: SelectOption[] = (warehousesPage?.items ?? []).map((w) => ({ value: w.id, label: `${w.name} (${w.code})` }));

  const totalInput = inputs.reduce((sum, i) => sum + (Number(i.quantity_kg) || 0), 0);
  const totalOutput = outputs.reduce((sum, o) => sum + (Number(o.quantity_kg) || 0), 0);
  const yieldPct = totalInput > 0 ? (totalOutput / totalInput) * 100 : 0;
  const lossPct = totalInput > 0 ? 100 - yieldPct : 0;

  const createMut = useMutation({
    mutationFn: () =>
      ginningProductionApi.create({
        production_date: productionDate,
        notes: notes || null,
        inputs: inputs
          .filter((i) => i.bunt_id && i.quantity_kg)
          .map((i): GinningProductionInputCreate => ({ bunt_id: i.bunt_id, quantity_kg: Number(i.quantity_kg) })),
        outputs: outputs
          .filter((o) => o.warehouse_id && o.quantity_kg)
          .map((o): GinningProductionOutputCreate => ({ product_type: o.product_type, warehouse_id: o.warehouse_id, quantity_kg: Number(o.quantity_kg) })),
      }),
    onSuccess: (order) => {
      toast.success(t("Buyurtma yaratildi (qoralama)", "Заказ создан (черновик)"));
      router.push(`/ginning/production/${order.id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="max-w-4xl">
      <Link href="/ginning/production" className="mb-4 inline-flex items-center gap-1 text-[13px] text-foreground-muted hover:text-foreground">
        <ArrowLeft size={14} /> {t("Buyurtmalar ro'yxati", "Список заказов")}
      </Link>

      <h1 className="mb-6 text-xl font-bold text-gray-900">{t("Yangi ishlab chiqarish buyurtmasi", "Новый заказ на производство")}</h1>

      <div className="mb-6 grid grid-cols-2 gap-3">
        <Input label={t("Sana", "Дата")} type="date" value={productionDate} onChange={(e) => setProductionDate(e.target.value)} />
        <Input label={t("Izoh", "Примечание")} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>

      {/* Inputs */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-semibold">{t("Kirish (Buntlar)", "Вход (Бунты)")}</span>
          <Button type="button" size="sm" variant="outline" onClick={() => setInputs([...inputs, { bunt_id: "", quantity_kg: "" }])}>
            <Plus size={12} /> {t("Qo'shish", "Добавить")}
          </Button>
        </div>
        {inputs.map((row, idx) => (
          <div key={idx} className="mb-2 grid grid-cols-[1fr_180px_36px] gap-2 rounded-lg border border-slate-200 p-2">
            <Select
              label="Bunt" value={row.bunt_id}
              onValueChange={(v) => setInputs(inputs.map((r, i) => (i === idx ? { ...r, bunt_id: v } : r)))}
              options={buntOptions} placeholder={t("Tanlang", "Выберите")}
            />
            <Input
              label="Qty (kg)" type="number" step="0.001" value={row.quantity_kg}
              onChange={(e) => setInputs(inputs.map((r, i) => (i === idx ? { ...r, quantity_kg: e.target.value } : r)))}
            />
            <div className="flex items-end">
              {inputs.length > 1 && (
                <Button type="button" variant="ghost" size="icon" onClick={() => setInputs(inputs.filter((_, i) => i !== idx))}>
                  <Trash2 size={14} className="text-red-500" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Outputs */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-semibold">{t("Chiqish (Mahsulotlar)", "Выход (Продукты)")}</span>
          <Button type="button" size="sm" variant="outline" onClick={() => setOutputs([...outputs, { product_type: "SEED", warehouse_id: "", quantity_kg: "" }])}>
            <Plus size={12} /> {t("Qo'shish", "Добавить")}
          </Button>
        </div>
        {outputs.map((row, idx) => (
          <div key={idx} className="mb-2 grid grid-cols-[1fr_1fr_160px_36px] gap-2 rounded-lg border border-slate-200 p-2">
            <Select
              label={t("Mahsulot", "Продукт")} value={row.product_type}
              onValueChange={(v) => setOutputs(outputs.map((r, i) => (i === idx ? { ...r, product_type: v as GinningProductType } : r)))}
              options={PRODUCT_TYPES.map((p) => ({ value: p, label: t(PRODUCT_LABELS[p].uz, PRODUCT_LABELS[p].ru) }))}
            />
            <Select
              label={t("Ombor", "Склад")} value={row.warehouse_id}
              onValueChange={(v) => setOutputs(outputs.map((r, i) => (i === idx ? { ...r, warehouse_id: v } : r)))}
              options={warehouseOptions} placeholder={t("Tanlang", "Выберите")}
            />
            <Input
              label="Qty (kg)" type="number" step="0.001" value={row.quantity_kg}
              onChange={(e) => setOutputs(outputs.map((r, i) => (i === idx ? { ...r, quantity_kg: e.target.value } : r)))}
            />
            <div className="flex items-end">
              {outputs.length > 1 && (
                <Button type="button" variant="ghost" size="icon" onClick={() => setOutputs(outputs.filter((_, i) => i !== idx))}>
                  <Trash2 size={14} className="text-red-500" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Live summary */}
      <div className="mb-6 grid grid-cols-4 gap-3">
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Jami kirish", "Всего вход")}</p>
          <p className="text-[18px] font-bold">{totalInput.toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg</p>
        </div>
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Jami chiqish", "Всего выход")}</p>
          <p className="text-[18px] font-bold">{totalOutput.toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg</p>
        </div>
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Unum", "Выход")}</p>
          <p className="text-[18px] font-bold text-success">{yieldPct.toFixed(2)}%</p>
        </div>
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Yo'qotish", "Потери")}</p>
          <p className="text-[18px] font-bold text-danger">{lossPct.toFixed(2)}%</p>
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => router.push("/ginning/production")}>{t("Bekor", "Отмена")}</Button>
        <Button loading={createMut.isPending} onClick={() => createMut.mutate()}>
          {t("Qoralama sifatida saqlash", "Сохранить как черновик")}
        </Button>
      </div>
    </div>
  );
}

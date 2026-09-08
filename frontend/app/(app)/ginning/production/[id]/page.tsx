"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Check, X } from "lucide-react";
import { toast } from "sonner";

import { ginningProductionApi } from "@/lib/api/ginningProduction";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";

export default function GinningProductionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const { data: order, isLoading } = useQuery({
    queryKey: ["ginning-production-order", id],
    queryFn: () => ginningProductionApi.get(id),
  });

  const completeMut = useMutation({
    mutationFn: () => ginningProductionApi.complete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ginning-production-order", id] });
      toast.success(t("Buyurtma yakunlandi va ombor postlandi", "Заказ завершён, склад проведён"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const cancelMut = useMutation({
    mutationFn: () => ginningProductionApi.cancel(id, t("Bekor qilindi", "Отменено пользователем")),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ginning-production-order", id] });
      toast.success(t("Bekor qilindi", "Отменено"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading || !order) {
    return <div className="text-sm text-foreground-muted">{t("Yuklanmoqda...", "Загрузка...")}</div>;
  }

  return (
    <div className="max-w-4xl">
      <Link href="/ginning/production" className="mb-4 inline-flex items-center gap-1 text-[13px] text-foreground-muted hover:text-foreground">
        <ArrowLeft size={14} /> {t("Buyurtmalar ro'yxati", "Список заказов")}
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{order.production_number}</h1>
          <p className="text-[13px] text-foreground-muted">{formatDate(order.production_date, language)}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={order.status === "COMPLETED" ? "success" : order.status === "CANCELLED" ? "danger" : "warning"}>
            {order.status}
          </Badge>
          {order.status === "DRAFT" && (
            <Button size="sm" onClick={() => completeMut.mutate()} loading={completeMut.isPending}>
              <Check size={14} /> {t("Yakunlash", "Завершить")}
            </Button>
          )}
          {order.status !== "CANCELLED" && (
            <Button size="sm" variant="danger" onClick={() => cancelMut.mutate()} loading={cancelMut.isPending}>
              <X size={14} /> {t("Bekor qilish", "Отменить")}
            </Button>
          )}
          {order.status === "COMPLETED" && (
            <Button size="sm" variant="outline" onClick={() => router.push(`/ginning/bales?production_order_id=${order.id}`)}>
              {t("Tuk (bale) qo'shish", "Добавить кипу")}
            </Button>
          )}
        </div>
      </div>

      <div className="mb-6 grid grid-cols-4 gap-3">
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Jami kirish", "Всего вход")}</p>
          <p className="text-[18px] font-bold">{Number(order.total_input_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg</p>
        </div>
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Jami chiqish", "Всего выход")}</p>
          <p className="text-[18px] font-bold">{Number(order.total_output_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg</p>
        </div>
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Unum", "Выход")}</p>
          <p className="text-[18px] font-bold text-success">{Number(order.yield_pct).toFixed(2)}%</p>
        </div>
        <div className="glass-card rounded-xl p-3">
          <p className="text-[11px] text-foreground-muted">{t("Yo'qotish", "Потери")}</p>
          <p className="text-[18px] font-bold text-danger">{Number(order.loss_pct).toFixed(2)}%</p>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="mb-2 text-[14px] font-semibold">{t("Kirish (Buntlar)", "Вход (Бунты)")}</h2>
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-[13px]">
            <thead className="bg-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">Bunt</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">Kg</th>
              </tr>
            </thead>
            <tbody>
              {order.inputs.map((i) => (
                <tr key={i.id} className="border-t border-border">
                  <td className="px-3 py-2 font-mono">{i.bunt_lot_number}</td>
                  <td className="px-3 py-2 text-right font-mono">{Number(i.quantity_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-[14px] font-semibold">{t("Chiqish (Mahsulotlar)", "Выход (Продукты)")}</h2>
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-[13px]">
            <thead className="bg-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Mahsulot", "Продукт")}</th>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Ombor", "Склад")}</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">Kg</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Unum %", "Выход %")}</th>
              </tr>
            </thead>
            <tbody>
              {order.outputs.map((o) => (
                <tr key={o.id} className="border-t border-border">
                  <td className="px-3 py-2">{o.product_type}</td>
                  <td className="px-3 py-2">{o.warehouse_name}</td>
                  <td className="px-3 py-2 text-right font-mono">{Number(o.quantity_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}</td>
                  <td className="px-3 py-2 text-right">{o.yield_pct !== null ? `${Number(o.yield_pct).toFixed(2)}%` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

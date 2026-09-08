"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { ginningBuntApi } from "@/lib/api/ginningBunt";
import { cottonReceivingApi } from "@/lib/api/cottonReceiving";
import { useAuthStore } from "@/lib/stores/auth";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";

export default function GinningBuntDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);

  const { data: bunt, isLoading } = useQuery({
    queryKey: ["ginning-bunt", id],
    queryFn: () => ginningBuntApi.get(id),
  });

  const { data: receivings } = useQuery({
    queryKey: ["cotton-receivings-for-bunt", id],
    queryFn: () => cottonReceivingApi.list({ bunt_id: id, page_size: 200 }),
  });

  if (isLoading || !bunt) {
    return <div className="text-sm text-foreground-muted">{t("Yuklanmoqda...", "Загрузка...")}</div>;
  }

  return (
    <div>
      <Link href="/ginning/bunts" className="mb-4 inline-flex items-center gap-1 text-[13px] text-foreground-muted hover:text-foreground">
        <ArrowLeft size={14} /> {t("Buntlar ro'yxati", "Список бунтов")}
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{bunt.lot_number}</h1>
          <p className="text-[13px] text-foreground-muted">{formatDate(bunt.opened_at, language)}</p>
        </div>
        <Badge variant={bunt.status === "OPEN" ? "success" : "default"}>
          {bunt.status === "OPEN" ? t("Ochiq", "Открыт") : t("Yopiq", "Закрыт")}
        </Badge>
      </div>

      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-4">
          <p className="text-[12px] text-foreground-muted">{t("Qoldiq", "Остаток")}</p>
          <p className="text-[22px] font-bold text-foreground">
            {Number(bunt.balance_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })} kg
          </p>
        </div>
        <div className="glass-card rounded-xl p-4">
          <p className="text-[12px] text-foreground-muted">{t("Fermerlar soni", "Число фермеров")}</p>
          <p className="text-[22px] font-bold text-foreground">{bunt.composition.length}</p>
        </div>
        <div className="glass-card rounded-xl p-4">
          <p className="text-[12px] text-foreground-muted">{t("Qabullar soni", "Число приёмок")}</p>
          <p className="text-[22px] font-bold text-foreground">{receivings?.total ?? 0}</p>
        </div>
      </div>

      <div className="mb-6">
        <h2 className="mb-3 text-[14px] font-semibold text-foreground">{t("Fermerlar tarkibi", "Состав по фермерам")}</h2>
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-[13px]">
            <thead className="bg-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Fermer", "Фермер")}</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Jami kg", "Всего кг")}</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Qabullar", "Приёмок")}</th>
              </tr>
            </thead>
            <tbody>
              {bunt.composition.map((c) => (
                <tr key={c.farmer_id} className="border-t border-border">
                  <td className="px-3 py-2 text-foreground">{c.farmer_name}</td>
                  <td className="px-3 py-2 text-right font-mono text-foreground">
                    {Number(c.total_net_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}
                  </td>
                  <td className="px-3 py-2 text-right text-foreground-muted">{c.receiving_count}</td>
                </tr>
              ))}
              {bunt.composition.length === 0 && (
                <tr><td colSpan={3} className="px-3 py-6 text-center text-foreground-muted">{t("Hali qabul yo'q", "Пока нет приёмок")}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-[14px] font-semibold text-foreground">{t("Qabul hujjatlari", "Документы приёмки")}</h2>
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-[13px]">
            <thead className="bg-muted">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">№</th>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Sana", "Дата")}</th>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Fermer", "Фермер")}</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Sof kg", "Нетто кг")}</th>
                <th className="px-3 py-2 text-right font-medium text-foreground-muted">{t("Narx/kg", "Цена/кг")}</th>
                <th className="px-3 py-2 text-left font-medium text-foreground-muted">{t("Holat", "Статус")}</th>
              </tr>
            </thead>
            <tbody>
              {(receivings?.items ?? []).map((r) => (
                <tr key={r.id} className="border-t border-border">
                  <td className="px-3 py-2 font-mono text-foreground">{r.receiving_number}</td>
                  <td className="px-3 py-2 text-foreground">{formatDate(r.receiving_date, language)}</td>
                  <td className="px-3 py-2 text-foreground">{r.farmer_name}</td>
                  <td className="px-3 py-2 text-right font-mono text-foreground">
                    {Number(r.net_weight_kg).toLocaleString("uz-UZ", { minimumFractionDigits: 3 })}
                  </td>
                  <td className="px-3 py-2 text-right text-foreground">{r.unit_price ?? "—"}</td>
                  <td className="px-3 py-2">
                    <Badge variant={r.status === "POSTED" ? "success" : r.status === "CANCELLED" ? "danger" : "default"}>
                      {r.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

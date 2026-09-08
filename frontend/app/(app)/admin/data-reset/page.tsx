"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { dataResetApi } from "@/lib/api/dataReset";
import { ApiException } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

interface ModuleDef {
  key: string;
  label: { uz: string; ru: string };
  hint: { uz: string; ru: string };
}

const MODULES: ModuleDef[] = [
  {
    key: "tolling",
    label: { uz: "Tolling", ru: "Толлинг" },
    hint: { uz: "Tolling lotlari, ishtirokchilar, kunlik taqsimotlar", ru: "Толлинговые лоты, участники, суточные распределения" },
  },
  {
    key: "shipments",
    label: { uz: "Jo'natmalar", ru: "Отгрузки" },
    hint: { uz: "Barcha jo'natmalar va ularning qatorlari", ru: "Все отгрузки и их строки" },
  },
  {
    key: "adjustments",
    label: { uz: "Korrekturalar", ru: "Корректировки" },
    hint: { uz: "Ombor korrektura hujjatlari", ru: "Документы корректировки склада" },
  },
  {
    key: "opening_balance",
    label: { uz: "Boshlang'ich qoldiq", ru: "Начальный остаток" },
    hint: { uz: "Boshlang'ich qoldiq hujjatlari", ru: "Документы начального остатка" },
  },
  {
    key: "daily_reports",
    label: { uz: "Kunlik hisobotlar", ru: "Суточные отчёты" },
    hint: { uz: "Kunlik hisobotlar. Tanlansa, Jo'natmalar ham birga tozalanadi", ru: "Суточные отчёты. Также очистит Отгрузки" },
  },
  {
    key: "stock_transactions",
    label: { uz: "Ombor tranzaksiyalari", ru: "Складские транзакции" },
    hint: { uz: "Barcha ombor harakati yozuvlari (ledger)", ru: "Все записи движения склада (леджер)" },
  },
  {
    key: "lots",
    label: { uz: "Lotlar", ru: "Лоты" },
    hint: {
      uz: "Lotlarning o'zi. Tanlansa, yuqoridagi barcha modullar ham birga tozalanadi",
      ru: "Сами лоты. Также очистит все модули выше",
    },
  },
];

export default function DataResetPage() {
  const { language, companies, activeCompanyId } = useAuthStore();
  const t = (uz: string, ru: string) => (language === "uz" ? uz : ru);
  const qc = useQueryClient();

  const activeCompany = companies.find((c) => c.id === activeCompanyId);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmText, setConfirmText] = useState("");
  const [lastResult, setLastResult] = useState<Record<string, number> | null>(null);

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    setLastResult(null);
  };

  const resetMut = useMutation({
    mutationFn: () =>
      dataResetApi.reset({
        modules: Array.from(selected),
        confirm_company_name: confirmText,
      }),
    onSuccess: (res) => {
      setLastResult(res.deleted_counts);
      setSelected(new Set());
      setConfirmText("");
      qc.invalidateQueries();
      toast.success(t("Bazadagi tanlangan ma'lumotlar tozalandi", "Выбранные данные очищены"));
    },
    onError: (e: Error) => {
      if (e instanceof ApiException && e.code === "CONFIRMATION_MISMATCH") {
        toast.error(t("Kompaniya nomi noto'g'ri kiritildi", "Название компании введено неверно"));
      } else {
        toast.error(e.message);
      }
    },
  });

  const canSubmit =
    selected.size > 0 &&
    !!activeCompany &&
    confirmText.trim() === activeCompany.name &&
    !resetMut.isPending;

  return (
    <div className="max-w-2xl">
      <h1 className="mb-1 text-xl font-bold text-gray-900">{t("Bazani tozalash", "Очистка данных")}</h1>
      <p className="mb-6 text-[13px] text-foreground-muted">
        {t(
          "Joriy kompaniya bo'yicha tanlangan modullardagi ma'lumotlarni butunlay o'chirish",
          "Полное удаление данных выбранных модулей для текущей компании"
        )}
      </p>

      <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger/5 p-3.5">
        <AlertTriangle size={18} className="mt-0.5 flex-shrink-0 text-danger" />
        <div className="text-[13px] text-foreground">
          <p className="font-semibold text-danger">{t("Diqqat: bu amalni ortga qaytarib bo'lmaydi", "Внимание: это действие необратимо")}</p>
          <p className="mt-0.5 text-foreground-muted">
            {t(
              "O'chirilgan ma'lumotlarni tiklash imkoni yo'q. Foydalanuvchilar, kompaniyalar, omborlar, kontragentlar va shartnomalar kabi asosiy (master) ma'lumotlar tegilmaydi.",
              "Удалённые данные восстановить нельзя. Основные (master) данные — пользователи, компании, склады, контрагенты, договоры — не затрагиваются."
            )}
          </p>
        </div>
      </div>

      <div className="mb-5 rounded-xl border border-border bg-surface p-3.5">
        <p className="text-[13px] text-foreground-muted">
          {t("Joriy kompaniya", "Текущая компания")}: <span className="font-semibold text-foreground">{activeCompany?.name ?? "—"}</span>
        </p>
      </div>

      <div className="mb-5 flex flex-col gap-2">
        {MODULES.map((m) => (
          <label
            key={m.key}
            className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-3 hover:bg-muted"
          >
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 flex-shrink-0 accent-danger"
              checked={selected.has(m.key)}
              onChange={() => toggle(m.key)}
            />
            <div>
              <p className="text-[13px] font-semibold text-foreground">{t(m.label.uz, m.label.ru)}</p>
              <p className="text-[12px] text-foreground-muted">{t(m.hint.uz, m.hint.ru)}</p>
            </div>
          </label>
        ))}
      </div>

      {selected.size > 0 && (
        <div className="mb-5">
          <Input
            label={t(
              `Davom etish uchun kompaniya nomini yozing: "${activeCompany?.name ?? ""}"`,
              `Введите название компании для подтверждения: "${activeCompany?.name ?? ""}"`
            )}
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder={activeCompany?.name}
          />
        </div>
      )}

      <Button
        variant="danger"
        disabled={!canSubmit}
        loading={resetMut.isPending}
        onClick={() => resetMut.mutate()}
      >
        <Trash2 size={15} /> {t("Bazani tozalash", "Очистить данные")}
      </Button>

      {lastResult && (
        <div className="mt-6 rounded-xl border border-border bg-surface p-3.5">
          <p className="mb-2 text-[13px] font-semibold text-foreground">{t("Natija", "Результат")}</p>
          <ul className="space-y-1 text-[12px] text-foreground-muted">
            {Object.entries(lastResult).map(([table, count]) => (
              <li key={table} className="flex justify-between">
                <span className="font-mono">{table}</span>
                <span>{count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

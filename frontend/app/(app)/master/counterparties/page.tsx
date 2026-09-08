"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Pencil, PowerOff, Power, GitMerge, Users2 } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { counterpartyApi } from "@/lib/api/counterparty";
import type { Counterparty, CounterpartyType } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";

const CP_TYPE_OPTIONS = [
  { value: "BUYER", label: "Buyer / Покупатель" },
  { value: "TOLLING_OWNER", label: "Tolling Owner / Давалец" },
  { value: "BOTH", label: "Both / Оба" },
  { value: "FARMER", label: "Farmer / Фермер" },
];

const schema = z.object({
  name: z.string().min(1).max(255),
  short_name: z.string().max(100).optional().nullable(),
  country: z.string().max(100).optional().nullable(),
  tax_id: z.string().max(100).optional().nullable(),
  counterparty_type: z.enum(["BUYER", "TOLLING_OWNER", "BOTH", "FARMER"]),
  notes: z.string().optional().nullable(),
});

type FormValues = z.infer<typeof schema>;

const mergeSchema = z.object({
  source_id: z.string().uuid(),
  reason: z.string().optional(),
});
type MergeForm = z.infer<typeof mergeSchema>;

export default function CounterpartiesPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<CounterpartyType | "">("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Counterparty | null>(null);
  const [mergeTarget, setMergeTarget] = useState<Counterparty | null>(null);

  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["counterparties", page, search, filterType],
    queryFn: () => counterpartyApi.list({
      page: page + 1,
      page_size: PAGE_SIZE,
      search: search || undefined,
      counterparty_type: filterType || undefined,
    }),
  });

  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { counterparty_type: "BUYER" },
  });
  const cpType = watch("counterparty_type");

  const mergeForm = useForm<MergeForm>({ resolver: zodResolver(mergeSchema) });

  const createMut = useMutation({
    mutationFn: counterpartyApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["counterparties"] }); setModalOpen(false); reset(); toast.success(t("Yaratildi", "Создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: FormValues }) => counterpartyApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["counterparties"] }); setModalOpen(false); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? counterpartyApi.deactivate(id) : counterpartyApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counterparties"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  const mergeMut = useMutation({
    mutationFn: ({ targetId, sourceId, reason }: { targetId: string; sourceId: string; reason?: string }) =>
      counterpartyApi.merge(targetId, sourceId, reason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["counterparties"] }); setMergeTarget(null); mergeForm.reset(); toast.success(t("Birlashtirildi", "Объединено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    reset({ name: "", short_name: "", country: "", tax_id: "", counterparty_type: "BUYER", notes: "" });
    setModalOpen(true);
  }

  function openEdit(cp: Counterparty) {
    setEditTarget(cp);
    reset({ name: cp.name, short_name: cp.short_name, country: cp.country, tax_id: cp.tax_id, counterparty_type: cp.counterparty_type, notes: cp.notes });
    setModalOpen(true);
  }

  function onSubmit(values: FormValues) {
    if (editTarget) {
      updateMut.mutate({ id: editTarget.id, data: values });
    } else {
      createMut.mutate(values);
    }
  }

  const columns: ColumnDef<Counterparty>[] = [
    {
      accessorKey: "name",
      header: t("Nomi", "Название"),
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.name}</p>
          {row.original.short_name && <p className="text-xs text-gray-400">{row.original.short_name}</p>}
          {row.original.tax_id && <p className="text-xs text-gray-400">INN: {row.original.tax_id}</p>}
        </div>
      ),
    },
    { accessorKey: "country", header: t("Mamlakat", "Страна"), cell: ({ getValue }) => (getValue() as string | null) || "—" },
    {
      accessorKey: "counterparty_type",
      header: t("Tur", "Тип"),
      size: 120,
      cell: ({ getValue }) => {
        const opt = CP_TYPE_OPTIONS.find(o => o.value === getValue());
        return opt ? <Badge variant="info">{opt.label.split(" / ")[language === "uz" ? 0 : 1]}</Badge> : null;
      },
    },
    {
      accessorKey: "is_active",
      header: t("Holat", "Статус"),
      size: 90,
      cell: ({ getValue }) => (
        <Badge variant={getValue() ? "success" : "danger"}>
          {getValue() ? t("Aktiv", "Активен") : t("Nofaol", "Неактивен")}
        </Badge>
      ),
    },
    {
      id: "actions",
      size: 110,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" title={t("Birlashtirish", "Объединить")} onClick={() => { setMergeTarget(row.original); mergeForm.reset(); }}>
            <GitMerge size={14} />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => openEdit(row.original)}>
            <Pencil size={14} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => toggleMut.mutate({ id: row.original.id, active: row.original.is_active })}
          >
            {row.original.is_active ? <PowerOff size={14} className="text-red-500" /> : <Power size={14} className="text-green-500" />}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users2 size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">{t("Kontragentlar", "Контрагенты")}</h1>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus size={15} />
          {t("Qo'shish", "Добавить")}
        </Button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className="max-w-xs flex-1">
          <Input placeholder={t("Qidirish...", "Поиск...")} value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} />
        </div>
        <div className="w-48">
          <Select
            value={filterType}
            onValueChange={(v) => { setFilterType(v as CounterpartyType | ""); setPage(0); }}
            placeholder={t("Barcha turlar", "Все типы")}
            options={[{ value: "", label: t("Barcha turlar", "Все типы") }, ...CP_TYPE_OPTIONS]}
          />
        </div>
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
        emptyText={t("Kontragentlar topilmadi", "Контрагенты не найдены")}
      />

      {/* Create/Edit Modal */}
      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) { setEditTarget(null); reset(); } }}
        title={editTarget ? t("Tahrirlash", "Редактировать") : t("Yangi kontragent", "Новый контрагент")}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input label={t("Nomi *", "Название *")} {...register("name")} error={errors.name?.message} />
          <Input label={t("Qisqa nomi", "Краткое название")} {...register("short_name")} />
          <Input label={t("Mamlakat", "Страна")} {...register("country")} />
          <Input label={t("INN", "ИНН")} {...register("tax_id")} />
          <Select
            label={t("Tur", "Тип")}
            value={cpType}
            onValueChange={(v) => setValue("counterparty_type", v as CounterpartyType)}
            options={CP_TYPE_OPTIONS}
          />
          <Input label={t("Izoh", "Примечание")} {...register("notes")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={createMut.isPending || updateMut.isPending}>
              {editTarget ? t("Saqlash", "Сохранить") : t("Yaratish", "Создать")}
            </Button>
          </ModalFooter>
        </form>
      </Modal>

      {/* Merge Modal */}
      <Modal
        open={!!mergeTarget}
        onOpenChange={(v) => { if (!v) { setMergeTarget(null); mergeForm.reset(); } }}
        title={t("Birlashtirish", "Объединить контрагентов")}
        description={mergeTarget ? `${t("Manba", "Источник")} → ${mergeTarget.name}` : undefined}
      >
        <form
          onSubmit={mergeForm.handleSubmit((d) =>
            mergeMut.mutate({ targetId: mergeTarget!.id, sourceId: d.source_id, reason: d.reason })
          )}
          className="flex flex-col gap-4"
        >
          <Input
            label={t("Manba kontragent IDsi", "ID контрагента-источника")}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            {...mergeForm.register("source_id")}
            error={mergeForm.formState.errors.source_id?.message}
          />
          <Input label={t("Sabab", "Причина")} {...mergeForm.register("reason")} />
          <p className="text-xs text-amber-600 bg-amber-50 rounded p-2">
            {t(
              "Barcha FK havolalar (jo'natmalar, lotlar, shartnomalar) maqsad kontragentga o'tkaziladi. Manba nofaol bo'ladi.",
              "Все FK-ссылки (отгрузки, лоты, контракты) будут перенаправлены на целевой контрагент. Источник станет неактивным."
            )}
          </p>
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setMergeTarget(null)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" variant="danger" loading={mergeMut.isPending}>{t("Birlashtirish", "Объединить")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

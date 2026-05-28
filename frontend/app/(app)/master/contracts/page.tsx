"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Pencil, PowerOff, Power, FileText } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { contractApi } from "@/lib/api/contract";
import { counterpartyApi } from "@/lib/api/counterparty";
import type { Contract } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const schema = z.object({
  contract_number: z.string().min(1).max(100),
  contract_date: z.string().min(1),
  counterparty_id: z.string().uuid(),
  description: z.string().optional().nullable(),
});

type FormValues = z.infer<typeof schema>;

export default function ContractsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Contract | null>(null);

  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["contracts", page, search],
    queryFn: () => contractApi.list({ page: page + 1, page_size: PAGE_SIZE, search: search || undefined }),
  });

  const { data: counterparties } = useQuery({
    queryKey: ["counterparties-all"],
    queryFn: () => counterpartyApi.list({ page_size: 200, active_only: true }),
  });

  const cpOptions = (counterparties?.items ?? []).map(cp => ({ value: cp.id, label: cp.name }));

  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const createMut = useMutation({
    mutationFn: contractApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["contracts"] }); setModalOpen(false); reset(); toast.success(t("Shartnoma yaratildi", "Договор создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FormValues> }) => contractApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["contracts"] }); setModalOpen(false); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? contractApi.deactivate(id) : contractApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contracts"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    reset({ contract_number: "", contract_date: new Date().toISOString().slice(0, 10), counterparty_id: "", description: "" });
    setModalOpen(true);
  }

  function openEdit(c: Contract) {
    setEditTarget(c);
    reset({ contract_number: c.contract_number, contract_date: c.contract_date, counterparty_id: c.counterparty_id, description: c.description ?? "" });
    setModalOpen(true);
  }

  function onSubmit(values: FormValues) {
    if (editTarget) {
      updateMut.mutate({ id: editTarget.id, data: { contract_number: values.contract_number, contract_date: values.contract_date, description: values.description } });
    } else {
      createMut.mutate(values);
    }
  }

  const columns: ColumnDef<Contract>[] = [
    {
      accessorKey: "contract_number",
      header: t("Shartnoma raqami", "Номер договора"),
      cell: ({ getValue }) => <span className="font-medium">{getValue() as string}</span>,
    },
    { accessorKey: "counterparty_name", header: t("Kontragent", "Контрагент") },
    {
      accessorKey: "contract_date",
      header: t("Sana", "Дата"),
      size: 110,
      cell: ({ getValue }) => formatDate(getValue() as string, language),
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
      size: 90,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
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
          <FileText size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">{t("Shartnomalar", "Договоры")}</h1>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus size={15} />
          {t("Qo'shish", "Добавить")}
        </Button>
      </div>

      <div className="mb-4 max-w-xs">
        <Input placeholder={t("Qidirish...", "Поиск...")} value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} />
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
        emptyText={t("Shartnomalar topilmadi", "Договоры не найдены")}
      />

      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) { setEditTarget(null); reset(); } }}
        title={editTarget ? t("Tahrirlash", "Редактировать") : t("Yangi shartnoma", "Новый договор")}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input label={t("Raqami *", "Номер *")} {...register("contract_number")} error={errors.contract_number?.message} />
          <Input label={t("Sana *", "Дата *")} type="date" {...register("contract_date")} error={errors.contract_date?.message} />
          {!editTarget && (
            <Select
              label={t("Kontragent *", "Контрагент *")}
              value={watch("counterparty_id")}
              onValueChange={(v) => setValue("counterparty_id", v)}
              options={cpOptions}
              placeholder={t("Tanlang...", "Выберите...")}
            />
          )}
          <Input label={t("Tavsif", "Описание")} {...register("description")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={createMut.isPending || updateMut.isPending}>
              {editTarget ? t("Saqlash", "Сохранить") : t("Yaratish", "Создать")}
            </Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

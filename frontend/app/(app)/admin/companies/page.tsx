"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Pencil, PowerOff, Power, Building2 } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { companyApi } from "@/lib/api/company";
import type { Company } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const schema = z.object({
  name: z.string().min(1).max(255),
  short_name: z.string().max(50).optional().nullable(),
  tax_id: z.string().max(50).optional().nullable(),
  address: z.string().optional().nullable(),
});

type FormValues = z.infer<typeof schema>;

export default function CompaniesPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Company | null>(null);

  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["companies", page, search],
    queryFn: () => companyApi.list({ page: page + 1, page_size: PAGE_SIZE, search: search || undefined }),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const createMut = useMutation({
    mutationFn: companyApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["companies"] }); setModalOpen(false); reset(); toast.success(t("Kompaniya yaratildi", "Компания создана")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: FormValues }) => companyApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["companies"] }); setModalOpen(false); reset(); setEditTarget(null); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? companyApi.deactivate(id) : companyApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    reset({ name: "", short_name: "", tax_id: "", address: "" });
    setModalOpen(true);
  }

  function openEdit(company: Company) {
    setEditTarget(company);
    reset({ name: company.name, short_name: company.short_name, tax_id: company.tax_id, address: company.address });
    setModalOpen(true);
  }

  function onSubmit(values: FormValues) {
    if (editTarget) {
      updateMut.mutate({ id: editTarget.id, data: values });
    } else {
      createMut.mutate(values);
    }
  }

  const columns: ColumnDef<Company>[] = [
    {
      accessorKey: "name",
      header: t("Nomi", "Название"),
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.name}</p>
          {row.original.short_name && <p className="text-xs text-gray-400">{row.original.short_name}</p>}
        </div>
      ),
    },
    { accessorKey: "tax_id", header: t("INN", "ИНН"), cell: ({ getValue }) => getValue() as string || "—" },
    { accessorKey: "address", header: t("Manzil", "Адрес"), cell: ({ getValue }) => (getValue() as string | null) || "—" },
    {
      accessorKey: "is_active",
      header: t("Holat", "Статус"),
      size: 90,
      cell: ({ getValue }) => (
        <Badge variant={getValue() ? "success" : "danger"}>
          {getValue() ? t("Aktiv", "Активна") : t("Nofaol", "Неактивна")}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: t("Yaratilgan", "Создана"),
      size: 110,
      cell: ({ getValue }) => formatDate(getValue() as string, language),
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
          <Building2 size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">{t("Kompaniyalar", "Компании")}</h1>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus size={15} />
          {t("Qo'shish", "Добавить")}
        </Button>
      </div>

      <div className="mb-4 max-w-xs">
        <Input
          placeholder={t("Qidirish...", "Поиск...")}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
        />
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
        emptyText={t("Kompaniyalar topilmadi", "Компании не найдены")}
      />

      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) { setEditTarget(null); reset(); } }}
        title={editTarget ? t("Tahrirlash", "Редактировать") : t("Yangi kompaniya", "Новая компания")}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input label={t("Nomi *", "Название *")} {...register("name")} error={errors.name?.message} />
          <Input label={t("Qisqa nomi", "Краткое название")} {...register("short_name")} error={errors.short_name?.message} />
          <Input label={t("INN", "ИНН")} {...register("tax_id")} error={errors.tax_id?.message} />
          <Input label={t("Manzil", "Адрес")} {...register("address")} error={errors.address?.message} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              {t("Bekor qilish", "Отмена")}
            </Button>
            <Button type="submit" loading={createMut.isPending || updateMut.isPending}>
              {editTarget ? t("Saqlash", "Сохранить") : t("Yaratish", "Создать")}
            </Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

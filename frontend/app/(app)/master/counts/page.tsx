"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Pencil, PowerOff, Power, Tag } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { countApi } from "@/lib/api/count";
import type { CountCatalog } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal, ModalFooter } from "@/components/ui/Modal";

const schema = z.object({
  count_value: z.string().min(1).max(50),
  yarn_type: z.string().max(100).optional().nullable(),
  composition: z.string().optional().nullable(),
  description: z.string().optional().nullable(),
});

type FormValues = z.infer<typeof schema>;

export default function CountsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CountCatalog | null>(null);

  const PAGE_SIZE = 100;

  const { data, isLoading } = useQuery({
    queryKey: ["counts", page, search],
    queryFn: () => countApi.list({ page: page + 1, page_size: PAGE_SIZE, search: search || undefined }),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const createMut = useMutation({
    mutationFn: countApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["counts"] }); setModalOpen(false); reset(); toast.success(t("Yaratildi", "Создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<FormValues> }) => countApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["counts"] }); setModalOpen(false); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? countApi.deactivate(id) : countApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counts"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    reset({ count_value: "", yarn_type: "", composition: "", description: "" });
    setModalOpen(true);
  }

  function openEdit(c: CountCatalog) {
    setEditTarget(c);
    reset({ count_value: c.count_value, yarn_type: c.yarn_type ?? "", composition: c.composition ?? "", description: c.description ?? "" });
    setModalOpen(true);
  }

  function onSubmit(values: FormValues) {
    if (editTarget) {
      updateMut.mutate({ id: editTarget.id, data: { yarn_type: values.yarn_type, composition: values.composition, description: values.description } });
    } else {
      createMut.mutate(values);
    }
  }

  const columns: ColumnDef<CountCatalog>[] = [
    { accessorKey: "count_value", header: t("Count", "Count"), cell: ({ getValue }) => <span className="font-semibold font-mono">{getValue() as string}</span> },
    { accessorKey: "yarn_type", header: t("Ip turi", "Тип нити"), cell: ({ getValue }) => (getValue() as string | null) || "—" },
    { accessorKey: "composition", header: t("Tarkibi", "Состав"), cell: ({ getValue }) => (getValue() as string | null) || "—" },
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
          <Tag size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">{t("Count kataloği", "Каталог count")}</h1>
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
        emptyText={t("Countlar topilmadi", "Count не найдены")}
      />

      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) { setEditTarget(null); reset(); } }}
        title={editTarget ? t("Tahrirlash", "Редактировать") : t("Yangi count", "Новый count")}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <Input
            label={t("Count qiymati *", "Значение count *")}
            placeholder="30/1"
            {...register("count_value")}
            disabled={!!editTarget}
            error={errors.count_value?.message}
          />
          <Input label={t("Ip turi", "Тип нити")} placeholder="Ring, OE..." {...register("yarn_type")} />
          <Input label={t("Tarkibi", "Состав")} placeholder="100% cotton" {...register("composition")} />
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

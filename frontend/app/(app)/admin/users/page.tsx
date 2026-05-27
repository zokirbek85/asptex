"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Pencil, PowerOff, Power, Users as UsersIcon, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { userApi } from "@/lib/api/user";
import type { User, UserRole } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const ROLE_OPTIONS = [
  { value: "ADMIN", label: "Admin" },
  { value: "DIRECTOR", label: "Director" },
  { value: "DEPUTY_DIRECTOR", label: "Deputy Director" },
  { value: "WH_RAW", label: "WH Raw Cotton" },
  { value: "WH_FINISHED", label: "WH Finished Goods" },
  { value: "PRODUCTION", label: "Production" },
  { value: "ACCOUNTANT", label: "Accountant" },
];

const createSchema = z.object({
  username: z.string().min(3).max(100),
  email: z.string().email().optional().or(z.literal("")),
  full_name: z.string().min(1).max(255),
  password: z.string().min(8).max(128),
  preferred_language: z.enum(["uz", "ru"]),
});

const updateSchema = z.object({
  email: z.string().email().optional().or(z.literal("")),
  full_name: z.string().min(1).max(255),
  preferred_language: z.enum(["uz", "ru"]),
});

type CreateForm = z.infer<typeof createSchema>;
type UpdateForm = z.infer<typeof updateSchema>;

export default function UsersPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<User | null>(null);
  const [rolesTarget, setRolesTarget] = useState<User | null>(null);

  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["users", page, search],
    queryFn: () => userApi.list({ page: page + 1, page_size: PAGE_SIZE, search: search || undefined }),
  });

  const createForm = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { preferred_language: "uz" },
  });

  const updateForm = useForm<UpdateForm>({
    resolver: zodResolver(updateSchema),
    defaultValues: { preferred_language: "uz" },
  });

  const createMut = useMutation({
    mutationFn: userApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setModalOpen(false); createForm.reset(); toast.success(t("Foydalanuvchi yaratildi", "Пользователь создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateForm }) =>
      userApi.update(id, { ...data, email: data.email || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setModalOpen(false); setEditTarget(null); toast.success(t("Yangilandi", "Обновлено")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? userApi.deactivate(id) : userApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    createForm.reset({ username: "", email: "", full_name: "", password: "", preferred_language: "uz" });
    setModalOpen(true);
  }

  function openEdit(user: User) {
    setEditTarget(user);
    updateForm.reset({ email: user.email ?? "", full_name: user.full_name, preferred_language: user.preferred_language });
    setModalOpen(true);
  }

  const columns: ColumnDef<User>[] = [
    {
      accessorKey: "username",
      header: t("Foydalanuvchi", "Пользователь"),
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.username}</p>
          <p className="text-xs text-gray-400">{row.original.full_name}</p>
        </div>
      ),
    },
    { accessorKey: "email", header: "Email", cell: ({ getValue }) => (getValue() as string | null) || "—" },
    {
      id: "roles",
      header: t("Rollar", "Роли"),
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.roles.slice(0, 3).map((r) => (
            <Badge key={r.id} variant="info" className="text-xs">{r.role}</Badge>
          ))}
          {row.original.roles.length > 3 && (
            <Badge variant="default">+{row.original.roles.length - 3}</Badge>
          )}
        </div>
      ),
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
      accessorKey: "created_at",
      header: t("Yaratilgan", "Создан"),
      size: 110,
      cell: ({ getValue }) => formatDate(getValue() as string, language),
    },
    {
      id: "actions",
      size: 110,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" title={t("Rollar", "Роли")} onClick={() => setRolesTarget(row.original)}>
            <ShieldCheck size={14} />
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
          <UsersIcon size={20} className="text-blue-600" />
          <h1 className="text-xl font-bold text-gray-900">{t("Foydalanuvchilar", "Пользователи")}</h1>
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
        emptyText={t("Foydalanuvchilar topilmadi", "Пользователи не найдены")}
      />

      {/* Create/Edit Modal */}
      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) { setEditTarget(null); } }}
        title={editTarget ? t("Tahrirlash", "Редактировать") : t("Yangi foydalanuvchi", "Новый пользователь")}
      >
        {editTarget ? (
          <form onSubmit={updateForm.handleSubmit((d) => updateMut.mutate({ id: editTarget.id, data: d }))} className="flex flex-col gap-4">
            <Input
              label={t("To'liq ismi *", "Полное имя *")}
              {...updateForm.register("full_name")}
              error={updateForm.formState.errors.full_name?.message}
            />
            <Input label="Email" {...updateForm.register("email")} error={updateForm.formState.errors.email?.message} />
            <Select
              label={t("Til", "Язык")}
              value={updateForm.watch("preferred_language")}
              onValueChange={(v) => updateForm.setValue("preferred_language", v as "uz" | "ru")}
              options={[{ value: "uz", label: "O'zbek" }, { value: "ru", label: "Русский" }]}
            />
            <ModalFooter>
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>{t("Bekor", "Отмена")}</Button>
              <Button type="submit" loading={updateMut.isPending}>{t("Saqlash", "Сохранить")}</Button>
            </ModalFooter>
          </form>
        ) : (
          <form onSubmit={createForm.handleSubmit((d) => createMut.mutate({ ...d, email: d.email || null }))} className="flex flex-col gap-4">
            <Input label={t("Login *", "Логин *")} {...createForm.register("username")} error={createForm.formState.errors.username?.message} />
            <Input label={t("To'liq ismi *", "Полное имя *")} {...createForm.register("full_name")} error={createForm.formState.errors.full_name?.message} />
            <Input label="Email" {...createForm.register("email")} error={createForm.formState.errors.email?.message} />
            <Input label={t("Parol *", "Пароль *")} type="password" {...createForm.register("password")} error={createForm.formState.errors.password?.message} />
            <Select
              label={t("Til", "Язык")}
              value={createForm.watch("preferred_language")}
              onValueChange={(v) => createForm.setValue("preferred_language", v as "uz" | "ru")}
              options={[{ value: "uz", label: "O'zbek" }, { value: "ru", label: "Русский" }]}
            />
            <ModalFooter>
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>{t("Bekor", "Отмена")}</Button>
              <Button type="submit" loading={createMut.isPending}>{t("Yaratish", "Создать")}</Button>
            </ModalFooter>
          </form>
        )}
      </Modal>

      {/* Roles Modal — read-only summary */}
      <Modal
        open={!!rolesTarget}
        onOpenChange={(v) => { if (!v) setRolesTarget(null); }}
        title={rolesTarget ? `${rolesTarget.username} — ${t("Rollar", "Роли")}` : ""}
      >
        {rolesTarget && (
          <div>
            {rolesTarget.roles.length === 0 ? (
              <p className="text-sm text-gray-500">{t("Rollar yo'q", "Роли не назначены")}</p>
            ) : (
              <div className="divide-y divide-gray-100">
                {rolesTarget.roles.map((r) => (
                  <div key={r.id} className="py-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{r.company_name}</p>
                      {r.warehouse_name && <p className="text-xs text-gray-400">{r.warehouse_name}</p>}
                    </div>
                    <Badge variant="info">{r.role}</Badge>
                  </div>
                ))}
              </div>
            )}
            <ModalFooter>
              <Button variant="outline" onClick={() => setRolesTarget(null)}>{t("Yopish", "Закрыть")}</Button>
            </ModalFooter>
          </div>
        )}
      </Modal>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Plus, Pencil, PowerOff, Power, Users as UsersIcon,
  ShieldCheck, Trash2,
} from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { userApi } from "@/lib/api/user";
import { warehouseApi } from "@/lib/api/warehouse";
import type { User, UserRole, UserRoleAssign, UserRoleRecord, Warehouse } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

// Roles that require a warehouse assignment
const WAREHOUSE_ROLES: UserRole[] = ["WH_RAW", "WH_FINISHED"];

const WAREHOUSE_TYPE_FOR_ROLE: Partial<Record<UserRole, string>> = {
  WH_RAW: "RAW_COTTON",
  WH_FINISHED: "FINISHED_GOODS",
};

const ROLE_OPTIONS = [
  { value: "ADMIN", label: "Admin" },
  { value: "DIRECTOR", label: "Director" },
  { value: "DEPUTY_DIRECTOR", label: "Deputy Director" },
  { value: "WH_RAW", label: "Xom ashyo ombori (WH_RAW)" },
  { value: "WH_FINISHED", label: "Tayyor mahsulot ombori (WH_FINISHED)" },
  { value: "PRODUCTION", label: "Ishlab chiqarish (PRODUCTION)" },
  { value: "ACCOUNTANT", label: "Buxgalter (ACCOUNTANT)" },
];

const LANG_OPTIONS = [
  { value: "uz", label: "O'zbek" },
  { value: "ru", label: "Русский" },
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

const assignRoleSchema = z.object({
  role: z.string().min(1, "Rolni tanlang"),
  warehouse_id: z.string().optional().nullable(),
});

type CreateForm = z.infer<typeof createSchema>;
type UpdateForm = z.infer<typeof updateSchema>;
type AssignRoleForm = z.infer<typeof assignRoleSchema>;

export default function UsersPage() {
  const { language, activeCompanyId } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<User | null>(null);
  const [rolesTarget, setRolesTarget] = useState<User | null>(null);
  const [showAddRole, setShowAddRole] = useState(false);
  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["users", page, search],
    queryFn: () => userApi.list({ page: page + 1, page_size: PAGE_SIZE, search: search || undefined }),
  });

  // Fetch warehouses for role assignment (only when roles modal is open)
  const { data: warehousesData } = useQuery({
    queryKey: ["warehouses-all"],
    queryFn: () => warehouseApi.list({ active_only: true, page_size: 200 }),
    enabled: !!rolesTarget,
  });
  const allWarehouses: Warehouse[] = warehousesData?.items ?? [];

  const createForm = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { preferred_language: "uz" },
  });

  const updateForm = useForm<UpdateForm>({
    resolver: zodResolver(updateSchema),
  });

  const assignRoleForm = useForm<AssignRoleForm>({
    resolver: zodResolver(assignRoleSchema),
    defaultValues: { role: "", warehouse_id: null },
  });

  const selectedRole = assignRoleForm.watch("role") as UserRole;
  const needsWarehouse = WAREHOUSE_ROLES.includes(selectedRole);
  const filteredWarehouses = needsWarehouse
    ? allWarehouses.filter(
        (w) => w.warehouse_type === WAREHOUSE_TYPE_FOR_ROLE[selectedRole]
      )
    : [];

  const createMut = useMutation({
    mutationFn: userApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setModalOpen(false);
      createForm.reset();
      toast.success(t("Foydalanuvchi yaratildi", "Пользователь создан"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateForm }) =>
      userApi.update(id, { ...data, email: data.email || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setModalOpen(false);
      setEditTarget(null);
      toast.success(t("Yangilandi", "Обновлено"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? userApi.deactivate(id) : userApi.activate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e: Error) => toast.error(e.message),
  });

  const assignRoleMut = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserRoleAssign }) =>
      userApi.assignRole(userId, data),
    onSuccess: (newRole) => {
      // Update rolesTarget locally so the modal reflects the change immediately
      if (rolesTarget) {
        const updated: User = {
          ...rolesTarget,
          roles: [...rolesTarget.roles.filter((r) => r.company_id !== newRole.company_id), newRole],
        };
        setRolesTarget(updated);
      }
      qc.invalidateQueries({ queryKey: ["users"] });
      assignRoleForm.reset({ role: "", warehouse_id: null });
      setShowAddRole(false);
      toast.success(t("Rol berildi", "Роль назначена"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeRoleMut = useMutation({
    mutationFn: ({ userId, companyId }: { userId: string; companyId: string }) =>
      userApi.removeRole(userId, companyId),
    onSuccess: (_, { companyId }) => {
      if (rolesTarget) {
        setRolesTarget({
          ...rolesTarget,
          roles: rolesTarget.roles.filter((r) => r.company_id !== companyId),
        });
      }
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success(t("Rol o'chirildi", "Роль удалена"));
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function openCreate() {
    setEditTarget(null);
    createForm.reset({ username: "", email: "", full_name: "", password: "", preferred_language: "uz" });
    setModalOpen(true);
  }

  function openEdit(user: User) {
    setEditTarget(user);
    updateForm.reset({
      email: user.email ?? "",
      full_name: user.full_name,
      preferred_language: user.preferred_language,
    });
    setModalOpen(true);
  }

  function openRoles(user: User) {
    setRolesTarget(user);
    setShowAddRole(false);
    assignRoleForm.reset({ role: "", warehouse_id: null });
  }

  function handleAssignRole(formData: AssignRoleForm) {
    if (!rolesTarget || !activeCompanyId) return;
    assignRoleMut.mutate({
      userId: rolesTarget.id,
      data: {
        company_id: activeCompanyId,
        role: formData.role as UserRole,
        warehouse_id: needsWarehouse ? (formData.warehouse_id ?? null) : null,
      },
    });
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
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ getValue }) => (getValue() as string | null) || "—",
    },
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
          {row.original.roles.length === 0 && (
            <span className="text-xs text-gray-400">—</span>
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
          <Button
            variant="ghost" size="icon"
            title={t("Rollarni boshqarish", "Управление ролями")}
            onClick={() => openRoles(row.original)}
          >
            <ShieldCheck size={14} className="text-blue-500" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => openEdit(row.original)}>
            <Pencil size={14} />
          </Button>
          <Button
            variant="ghost" size="icon"
            onClick={() => toggleMut.mutate({ id: row.original.id, active: row.original.is_active })}
          >
            {row.original.is_active
              ? <PowerOff size={14} className="text-red-500" />
              : <Power size={14} className="text-green-500" />}
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
          <h1 className="text-xl font-bold text-gray-900">
            {t("Foydalanuvchilar", "Пользователи")}
          </h1>
        </div>
        <Button onClick={openCreate} size="sm">
          <Plus size={15} /> {t("Qo'shish", "Добавить")}
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
          const next = typeof updater === "function"
            ? updater({ pageIndex: page, pageSize: PAGE_SIZE })
            : updater;
          setPage(next.pageIndex);
        }}
        emptyText={t("Foydalanuvchilar topilmadi", "Пользователи не найдены")}
      />

      {/* ── Create / Edit Modal ────────────────────────────────────────────── */}
      <Modal
        open={modalOpen}
        onOpenChange={(v) => { setModalOpen(v); if (!v) setEditTarget(null); }}
        title={editTarget
          ? t("Foydalanuvchini tahrirlash", "Редактировать пользователя")
          : t("Yangi foydalanuvchi", "Новый пользователь")}
      >
        {editTarget ? (
          <form
            onSubmit={updateForm.handleSubmit((d) =>
              updateMut.mutate({ id: editTarget.id, data: d })
            )}
            className="flex flex-col gap-4"
          >
            <Input
              label={t("To'liq ismi *", "Полное имя *")}
              {...updateForm.register("full_name")}
              error={updateForm.formState.errors.full_name?.message}
            />
            <Input
              label="Email"
              {...updateForm.register("email")}
              error={updateForm.formState.errors.email?.message}
            />
            <Select
              label={t("Til", "Язык")}
              value={updateForm.watch("preferred_language")}
              onValueChange={(v) => updateForm.setValue("preferred_language", v as "uz" | "ru")}
              options={LANG_OPTIONS}
            />
            <ModalFooter>
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
                {t("Bekor", "Отмена")}
              </Button>
              <Button type="submit" loading={updateMut.isPending}>
                {t("Saqlash", "Сохранить")}
              </Button>
            </ModalFooter>
          </form>
        ) : (
          <form
            onSubmit={createForm.handleSubmit((d) =>
              createMut.mutate({ ...d, email: d.email || null })
            )}
            className="flex flex-col gap-4"
          >
            <Input
              label={t("Login *", "Логин *")}
              {...createForm.register("username")}
              error={createForm.formState.errors.username?.message}
            />
            <Input
              label={t("To'liq ismi *", "Полное имя *")}
              {...createForm.register("full_name")}
              error={createForm.formState.errors.full_name?.message}
            />
            <Input
              label="Email"
              {...createForm.register("email")}
              error={createForm.formState.errors.email?.message}
            />
            <Input
              label={t("Parol *", "Пароль *")}
              type="password"
              {...createForm.register("password")}
              error={createForm.formState.errors.password?.message}
            />
            <Select
              label={t("Til", "Язык")}
              value={createForm.watch("preferred_language")}
              onValueChange={(v) => createForm.setValue("preferred_language", v as "uz" | "ru")}
              options={LANG_OPTIONS}
            />
            <ModalFooter>
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
                {t("Bekor", "Отmena")}
              </Button>
              <Button type="submit" loading={createMut.isPending}>
                {t("Yaratish", "Создать")}
              </Button>
            </ModalFooter>
          </form>
        )}
      </Modal>

      {/* ── Roles Management Modal ─────────────────────────────────────────── */}
      <Modal
        open={!!rolesTarget}
        onOpenChange={(v) => {
          if (!v) { setRolesTarget(null); setShowAddRole(false); }
        }}
        title={rolesTarget
          ? `${rolesTarget.username} — ${t("Rollarni boshqarish", "Управление ролями")}`
          : ""}
        className="max-w-lg"
      >
        {rolesTarget && (
          <div>
            {/* Existing roles */}
            <div className="mb-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                {t("Mavjud rollar", "Текущие роли")}
              </p>
              {rolesTarget.roles.length === 0 ? (
                <p className="rounded-lg bg-slate-50 py-4 text-center text-sm text-slate-400">
                  {t("Rol belgilanmagan", "Роли не назначены")}
                </p>
              ) : (
                <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                  {rolesTarget.roles.map((r) => (
                    <div key={r.id} className="flex items-center justify-between px-3 py-2.5">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant="info" className="shrink-0">{r.role}</Badge>
                          <span className="truncate text-sm text-slate-600">{r.company_name}</span>
                        </div>
                        {r.warehouse_name && (
                          <p className="mt-0.5 text-xs text-slate-400">
                            {t("Ombor", "Склад")}: {r.warehouse_name}
                          </p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        title={t("O'chirish", "Удалить")}
                        loading={removeRoleMut.isPending}
                        onClick={() =>
                          removeRoleMut.mutate({
                            userId: rolesTarget.id,
                            companyId: r.company_id,
                          })
                        }
                      >
                        <Trash2 size={13} className="text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add role section */}
            {!showAddRole ? (
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={() => {
                  setShowAddRole(true);
                  assignRoleForm.reset({ role: "", warehouse_id: null });
                }}
              >
                <Plus size={14} /> {t("Rol qo'shish", "Добавить роль")}
              </Button>
            ) : (
              <form
                onSubmit={assignRoleForm.handleSubmit(handleAssignRole)}
                className="rounded-lg border border-blue-100 bg-blue-50 p-3"
              >
                <p className="mb-3 text-sm font-medium text-blue-700">
                  {t("Yangi rol belgilash", "Назначить новую роль")}
                </p>

                <div className="flex flex-col gap-3">
                  <Select
                    label={t("Rol *", "Роль *")}
                    value={assignRoleForm.watch("role")}
                    onValueChange={(v) => {
                      assignRoleForm.setValue("role", v);
                      assignRoleForm.setValue("warehouse_id", null);
                    }}
                    options={ROLE_OPTIONS}
                    error={assignRoleForm.formState.errors.role?.message}
                  />

                  {needsWarehouse && (
                    <Select
                      label={t("Ombor *", "Склад *")}
                      value={assignRoleForm.watch("warehouse_id") ?? ""}
                      onValueChange={(v) => assignRoleForm.setValue("warehouse_id", v || null)}
                      options={
                        filteredWarehouses.length > 0
                          ? filteredWarehouses.map((w) => ({ value: w.id, label: w.name }))
                          : [{ value: "", label: t("Omborlar topilmadi", "Нет складов"), disabled: true }]
                      }
                      placeholder={t("Ombor tanlang...", "Выберите склад...")}
                    />
                  )}
                </div>

                <div className="mt-3 flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setShowAddRole(false)}
                  >
                    {t("Bekor", "Отмена")}
                  </Button>
                  <Button type="submit" size="sm" loading={assignRoleMut.isPending}>
                    {t("Saqlash", "Сохранить")}
                  </Button>
                </div>
              </form>
            )}

            <ModalFooter>
              <Button variant="outline" onClick={() => setRolesTarget(null)}>
                {t("Yopish", "Закрыть")}
              </Button>
            </ModalFooter>
          </div>
        )}
      </Modal>
    </div>
  );
}

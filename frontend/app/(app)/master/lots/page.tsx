"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Eye, Lock, Unlock, XCircle } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { lotApi } from "@/lib/api/lot";
import type { Lot, LotStatus } from "@/lib/types";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Modal, ModalFooter } from "@/components/ui/Modal";
import { formatDate } from "@/lib/utils";

const closeSchema = z.object({ reason: z.string().optional() });
const reopenSchema = z.object({ reason: z.string().min(1, "Required") });

type CloseForm = z.infer<typeof closeSchema>;
type ReopenForm = z.infer<typeof reopenSchema>;

const STATUS_OPTIONS = [
  { value: "", label: "All / Все" },
  { value: "OPEN", label: "Open / Открыт" },
  { value: "CLOSED", label: "Closed / Закрыт" },
  { value: "BLOCKED", label: "Blocked / Заблокирован" },
];

export default function LotsPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;
  const qc = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<LotStatus | "">("");
  const [closeTarget, setCloseTarget] = useState<Lot | null>(null);
  const [reopenTarget, setReopenTarget] = useState<Lot | null>(null);

  const PAGE_SIZE = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["lots", page, search, statusFilter],
    queryFn: () => lotApi.list({ page: page + 1, page_size: PAGE_SIZE, search: search || undefined, status: statusFilter || undefined }),
  });

  const closeForm = useForm<CloseForm>({ resolver: zodResolver(closeSchema) });
  const reopenForm = useForm<ReopenForm>({ resolver: zodResolver(reopenSchema) });

  const createMut = useMutation({
    mutationFn: () => lotApi.create(),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); toast.success(t("Lot yaratildi", "Лот создан")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const closeMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => lotApi.close(id, reason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); setCloseTarget(null); closeForm.reset(); toast.success(t("Lot yopildi", "Лот закрыт")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const reopenMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => lotApi.reopen(id, reason),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); setReopenTarget(null); reopenForm.reset(); toast.success(t("Lot ochildi", "Лот открыт")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const blockMut = useMutation({
    mutationFn: lotApi.block,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); toast.success(t("Bloklandi", "Заблокирован")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const unblockMut = useMutation({
    mutationFn: lotApi.unblock,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); toast.success(t("Blok olib tashlandi", "Разблокирован")); },
    onError: (e: Error) => toast.error(e.message),
  });

  const statusVariant = (s: LotStatus) =>
    s === "OPEN" ? "success" : s === "BLOCKED" ? "danger" : "default";

  const columns: ColumnDef<Lot>[] = [
    {
      accessorKey: "lot_number",
      header: t("Lot raqami", "Номер лота"),
      cell: ({ row }) => (
        <Link href={`/master/lots/${row.original.id}`} className="font-semibold text-blue-600 hover:underline font-mono">
          {row.original.lot_number}
        </Link>
      ),
    },
    {
      accessorKey: "status",
      header: t("Holat", "Статус"),
      size: 100,
      cell: ({ getValue }) => {
        const s = getValue() as LotStatus;
        return <Badge variant={statusVariant(s)}>{s}</Badge>;
      },
    },
    {
      accessorKey: "opened_at",
      header: t("Ochildi", "Открыт"),
      size: 110,
      cell: ({ getValue }) => formatDate(getValue() as string, language),
    },
    {
      accessorKey: "closed_at",
      header: t("Yopildi", "Закрыт"),
      size: 110,
      cell: ({ getValue }) => getValue() ? formatDate(getValue() as string, language) : "—",
    },
    { accessorKey: "notes", header: t("Izoh", "Примечание"), cell: ({ getValue }) => (getValue() as string | null) || "—" },
    {
      id: "actions",
      size: 130,
      cell: ({ row }) => {
        const lot = row.original;
        return (
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" asChild>
              <Link href={`/master/lots/${lot.id}`}><Eye size={14} /></Link>
            </Button>
            {lot.status === "OPEN" && (
              <Button variant="ghost" size="icon" title={t("Yopish", "Закрыть")} onClick={() => { setCloseTarget(lot); closeForm.reset(); }}>
                <XCircle size={14} className="text-yellow-600" />
              </Button>
            )}
            {lot.status === "CLOSED" && (
              <Button variant="ghost" size="icon" title={t("Qayta ochish", "Открыть снова")} onClick={() => { setReopenTarget(lot); reopenForm.reset(); }}>
                <Unlock size={14} className="text-green-600" />
              </Button>
            )}
            {lot.status !== "BLOCKED" ? (
              <Button variant="ghost" size="icon" title={t("Bloklash", "Заблокировать")} onClick={() => blockMut.mutate(lot.id)}>
                <Lock size={14} className="text-red-500" />
              </Button>
            ) : (
              <Button variant="ghost" size="icon" title={t("Blokni olib tashlash", "Разблокировать")} onClick={() => unblockMut.mutate(lot.id)}>
                <Unlock size={14} className="text-blue-500" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Lotlar", "Лоты")}</h1>
        <Button onClick={() => createMut.mutate()} loading={createMut.isPending} size="sm">
          <Plus size={15} />
          {t("Yangi lot", "Новый лот")}
        </Button>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className="max-w-xs flex-1">
          <Input placeholder={t("Qidirish...", "Поиск...")} value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} />
        </div>
        <div className="w-44">
          <Select
            value={statusFilter}
            onValueChange={(v) => { setStatusFilter(v as LotStatus | ""); setPage(0); }}
            options={STATUS_OPTIONS}
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
        emptyText={t("Lotlar topilmadi", "Лоты не найдены")}
      />

      {/* Close Modal */}
      <Modal
        open={!!closeTarget}
        onOpenChange={(v) => { if (!v) { setCloseTarget(null); closeForm.reset(); } }}
        title={closeTarget ? `${t("Lotni yopish", "Закрыть лот")} ${closeTarget.lot_number}` : ""}
      >
        <form onSubmit={closeForm.handleSubmit((d) => closeMut.mutate({ id: closeTarget!.id, reason: d.reason }))} className="flex flex-col gap-4">
          <Input label={t("Sabab (ixtiyoriy)", "Причина (необязательно)")} {...closeForm.register("reason")} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setCloseTarget(null)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={closeMut.isPending}>{t("Yopish", "Закрыть")}</Button>
          </ModalFooter>
        </form>
      </Modal>

      {/* Reopen Modal */}
      <Modal
        open={!!reopenTarget}
        onOpenChange={(v) => { if (!v) { setReopenTarget(null); reopenForm.reset(); } }}
        title={reopenTarget ? `${t("Lotni ochish", "Открыть лот")} ${reopenTarget.lot_number}` : ""}
      >
        <form onSubmit={reopenForm.handleSubmit((d) => reopenMut.mutate({ id: reopenTarget!.id, reason: d.reason }))} className="flex flex-col gap-4">
          <Input label={t("Sabab *", "Причина *")} {...reopenForm.register("reason")} error={reopenForm.formState.errors.reason?.message} />
          <ModalFooter>
            <Button type="button" variant="outline" onClick={() => setReopenTarget(null)}>{t("Bekor", "Отмена")}</Button>
            <Button type="submit" loading={reopenMut.isPending}>{t("Ochish", "Открыть")}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

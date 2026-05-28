"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { apiClient } from "@/lib/api/client";
import { exportApi } from "@/lib/api/export";
import { useAuthStore } from "@/lib/stores/auth";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { PaginatedResponse } from "@/lib/types";

interface AuditLogEntry {
  id: string;
  company_id: string | null;
  actor_id: string;
  actor_username: string;
  actor_full_name: string;
  entity_type: string;
  entity_id: string | null;
  entity_display: string | null;
  action: string;
  before_data: Record<string, unknown> | null;
  after_data: Record<string, unknown> | null;
  reason: string | null;
  ip_address: string | null;
  created_at: string;
}

const ACTION_VARIANT: Record<string, "success" | "danger" | "warning" | "info" | "default"> = {
  CREATE: "success",
  DELETE: "danger",
  UPDATE: "info",
  SUBMIT: "info",
  CLOSE: "default",
  REOPEN: "warning",
  CANCEL: "danger",
  POST: "success",
  BLOCK: "danger",
};

const ENTITY_TYPES = [
  { value: "", label: "All / Все" },
  { value: "lot", label: "Lot" },
  { value: "daily_report", label: "Daily Report" },
  { value: "shipment", label: "Shipment" },
  { value: "adjustment", label: "Adjustment" },
  { value: "user", label: "User" },
  { value: "counterparty", label: "Counterparty" },
];

export default function AuditLogPage() {
  const { language } = useAuthStore();
  const t = (uz: string, ru: string) => language === "uz" ? uz : ru;

  const [page, setPage] = useState(0);
  const [entityType, setEntityType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [actor, setActor] = useState("");
  const PAGE_SIZE = 100;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-log", page, entityType, dateFrom, dateTo, actor],
    queryFn: () => apiClient.get<PaginatedResponse<AuditLogEntry>>("/audit/", {
      page: page + 1,
      page_size: PAGE_SIZE,
      entity_type: entityType || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      actor: actor || undefined,
    }),
  });

  const columns: ColumnDef<AuditLogEntry>[] = [
    {
      accessorKey: "created_at",
      header: t("Vaqt", "Время"),
      size: 160,
      cell: ({ getValue }) => {
        const d = new Date(getValue() as string);
        return <span className="text-xs text-slate-500">{d.toLocaleString("ru-RU")}</span>;
      },
    },
    {
      accessorKey: "actor_username",
      header: t("Foydalanuvchi", "Пользователь"),
      size: 120,
      cell: ({ row }) => (
        <span className="text-xs">
          <span className="font-medium">{row.original.actor_username}</span>
          <br />
          <span className="text-slate-400">{row.original.actor_full_name}</span>
        </span>
      ),
    },
    {
      accessorKey: "action",
      header: t("Harakat", "Действие"),
      size: 100,
      cell: ({ getValue }) => {
        const a = getValue() as string;
        return <Badge variant={ACTION_VARIANT[a] ?? "default"}>{a}</Badge>;
      },
    },
    {
      accessorKey: "entity_type",
      header: t("Ob'ekt turi", "Тип объекта"),
      size: 110,
      cell: ({ getValue }) => <span className="font-mono text-xs">{getValue() as string}</span>,
    },
    {
      accessorKey: "entity_display",
      header: t("Ob'ekt", "Объект"),
      cell: ({ getValue }) => getValue() || "—",
    },
    {
      accessorKey: "reason",
      header: t("Sabab", "Причина"),
      cell: ({ getValue }) => getValue() || "—",
    },
    {
      accessorKey: "ip_address",
      header: "IP",
      size: 120,
      cell: ({ getValue }) => <span className="font-mono text-xs">{(getValue() as string) || "—"}</span>,
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">{t("Audit jurnali", "Журнал аудита")}</h1>
        <Button
          variant="outline" size="sm"
          onClick={() => exportApi.auditLog({ date_from: dateFrom, date_to: dateTo, entity_type: entityType })}
        >
          <Download size={14} /> Excel
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="w-40">
          <Select
            label={t("Tur", "Тип")}
            value={entityType}
            onValueChange={(v) => { setEntityType(v); setPage(0); }}
            options={ENTITY_TYPES}
          />
        </div>
        <div className="w-36">
          <Input
            label={t("Boshidan", "С даты")}
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
          />
        </div>
        <div className="w-36">
          <Input
            label={t("Gacha", "По дату")}
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
          />
        </div>
        <div className="w-44">
          <Input
            label={t("Foydalanuvchi", "Пользователь")}
            placeholder={t("Username...", "Логин...")}
            value={actor}
            onChange={(e) => { setActor(e.target.value); setPage(0); }}
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
        emptyText={t("Jurnal bo'sh", "Журнал пуст")}
      />
    </div>
  );
}

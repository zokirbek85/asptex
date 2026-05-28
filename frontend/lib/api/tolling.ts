import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";

// ── Types ──────────────────────────────────────────────────────────────────────

export type TollingLotStatus = "OPEN" | "CLOSED";
export type TollingDistributionStatus = "DRAFT" | "CONFIRMED";
export type TollingLineType = "OWNER_NET" | "PROCESSOR_FEE";

export interface TollingParticipant {
  id: string;
  tolling_lot_id: string;
  counterparty_id: string;
  counterparty_name: string | null;
  contract_id: string | null;
  raw_kg_delivered: number;
  fee_pct: number;
  fee_currency: string;
  fee_rate_per_kg: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TollingLot {
  id: string;
  company_id: string;
  lot_id: string;
  lot_number: string | null;
  status: TollingLotStatus;
  opened_at: string;
  closed_at: string | null;
  closed_by: string | null;
  close_reason: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  participants: TollingParticipant[];
  total_raw_kg: number;
  total_distributions: number;
  total_fg_distributed_kg: number;
}

export interface RawIntakeItem {
  participant_id: string;
  raw_kg_received_today: number;
}

export interface RawIntakeItemOut {
  id: string;
  participant_id: string;
  counterparty_id: string | null;
  counterparty_name: string | null;
  raw_kg_received_today: number;
}

export interface DistributionLineOut {
  id: string | null;
  participant_id: string | null;
  counterparty_id: string | null;
  counterparty_name: string | null;
  line_type: TollingLineType;
  gross_kg: number;
  fee_kg: number;
  net_kg: number;
  ownership_share_pct: number;
  fee_pct_applied: number;
  fee_amount_uzs: number | null;
  fee_amount_usd: number | null;
  stock_transaction_id: string | null;
}

export interface TollingDistribution {
  id: string;
  company_id: string;
  tolling_lot_id: string;
  distribution_date: string;
  daily_fg_kg_total: number;
  status: TollingDistributionStatus;
  confirmed_at: string | null;
  confirmed_by: string | null;
  notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  lines: DistributionLineOut[];
  raw_intakes: RawIntakeItemOut[];
  total_net_kg: number;
  total_fee_kg: number;
  total_kg_check: number;
}

export interface LotSummaryRow {
  counterparty_id: string;
  counterparty_name: string;
  raw_kg_delivered: number;
  ownership_share_pct: number;
  total_gross_kg: number;
  total_fee_kg: number;
  total_net_kg: number;
  fee_amount_uzs: number | null;
  fee_amount_usd: number | null;
}

export interface LotSummary {
  tolling_lot_id: string;
  lot_number: string;
  status: TollingLotStatus;
  opened_at: string;
  closed_at: string | null;
  rows: LotSummaryRow[];
  total_fg_kg: number;
  total_fee_kg: number;
  total_net_kg: number;
}

export interface DailyRegisterRow {
  distribution_id: string;
  distribution_date: string;
  daily_fg_kg_total: number;
  status: TollingDistributionStatus;
  lines: DistributionLineOut[];
  total_fee_kg: number;
  total_net_kg: number;
}

export interface DailyRegister {
  tolling_lot_id: string | null;
  date_from: string | null;
  date_to: string | null;
  rows: DailyRegisterRow[];
}

// ── API client ────────────────────────────────────────────────────────────────

export const tollingApi = {
  // Lots
  getActiveLot: () =>
    apiClient.get<TollingLot | null>("/tolling/lots/active"),

  getLot: (lotId: string) =>
    apiClient.get<TollingLot>(`/tolling/lots/${lotId}`),

  createLot: (data: { notes?: string | null }) =>
    apiClient.post<TollingLot>("/tolling/lots", data),

  closeLot: (lotId: string, data: { close_reason?: string | null }) =>
    apiClient.post<TollingLot>(`/tolling/lots/${lotId}/close`, data),

  // Participants
  addParticipant: (lotId: string, data: {
    counterparty_id: string;
    contract_id?: string | null;
    raw_kg_delivered?: number;
    fee_pct: number;
    fee_currency?: string;
    fee_rate_per_kg?: number | null;
  }) => apiClient.post<TollingParticipant>(`/tolling/lots/${lotId}/participants`, data),

  updateParticipant: (lotId: string, participantId: string, data: {
    fee_pct?: number;
    fee_rate_per_kg?: number | null;
    raw_kg_delivered?: number;
    is_active?: boolean;
  }) => apiClient.patch<TollingParticipant>(`/tolling/lots/${lotId}/participants/${participantId}`, data),

  removeParticipant: (lotId: string, participantId: string) =>
    apiClient.delete<void>(`/tolling/lots/${lotId}/participants/${participantId}`),

  // Distributions
  listDistributions: (params?: {
    tolling_lot_id?: string;
    date_from?: string;
    date_to?: string;
    status?: TollingDistributionStatus;
    page?: number;
    page_size?: number;
  }) => apiClient.get<PaginatedResponse<TollingDistribution>>("/tolling/distributions", params as Record<string, string>),

  createDistribution: (data: {
    tolling_lot_id: string;
    distribution_date: string;
    daily_fg_kg_total: number;
    raw_intakes?: RawIntakeItem[];
    notes?: string | null;
  }) => apiClient.post<TollingDistribution>("/tolling/distributions", data),

  getDistribution: (distId: string) =>
    apiClient.get<TollingDistribution>(`/tolling/distributions/${distId}`),

  updateDistribution: (distId: string, data: {
    daily_fg_kg_total?: number;
    raw_intakes?: RawIntakeItem[];
    notes?: string | null;
  }) => apiClient.patch<TollingDistribution>(`/tolling/distributions/${distId}`, data),

  previewDistribution: (distId: string) =>
    apiClient.post<TollingDistribution>(`/tolling/distributions/${distId}/preview`),

  confirmDistribution: (distId: string) =>
    apiClient.post<TollingDistribution>(`/tolling/distributions/${distId}/confirm`),

  unconfirmDistribution: (distId: string) =>
    apiClient.post<TollingDistribution>(`/tolling/distributions/${distId}/unconfirm`),

  // Reports
  getLotSummary: (lotId: string) =>
    apiClient.get<LotSummary>(`/tolling/reports/lot-summary/${lotId}`),

  getDailyRegister: (params?: {
    tolling_lot_id?: string;
    date_from?: string;
    date_to?: string;
  }) => apiClient.get<DailyRegister>("/tolling/reports/daily-register", params as Record<string, string>),

  // Exports — open in new tab
  exportLotSummary: (lotId: string) => {
    window.open(`/api/v1/tolling/export/lot-summary/${lotId}`, "_blank");
  },

  exportDailyRegister: (params?: { tolling_lot_id?: string; date_from?: string; date_to?: string }) => {
    const qs = params ? new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v))).toString() : "";
    window.open(`/api/v1/tolling/export/daily-register${qs ? "?" + qs : ""}`, "_blank");
  },
};

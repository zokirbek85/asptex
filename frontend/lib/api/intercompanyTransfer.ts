import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";
import type { GinningProductType } from "./ginningProduction";

export type IntercompanyTransferStatus = "DRAFT" | "CONFIRMED" | "CANCELLED";

export interface IntercompanyTransferLineCreate {
  bale_id?: string | null;
  quantity_kg: number;
}

export interface IntercompanyTransferCreate {
  destination_company_id: string;
  source_warehouse_id: string;
  destination_warehouse_id: string;
  product_type: GinningProductType;
  transfer_date: string;
  unit_price?: number | null;
  currency?: string;
  notes?: string | null;
  lines: IntercompanyTransferLineCreate[];
}

export interface IntercompanyTransferLine {
  id: string;
  bale_id: string | null;
  bale_number: string | null;
  quantity_kg: number;
}

export interface IntercompanyTransfer {
  id: string;
  source_company_id: string;
  source_company_name: string;
  destination_company_id: string;
  destination_company_name: string;
  source_warehouse_id: string;
  destination_warehouse_id: string;
  product_type: GinningProductType;
  transfer_number: string;
  transfer_date: string;
  status: IntercompanyTransferStatus;
  unit_price: number | null;
  currency: string;
  total_value: number | null;
  total_quantity_kg: number;
  lines: IntercompanyTransferLine[];
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  notes: string | null;
  created_at: string;
}

export const intercompanyTransferApi = {
  list: (params?: { status?: IntercompanyTransferStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<IntercompanyTransfer>>("/ginning/intercompany-transfers/", params),

  get: (id: string) => apiClient.get<IntercompanyTransfer>(`/ginning/intercompany-transfers/${id}`),

  create: (data: IntercompanyTransferCreate) =>
    apiClient.post<IntercompanyTransfer>("/ginning/intercompany-transfers/", data),

  confirm: (id: string) => apiClient.post<IntercompanyTransfer>(`/ginning/intercompany-transfers/${id}/confirm`),

  cancel: (id: string, reason: string) =>
    apiClient.post<IntercompanyTransfer>(`/ginning/intercompany-transfers/${id}/cancel`, { reason }),
};

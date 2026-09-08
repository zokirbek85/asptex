import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";

export type BuntStatus = "OPEN" | "CLOSED";

export interface GinningBunt {
  id: string;
  company_id: string;
  lot_id: string;
  lot_number: string;
  warehouse_id: string;
  status: BuntStatus;
  opened_at: string;
  closed_at: string | null;
  close_reason: string | null;
  notes: string | null;
  created_at: string;
}

export interface BuntFarmerComposition {
  farmer_id: string;
  farmer_name: string;
  total_net_kg: number;
  receiving_count: number;
}

export interface GinningBuntDetail extends GinningBunt {
  balance_kg: number;
  composition: BuntFarmerComposition[];
}

export const ginningBuntApi = {
  list: (params?: { warehouse_id?: string; status?: BuntStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<GinningBunt>>("/ginning/bunts/", params),

  get: (id: string) => apiClient.get<GinningBuntDetail>(`/ginning/bunts/${id}`),

  create: (data: { warehouse_id: string; notes?: string | null }) =>
    apiClient.post<GinningBunt>("/ginning/bunts/", data),

  close: (id: string, reason?: string) =>
    apiClient.patch<GinningBunt>(`/ginning/bunts/${id}/close`, { reason }),

  reopen: (id: string) => apiClient.patch<GinningBunt>(`/ginning/bunts/${id}/reopen`),
};

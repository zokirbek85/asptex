import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";

export type GinningProductionStatus = "DRAFT" | "COMPLETED" | "CANCELLED";
export type GinningProductType = "FIBER" | "SEED" | "LINT" | "PUX" | "ULYUK" | "OTHER";

export interface GinningProductionInputCreate {
  bunt_id: string;
  quantity_kg: number;
}

export interface GinningProductionOutputCreate {
  product_type: GinningProductType;
  warehouse_id: string;
  quantity_kg: number;
  notes?: string | null;
}

export interface GinningProductionOrderCreate {
  production_date: string;
  notes?: string | null;
  inputs: GinningProductionInputCreate[];
  outputs: GinningProductionOutputCreate[];
}

export interface GinningProductionInputResponse {
  id: string;
  bunt_id: string;
  bunt_lot_number: string;
  quantity_kg: number;
}

export interface GinningProductionOutputResponse {
  id: string;
  product_type: GinningProductType;
  warehouse_id: string;
  warehouse_name: string;
  quantity_kg: number;
  yield_pct: number | null;
  notes: string | null;
}

export interface GinningProductionOrder {
  id: string;
  company_id: string;
  production_number: string;
  production_date: string;
  status: GinningProductionStatus;
  inputs: GinningProductionInputResponse[];
  outputs: GinningProductionOutputResponse[];
  total_input_kg: number;
  total_output_kg: number;
  diff_kg: number;
  yield_pct: number;
  loss_pct: number;
  completed_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  notes: string | null;
  created_at: string;
}

export const ginningProductionApi = {
  list: (params?: { status?: GinningProductionStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<GinningProductionOrder>>("/ginning/production/", params),

  get: (id: string) => apiClient.get<GinningProductionOrder>(`/ginning/production/${id}`),

  create: (data: GinningProductionOrderCreate) =>
    apiClient.post<GinningProductionOrder>("/ginning/production/", data),

  update: (id: string, data: { notes?: string | null; inputs: GinningProductionInputCreate[]; outputs: GinningProductionOutputCreate[] }) =>
    apiClient.put<GinningProductionOrder>(`/ginning/production/${id}`, data),

  complete: (id: string) => apiClient.post<GinningProductionOrder>(`/ginning/production/${id}/complete`),

  cancel: (id: string, reason: string) =>
    apiClient.post<GinningProductionOrder>(`/ginning/production/${id}/cancel`, { reason }),
};

import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";

export type GinningBaleStatus = "IN_STOCK" | "SOLD" | "TRANSFERRED";

export interface GinningBaleCreate {
  production_order_id: string;
  warehouse_id: string;
  gross_weight_kg: number;
  tare_weight_kg: number;
  moisture_pct?: number | null;
  micronaire?: number | null;
  staple_length_mm?: number | null;
  strength?: number | null;
  color?: string | null;
  trash_pct?: number | null;
  grade?: string | null;
  quality_class?: string | null;
  notes?: string | null;
}

export interface GinningBale {
  id: string;
  company_id: string;
  production_order_id: string;
  production_number: string;
  warehouse_id: string;
  bale_number: string;
  production_date: string;
  gross_weight_kg: number;
  tare_weight_kg: number;
  net_weight_kg: number;
  moisture_pct: number | null;
  micronaire: number | null;
  staple_length_mm: number | null;
  strength: number | null;
  color: string | null;
  trash_pct: number | null;
  grade: string | null;
  quality_class: string | null;
  status: GinningBaleStatus;
  notes: string | null;
  created_at: string;
}

export interface GinningBaleCreateResult {
  bale: GinningBale;
  reconciliation_warning: string | null;
}

export const ginningBaleApi = {
  list: (params?: { production_order_id?: string; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<GinningBale>>("/ginning/bales/", params),

  get: (id: string) => apiClient.get<GinningBale>(`/ginning/bales/${id}`),

  create: (data: GinningBaleCreate) =>
    apiClient.post<GinningBaleCreateResult>("/ginning/bales/", data),
};

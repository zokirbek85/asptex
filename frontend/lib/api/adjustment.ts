import { apiClient } from "./client";
import type { AdjustmentStatus, PackagingItemType, PaginatedResponse, WasteType } from "@/lib/types";

export interface AdjustmentLineCreate {
  lot_id?: string | null;
  count_id?: string | null;
  owner_id?: string | null;
  waste_type?: WasteType | null;
  pkg_item_type?: PackagingItemType | null;
  quantity_kg_after: number;
  bags_after?: number;
  units_after?: number;
  notes?: string | null;
}

export interface AdjustmentCreate {
  warehouse_id: string;
  adjustment_date: string;
  reason: string;
}

export interface AdjustmentLineResponse {
  id: string;
  line_number: number;
  lot_id: string | null;
  count_id: string | null;
  owner_id: string | null;
  waste_type: WasteType | null;
  pkg_item_type: PackagingItemType | null;
  quantity_kg_before: number;
  quantity_kg_after: number;
  bags_before: number;
  bags_after: number;
  units_before: number;
  units_after: number;
  transaction_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface AdjustmentResponse {
  id: string;
  company_id: string;
  warehouse_id: string;
  adjustment_number: string;
  adjustment_date: string;
  reason: string;
  status: AdjustmentStatus;
  lines: AdjustmentLineResponse[];
  posted_at: string | null;
  posted_by: string | null;
  created_at: string;
  updated_at: string;
}

export const adjustmentApi = {
  list: (params?: { warehouse_id?: string; status?: AdjustmentStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<AdjustmentResponse>>("/adjustments/", params),

  get: (id: string) =>
    apiClient.get<AdjustmentResponse>(`/adjustments/${id}`),

  create: (body: AdjustmentCreate) =>
    apiClient.post<AdjustmentResponse>("/adjustments/", body),

  updateLines: (id: string, lines: AdjustmentLineCreate[]) =>
    apiClient.put<AdjustmentResponse>(`/adjustments/${id}/lines`, lines),

  post: (id: string) =>
    apiClient.post<AdjustmentResponse>(`/adjustments/${id}/post`),
};

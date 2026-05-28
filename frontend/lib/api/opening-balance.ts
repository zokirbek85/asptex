import { apiClient } from "./client";
import type { AdjustmentStatus, PackagingItemType, PaginatedResponse, WasteType } from "@/lib/types";

export interface OpeningBalanceLineCreate {
  lot_id?: string | null;
  count_id?: string | null;
  owner_id?: string | null;
  waste_type?: WasteType | null;
  pkg_item_type?: PackagingItemType | null;
  quantity_kg: number;
  quantity_bags?: number | null;
  quantity_kip?: number | null;
  quantity_units?: number | null;
  notes?: string | null;
}

export interface OpeningBalanceCreate {
  warehouse_id: string;
  balance_date: string;
  notes?: string | null;
}

export interface OpeningBalanceLineResponse {
  id: string;
  line_number: number;
  lot_id: string | null;
  count_id: string | null;
  owner_id: string | null;
  waste_type: WasteType | null;
  pkg_item_type: PackagingItemType | null;
  quantity_kg: number;
  quantity_bags: number | null;
  quantity_kip: number | null;
  quantity_units: number | null;
  lot_number: string | null;
  count_value: string | null;
  owner_name: string | null;
  transaction_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface OpeningBalanceResponse {
  id: string;
  company_id: string;
  warehouse_id: string;
  balance_date: string;
  status: AdjustmentStatus;
  notes: string | null;
  lines: OpeningBalanceLineResponse[];
  posted_at: string | null;
  posted_by: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export const openingBalanceApi = {
  list: (params?: { warehouse_id?: string; status?: AdjustmentStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<OpeningBalanceResponse>>("/opening-balances/", params),

  get: (id: string) =>
    apiClient.get<OpeningBalanceResponse>(`/opening-balances/${id}`),

  create: (body: OpeningBalanceCreate) =>
    apiClient.post<OpeningBalanceResponse>("/opening-balances/", body),

  updateLines: (id: string, lines: OpeningBalanceLineCreate[]) =>
    apiClient.put<OpeningBalanceResponse>(`/opening-balances/${id}/lines`, lines),

  post: (id: string) =>
    apiClient.post<OpeningBalanceResponse>(`/opening-balances/${id}/post`),

  delete: (id: string) =>
    apiClient.delete<void>(`/opening-balances/${id}`),
};

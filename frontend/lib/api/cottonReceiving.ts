import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";

export type CottonReceivingStatus = "DRAFT" | "POSTED" | "CANCELLED";

export interface CottonReceivingCreate {
  bunt_id: string;
  farmer_id: string;
  contract_id?: string | null;
  receiving_date: string;
  vehicle_number?: string | null;
  driver_name?: string | null;
  gross_weight_kg: number;
  tare_weight_kg: number;
  moisture_pct?: number | null;
  contamination_pct?: number | null;
  grade?: string | null;
  variety?: string | null;
  sort?: string | null;
  quality_class?: string | null;
  unit_price?: number | null;
  currency?: string;
  notes?: string | null;
}

export interface CottonReceiving {
  id: string;
  company_id: string;
  bunt_id: string;
  bunt_lot_number: string;
  farmer_id: string;
  farmer_name: string;
  contract_id: string | null;
  receiving_number: string;
  receiving_date: string;
  vehicle_number: string | null;
  driver_name: string | null;
  gross_weight_kg: number;
  tare_weight_kg: number;
  net_weight_kg: number;
  moisture_pct: number | null;
  contamination_pct: number | null;
  grade: string | null;
  variety: string | null;
  sort: string | null;
  quality_class: string | null;
  unit_price: number | null;
  price_source: string | null;
  total_amount: number | null;
  currency: string;
  status: CottonReceivingStatus;
  posted_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  notes: string | null;
  created_at: string;
}

export interface CottonPriceListRule {
  id: string;
  grade: string | null;
  variety: string | null;
  sort: string | null;
  quality_class: string | null;
  price_per_kg: number;
  currency: string;
  effective_from: string;
  is_active: boolean;
  created_at: string;
}

export const cottonReceivingApi = {
  list: (params?: {
    bunt_id?: string; farmer_id?: string; status?: CottonReceivingStatus; page?: number; page_size?: number;
  }) => apiClient.get<PaginatedResponse<CottonReceiving>>("/ginning/cotton-receiving/", params),

  get: (id: string) => apiClient.get<CottonReceiving>(`/ginning/cotton-receiving/${id}`),

  create: (data: CottonReceivingCreate) =>
    apiClient.post<CottonReceiving>("/ginning/cotton-receiving/", data),

  update: (id: string, data: Partial<CottonReceivingCreate>) =>
    apiClient.put<CottonReceiving>(`/ginning/cotton-receiving/${id}`, data),

  post: (id: string) => apiClient.post<CottonReceiving>(`/ginning/cotton-receiving/${id}/post`),

  cancel: (id: string, reason: string) =>
    apiClient.post<CottonReceiving>(`/ginning/cotton-receiving/${id}/cancel`, { reason }),

  listPriceRules: () => apiClient.get<CottonPriceListRule[]>("/ginning/cotton-receiving/price-list/"),

  createPriceRule: (data: {
    grade?: string | null; variety?: string | null; sort?: string | null; quality_class?: string | null;
    price_per_kg: number; currency?: string; effective_from: string;
  }) => apiClient.post<CottonPriceListRule>("/ginning/cotton-receiving/price-list/", data),
};

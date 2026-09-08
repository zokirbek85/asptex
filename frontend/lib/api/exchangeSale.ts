import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";
import type { GinningProductType } from "./ginningProduction";

export type ExchangeSaleStatus = "ACTIVE" | "PARTIALLY_CANCELLED" | "CANCELLED";

export interface ExchangeSaleLineCreate {
  product_type: GinningProductType;
  bale_id?: string | null;
  quantity_kg: number;
  unit_price: number;
  currency?: string;
  notes?: string | null;
}

export interface ExchangeSaleCreate {
  warehouse_id: string;
  sale_date: string;
  customer_id: string;
  contract_id?: string | null;
  exchange_name?: string | null;
  exchange_lot_number?: string | null;
  commission_amount?: number | null;
  broker_name?: string | null;
  transport_cost?: number | null;
  other_costs?: number | null;
  notes?: string | null;
  lines: ExchangeSaleLineCreate[];
}

export interface ExchangeSaleLine {
  id: string;
  line_number: number;
  product_type: GinningProductType;
  bale_id: string | null;
  bale_number: string | null;
  quantity_kg: number;
  unit_price: number;
  currency: string;
  total_amount: number;
  cancelled_kg: number;
  is_fully_cancelled: boolean;
  net_kg: number;
  notes: string | null;
}

export interface ExchangeSale {
  id: string;
  company_id: string;
  warehouse_id: string;
  sale_number: string;
  sale_date: string;
  status: ExchangeSaleStatus;
  customer_id: string;
  customer_name: string;
  contract_id: string | null;
  exchange_name: string | null;
  exchange_lot_number: string | null;
  commission_amount: number | null;
  broker_name: string | null;
  transport_cost: number | null;
  other_costs: number | null;
  payment_status: string;
  lines: ExchangeSaleLine[];
  total_kg: number;
  net_kg: number;
  total_value: number;
  notes: string | null;
  created_at: string;
}

export const exchangeSaleApi = {
  list: (params?: {
    warehouse_id?: string; customer_id?: string; status?: ExchangeSaleStatus; page?: number; page_size?: number;
  }) => apiClient.get<PaginatedResponse<ExchangeSale>>("/ginning/exchange-sales/", params),

  get: (id: string) => apiClient.get<ExchangeSale>(`/ginning/exchange-sales/${id}`),

  create: (data: ExchangeSaleCreate) =>
    apiClient.post<ExchangeSale>("/ginning/exchange-sales/", data),

  cancelLine: (saleId: string, lineId: string, body: { quantity_kg: number; reason: string }) =>
    apiClient.post<ExchangeSale>(`/ginning/exchange-sales/${saleId}/lines/${lineId}/cancel`, body),
};

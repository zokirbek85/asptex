import { apiClient } from "./client";
import type { PaginatedResponse, ShipmentStatus } from "@/lib/types";

export interface ShipmentLineCreate {
  lot_id: string;
  count_id: string;
  owner_id: string;
  quantity_kg: number;
  quantity_bags?: number | null;
  notes?: string | null;
}

export interface ShipmentCreate {
  warehouse_id: string;
  shipment_date: string;
  buyer_id: string;
  contract_id?: string | null;
  lines: ShipmentLineCreate[];
  notes?: string | null;
}

export interface ShipmentLineResponse {
  id: string;
  line_number: number;
  lot_id: string;
  lot_number: string;
  count_id: string;
  count_value: string;
  owner_id: string;
  owner_name: string;
  quantity_kg: number;
  quantity_bags: number | null;
  cancelled_kg: number;
  cancelled_bags: number;
  is_fully_cancelled: boolean;
  net_kg: number;
}

export interface ShipmentResponse {
  id: string;
  shipment_number: string;
  shipment_date: string;
  status: ShipmentStatus;
  buyer_id: string;
  buyer_name: string;
  contract_id: string | null;
  warehouse_id: string;
  lines: ShipmentLineResponse[];
  total_kg: number;
  net_kg: number;
  notes: string | null;
  created_at: string;
}

export const shipmentApi = {
  list: (params?: {
    warehouse_id?: string;
    buyer_id?: string;
    lot_id?: string;
    status?: ShipmentStatus;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }) => apiClient.get<PaginatedResponse<ShipmentResponse>>("/shipments/", params),

  get: (id: string) =>
    apiClient.get<ShipmentResponse>(`/shipments/${id}`),

  getByNumber: (number: string) =>
    apiClient.get<ShipmentResponse>(`/shipments/by-number/${number}`),

  create: (body: ShipmentCreate) =>
    apiClient.post<ShipmentResponse>("/shipments/", body),

  cancelLine: (shipmentId: string, lineId: string, body: { quantity_kg: number; quantity_bags?: number | null; reason: string }) =>
    apiClient.post<ShipmentResponse>(`/shipments/${shipmentId}/lines/${lineId}/cancel`, body),
};

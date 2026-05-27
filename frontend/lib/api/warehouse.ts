import { apiClient } from "./client";
import type { PaginatedResponse, Warehouse, WarehouseCreate, WarehouseType, WarehouseUpdate } from "@/lib/types";

export const warehouseApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    active_only?: boolean;
    warehouse_type?: WarehouseType;
  }) => apiClient.get<PaginatedResponse<Warehouse>>("/warehouses/", params),

  get: (id: string) =>
    apiClient.get<Warehouse>(`/warehouses/${id}`),

  create: (data: WarehouseCreate) =>
    apiClient.post<Warehouse>("/warehouses/", data),

  update: (id: string, data: WarehouseUpdate) =>
    apiClient.put<Warehouse>(`/warehouses/${id}`, data),

  activate: (id: string) =>
    apiClient.patch<Warehouse>(`/warehouses/${id}/activate`),

  deactivate: (id: string) =>
    apiClient.patch<Warehouse>(`/warehouses/${id}/deactivate`),
};

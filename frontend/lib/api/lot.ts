import { apiClient } from "./client";
import type { Lot, LotStatus, PaginatedResponse, StockSummaryItem } from "@/lib/types";

export const lotApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; status?: LotStatus }) =>
    apiClient.get<PaginatedResponse<Lot>>("/lots/", params),

  get: (id: string, include_stock = false) =>
    apiClient.get<Lot>(`/lots/${id}`, { include_stock }),

  create: (notes?: string) =>
    apiClient.post<Lot>("/lots/", { notes }),

  update: (id: string, notes: string) =>
    apiClient.put<Lot>(`/lots/${id}`, { notes }),

  getStock: (id: string) =>
    apiClient.get<StockSummaryItem[]>(`/lots/${id}/stock`),

  close: (id: string, reason?: string) =>
    apiClient.patch<Lot>(`/lots/${id}/close`, { reason }),

  reopen: (id: string, reason: string) =>
    apiClient.patch<Lot>(`/lots/${id}/reopen`, { reason }),

  block: (id: string) =>
    apiClient.patch<Lot>(`/lots/${id}/block`),

  unblock: (id: string) =>
    apiClient.patch<Lot>(`/lots/${id}/unblock`),
};

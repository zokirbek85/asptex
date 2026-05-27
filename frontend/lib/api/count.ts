import { apiClient } from "./client";
import type { CountCatalog, CountCreate, CountUpdate, PaginatedResponse } from "@/lib/types";

export const countApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; active_only?: boolean }) =>
    apiClient.get<PaginatedResponse<CountCatalog>>("/counts/", params),

  get: (id: string) =>
    apiClient.get<CountCatalog>(`/counts/${id}`),

  create: (data: CountCreate) =>
    apiClient.post<CountCatalog>("/counts/", data),

  update: (id: string, data: CountUpdate) =>
    apiClient.put<CountCatalog>(`/counts/${id}`, data),

  activate: (id: string) =>
    apiClient.patch<CountCatalog>(`/counts/${id}/activate`),

  deactivate: (id: string) =>
    apiClient.patch<CountCatalog>(`/counts/${id}/deactivate`),
};

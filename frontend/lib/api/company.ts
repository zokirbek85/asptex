import { apiClient } from "./client";
import type { Company, CompanyCreate, CompanyUpdate, PaginatedResponse } from "@/lib/types";

export const companyApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; active_only?: boolean }) =>
    apiClient.get<PaginatedResponse<Company>>("/companies/", params),

  get: (id: string) =>
    apiClient.get<Company>(`/companies/${id}`),

  create: (data: CompanyCreate) =>
    apiClient.post<Company>("/companies/", data),

  update: (id: string, data: CompanyUpdate) =>
    apiClient.put<Company>(`/companies/${id}`, data),

  activate: (id: string) =>
    apiClient.patch<Company>(`/companies/${id}/activate`),

  deactivate: (id: string) =>
    apiClient.patch<Company>(`/companies/${id}/deactivate`),
};

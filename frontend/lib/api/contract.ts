import { apiClient } from "./client";
import type { Contract, ContractCreate, ContractUpdate, PaginatedResponse } from "@/lib/types";

export const contractApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    active_only?: boolean;
    counterparty_id?: string;
  }) => apiClient.get<PaginatedResponse<Contract>>("/contracts/", params),

  get: (id: string) =>
    apiClient.get<Contract>(`/contracts/${id}`),

  create: (data: ContractCreate) =>
    apiClient.post<Contract>("/contracts/", data),

  update: (id: string, data: ContractUpdate) =>
    apiClient.put<Contract>(`/contracts/${id}`, data),

  activate: (id: string) =>
    apiClient.patch<Contract>(`/contracts/${id}/activate`),

  deactivate: (id: string) =>
    apiClient.patch<Contract>(`/contracts/${id}/deactivate`),
};

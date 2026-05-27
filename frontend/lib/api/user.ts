import { apiClient } from "./client";
import type { PaginatedResponse, User, UserCreate, UserRoleAssign, UserRoleRecord, UserUpdate } from "@/lib/types";

export const userApi = {
  list: (params?: { page?: number; page_size?: number; search?: string; active_only?: boolean }) =>
    apiClient.get<PaginatedResponse<User>>("/users/", params),

  get: (id: string) =>
    apiClient.get<User>(`/users/${id}`),

  create: (data: UserCreate) =>
    apiClient.post<User>("/users/", data),

  update: (id: string, data: UserUpdate) =>
    apiClient.put<User>(`/users/${id}`, data),

  changePassword: (id: string, new_password: string) =>
    apiClient.patch<{ message: string }>(`/users/${id}/password`, { new_password }),

  activate: (id: string) =>
    apiClient.patch<User>(`/users/${id}/activate`),

  deactivate: (id: string) =>
    apiClient.patch<User>(`/users/${id}/deactivate`),

  assignRole: (id: string, data: UserRoleAssign) =>
    apiClient.post<UserRoleRecord>(`/users/${id}/roles`, data),

  updateRole: (id: string, companyId: string, data: Omit<UserRoleAssign, "company_id">) =>
    apiClient.put<UserRoleRecord>(`/users/${id}/roles/${companyId}`, data),

  removeRole: (id: string, companyId: string) =>
    apiClient.delete<{ message: string }>(`/users/${id}/roles/${companyId}`),
};

import { apiClient } from "./client";

export interface DataResetRequest {
  modules: string[];
  confirm_company_name: string;
}

export interface DataResetResponse {
  modules_cleared: string[];
  deleted_counts: Record<string, number>;
}

export const dataResetApi = {
  modules: () => apiClient.get<string[]>("/admin/data-reset/modules"),

  reset: (body: DataResetRequest) =>
    apiClient.post<DataResetResponse>("/admin/data-reset/", body),
};

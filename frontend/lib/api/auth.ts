import { apiClient } from "./client";
import type {
  AccessTokenResponse,
  MeResponse,
  TokenResponse,
} from "@/lib/types";

export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post<TokenResponse>("/auth/login", { username, password }, false),

  switchCompany: (company_id: string) =>
    apiClient.post<AccessTokenResponse>("/auth/switch-company", { company_id }),

  refresh: (refresh_token: string) =>
    apiClient.post<AccessTokenResponse>("/auth/refresh", { refresh_token }, false),

  logout: (refresh_token: string) =>
    apiClient.post<{ message: string }>("/auth/logout", { refresh_token }),

  me: () => apiClient.get<MeResponse>("/auth/me"),
};

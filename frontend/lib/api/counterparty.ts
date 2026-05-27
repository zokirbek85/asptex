import { apiClient } from "./client";
import type {
  Counterparty,
  CounterpartyContact,
  CounterpartyCreate,
  CounterpartyType,
  CounterpartyUpdate,
  PaginatedResponse,
} from "@/lib/types";

export const counterpartyApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    active_only?: boolean;
    counterparty_type?: CounterpartyType;
  }) => apiClient.get<PaginatedResponse<Counterparty>>("/counterparties/", params),

  get: (id: string) =>
    apiClient.get<Counterparty>(`/counterparties/${id}`),

  create: (data: CounterpartyCreate) =>
    apiClient.post<Counterparty>("/counterparties/", data),

  update: (id: string, data: CounterpartyUpdate) =>
    apiClient.put<Counterparty>(`/counterparties/${id}`, data),

  addContact: (id: string, data: { contact_type: string; contact_value: string; label?: string | null; is_primary?: boolean }) =>
    apiClient.post<CounterpartyContact>(`/counterparties/${id}/contacts`, data),

  removeContact: (id: string, contactId: string) =>
    apiClient.delete<{ message: string }>(`/counterparties/${id}/contacts/${contactId}`),

  activate: (id: string) =>
    apiClient.patch<Counterparty>(`/counterparties/${id}/activate`),

  deactivate: (id: string) =>
    apiClient.patch<Counterparty>(`/counterparties/${id}/deactivate`),

  merge: (targetId: string, sourceId: string, reason?: string) =>
    apiClient.post<Counterparty>(`/counterparties/${targetId}/merge`, { source_id: sourceId, reason }),
};

import { apiClient } from "./client";
import type { PaginatedResponse } from "@/lib/types";

export type FarmerPaymentStatus = "DRAFT" | "POSTED" | "CANCELLED";
export type FarmerLedgerEntryType = "RECEIVABLE_COTTON" | "ADVANCE_PAYMENT" | "PAYMENT" | "DEDUCTION" | "ADJUSTMENT";

export interface FarmerBalance {
  farmer_id: string;
  farmer_name: string;
  balance: number;
  currency: string;
}

export interface FarmerLedgerEntry {
  id: string;
  entry_type: FarmerLedgerEntryType;
  direction: number;
  amount: number;
  currency: string;
  reference_type: string | null;
  reference_id: string | null;
  entry_date: string;
  notes: string | null;
  created_at: string;
}

export interface FarmerPaymentCreate {
  farmer_id: string;
  payment_date: string;
  amount: number;
  currency?: string;
  payment_method?: string;
  reference_note?: string | null;
}

export interface FarmerPayment {
  id: string;
  company_id: string;
  farmer_id: string;
  farmer_name: string;
  payment_number: string;
  payment_date: string;
  amount: number;
  currency: string;
  payment_method: string;
  status: FarmerPaymentStatus;
  posted_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  reference_note: string | null;
  created_at: string;
}

export const farmerSettlementApi = {
  listBalances: () => apiClient.get<FarmerBalance[]>("/ginning/farmer-settlements/balances"),

  getStatement: (farmerId: string, params?: { page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<FarmerLedgerEntry>>(`/ginning/farmer-settlements/farmers/${farmerId}/statement`, params),

  listPayments: (params?: { farmer_id?: string; status?: FarmerPaymentStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<FarmerPayment>>("/ginning/farmer-settlements/payments", params),

  createPayment: (data: FarmerPaymentCreate) =>
    apiClient.post<FarmerPayment>("/ginning/farmer-settlements/payments", data),

  postPayment: (id: string) => apiClient.post<FarmerPayment>(`/ginning/farmer-settlements/payments/${id}/post`),

  cancelPayment: (id: string, reason: string) =>
    apiClient.post<FarmerPayment>(`/ginning/farmer-settlements/payments/${id}/cancel`, { reason }),
};

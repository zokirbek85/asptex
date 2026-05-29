import { apiClient } from "./client";
import type {
  LineCategory,
  PackagingItemType,
  PaginatedResponse,
  ReportStatus,
  WasteType,
} from "@/lib/types";

export interface DailyReportLineCreate {
  line_category: LineCategory;
  lot_id?: string | null;
  count_id?: string | null;
  owner_id?: string | null;
  waste_type?: WasteType | null;
  buyer_id?: string | null;
  pkg_item_type?: PackagingItemType | null;
  quantity_kg: number;
  quantity_bags?: number | null;
  quantity_kip?: number | null;
  quantity_units?: number | null;
  notes?: string | null;
}

export interface DailyReportLineResponse extends DailyReportLineCreate {
  id: string;
  line_number: number;
  transaction_id: string | null;
}

export interface OpeningBalanceLine {
  lot_id: string | null;
  lot_number: string | null;
  count_id: string | null;
  count_value: string | null;
  owner_id: string | null;
  owner_name: string | null;
  waste_type: WasteType | null;
  pkg_item_type: PackagingItemType | null;
  quantity_kg: number;
  quantity_bags: number | null;
  quantity_units: number | null;
}

export interface DailyReportResponse {
  id: string;
  company_id: string;
  warehouse_id: string;
  report_date: string;
  status: ReportStatus;
  opening_balance: OpeningBalanceLine[];
  lines: DailyReportLineResponse[];
  submitted_at: string | null;
  submitted_by: string | null;
  closed_at: string | null;
  closed_by: string | null;
  reopen_count: number;
  notes: string | null;
  created_at: string;
}

export const dailyReportApi = {
  list: (params?: {
    warehouse_id?: string;
    page?: number;
    page_size?: number;
    status?: ReportStatus;
    date_from?: string;
    date_to?: string;
  }) => apiClient.get<PaginatedResponse<DailyReportResponse>>("/daily-reports/", params),

  lookup: (warehouse_id: string, report_date: string) =>
    apiClient.get<DailyReportResponse | null>("/daily-reports/lookup", { warehouse_id, report_date }),

  getFgTotal: (report_date: string) =>
    apiClient.get<{ date: string; total_kg: number }>("/daily-reports/fg-total", { report_date }),

  getOrCreate: (body: { warehouse_id: string; report_date: string; notes?: string | null }) =>
    apiClient.post<DailyReportResponse>("/daily-reports/", body),

  get: (id: string) =>
    apiClient.get<DailyReportResponse>(`/daily-reports/${id}`),

  updateLines: (id: string, lines: DailyReportLineCreate[]) =>
    apiClient.put<DailyReportResponse>(`/daily-reports/${id}/lines`, { lines }),

  submit: (id: string, lines: DailyReportLineCreate[]) =>
    apiClient.post<DailyReportResponse>(`/daily-reports/${id}/submit`, { lines }),

  close: (id: string) =>
    apiClient.post<DailyReportResponse>(`/daily-reports/${id}/close`),

  reopen: (id: string, reopen_reason: string) =>
    apiClient.post<DailyReportResponse>(`/daily-reports/${id}/reopen`, { reopen_reason }),

  deleteDraft: (id: string) =>
    apiClient.delete<void>(`/daily-reports/${id}`),
};

import { apiClient } from "./client";

export interface GinningDashboardSummary {
  raw_cotton_received_kg: number;
  raw_cotton_available_kg: number;
  raw_cotton_processed_kg: number;
  fiber_produced_kg: number;
  seed_produced_kg: number;
  lint_produced_kg: number;
  pux_produced_kg: number;
  ulyuk_produced_kg: number;
  total_output_kg: number;
  fiber_yield_pct: number;
  exchange_sales_value: number;
  exchange_sales_kg: number;
  intercompany_transfers_kg: number;
  farmer_payable_total: number;
  farmer_paid_total: number;
  open_bunts_count: number;
  draft_production_orders_count: number;
}

export interface GinningReceivingTrendPoint {
  date: string;
  quantity_kg: number;
}

export interface ChartDataPoint {
  label: string;
  value: number;
}

export const ginningDashboardApi = {
  getSummary: () => apiClient.get<GinningDashboardSummary>("/ginning/dashboard/summary"),

  getReceivingTrend: (days = 30) =>
    apiClient.get<GinningReceivingTrendPoint[]>("/ginning/dashboard/receiving-trend", { days }),

  getOutputDistribution: () =>
    apiClient.get<ChartDataPoint[]>("/ginning/dashboard/output-distribution"),
};

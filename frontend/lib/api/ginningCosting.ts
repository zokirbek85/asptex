import { apiClient } from "./client";
import type { GinningProductType } from "./ginningProduction";

export type GinningCostType =
  | "ELECTRICITY" | "GAS" | "LABOR" | "DEPRECIATION" | "MAINTENANCE" | "PACKAGING" | "OVERHEAD" | "OTHER";
export type CostAllocationMethod = "SALES_VALUE" | "QUANTITY" | "MANUAL_PERCENTAGE";

export interface GinningProductionCost {
  id: string;
  production_order_id: string;
  cost_type: GinningCostType;
  amount: number;
  currency: string;
  notes: string | null;
  created_at: string;
}

export interface CostAllocationLine {
  output_id: string;
  product_type: GinningProductType;
  quantity_kg: number;
  allocated_cost: number;
  cost_per_kg: number;
}

export interface ProductionCostSummary {
  production_order_id: string;
  production_number: string;
  raw_material_cost: number;
  other_costs: GinningProductionCost[];
  other_costs_total: number;
  total_cost: number;
  allocation_method: CostAllocationMethod;
  allocations: CostAllocationLine[];
}

export interface ProductProfitability {
  product_type: GinningProductType;
  total_sales_value: number;
  total_allocated_cost: number;
  total_allocated_sales_expenses: number;
  profit: number;
  total_quantity_sold_kg: number;
}

export const ginningCostingApi = {
  addCost: (orderId: string, data: { cost_type: GinningCostType; amount: number; currency?: string; notes?: string | null }) =>
    apiClient.post<GinningProductionCost>(`/ginning/costing/production-orders/${orderId}/costs`, data),

  getSummary: (orderId: string, method: CostAllocationMethod = "QUANTITY") =>
    apiClient.get<ProductionCostSummary>(`/ginning/costing/production-orders/${orderId}/summary`, { method }),

  getSummaryWithManualPct: (orderId: string, manual_percentages: Record<string, number>) =>
    apiClient.post<ProductionCostSummary>(`/ginning/costing/production-orders/${orderId}/summary`, {
      method: "MANUAL_PERCENTAGE",
      manual_percentages,
    }),

  getProfitability: (params?: { date_from?: string; date_to?: string }) =>
    apiClient.get<ProductProfitability[]>("/ginning/costing/profitability", params),
};
